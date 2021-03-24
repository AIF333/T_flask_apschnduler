from __future__ import absolute_import
from apscheduler.job import Job
from apscheduler.jobstores.base import JobLookupError
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.schedulers.base import BaseScheduler, STATE_STOPPED, ConflictingIdError
from apscheduler.triggers.base import BaseTrigger
from flask_apscheduler import APScheduler
from threading import Thread, Event
from apscheduler.util import undefined, datetime_to_utc_timestamp, TIMEOUT_MAX, asbool
from inspect import ismethod, isclass
import six
from apscheduler.util import ref_to_obj, obj_to_ref, get_callable_name, check_callable_args, convert_to_datetime
from hdy_flask_apschnduler.utils import get_host_ip

try:
    from collections.abc import Iterable, Mapping
except ImportError:
    from collections import Iterable, Mapping

try:
    import cPickle as pickle
except ImportError:  # pragma: nocover
    import pickle

try:
    from bson.binary import Binary
    from pymongo.errors import DuplicateKeyError
    from pymongo import MongoClient, ASCENDING
except ImportError:  # pragma: nocover
    raise ImportError('MongoDBJobStore requires PyMongo installed')

"""
说明： 通过继承和调整部分方法，使flask_apschnduler支持分布式，动态修改mongo表任务对应的ip可支持任务自动分发到对应的机器
实现原理： 增加ip字段，判断配置的ip是否和服务器真实ip一致，如果是则可以执行定时任务
局限： 1.基于 Flask-APScheduler==1.12.1 APScheduler==3.7.0 版本的
      2.SCHEDULER_JOBSTORES只支持mongodb的存储，其他类型都不支持
"""


class HdyAPScheduler(APScheduler):
    def __init__(self, scheduler=None, app=None):
        super(HdyAPScheduler, self).__init__(scheduler, app)
        self._scheduler = HdyBackgroundScheduler()


class HdyBaseScheduler(BaseScheduler):
    def add_job(self, func, ip=None, trigger=None, args=None, kwargs=None, id=None, name=None,
                misfire_grace_time=undefined, coalesce=undefined, max_instances=undefined,
                next_run_time=undefined, jobstore='default', executor='default',
                replace_existing=False, **trigger_args):

        job_kwargs = {
            'trigger': self._create_trigger(trigger, trigger_args),
            'executor': executor,
            'func': func,
            'args': tuple(args) if args is not None else (),
            'kwargs': dict(kwargs) if kwargs is not None else {},
            'id': id,
            'name': name,
            'misfire_grace_time': misfire_grace_time,
            'coalesce': coalesce,
            'max_instances': max_instances,
            'next_run_time': next_run_time,
            'ip': ip
        }
        job_kwargs = dict((key, value) for key, value in six.iteritems(job_kwargs) if
                          value is not undefined)
        job = HdyJob(self, **job_kwargs)

        # Don't really add jobs to job stores before the scheduler is up and running
        with self._jobstores_lock:
            if self.state == STATE_STOPPED:
                self._pending_jobs.append((job, jobstore, replace_existing))
                self._logger.info('Adding job tentatively -- it will be properly scheduled when '
                                  'the scheduler starts')
            else:
                self._real_add_job(job, jobstore, replace_existing)

        return job


class HdyBlockingScheduler(HdyBaseScheduler):
    _event = None

    def start(self, *args, **kwargs):
        if self._event is None or self._event.is_set():
            self._event = Event()

        super(HdyBlockingScheduler, self).start(*args, **kwargs)
        self._main_loop()

    def shutdown(self, wait=True):
        super(HdyBlockingScheduler, self).shutdown(wait)
        self._event.set()

    def _main_loop(self):
        wait_seconds = TIMEOUT_MAX
        while self.state != STATE_STOPPED:
            self._event.wait(wait_seconds)
            self._event.clear()
            wait_seconds = self._process_jobs()

    def wakeup(self):
        self._event.set()


class HdyBackgroundScheduler(HdyBlockingScheduler):
    _thread = None

    def _configure(self, config):
        self._daemon = asbool(config.pop('daemon', True))
        super(HdyBackgroundScheduler, self)._configure(config)

    def start(self, *args, **kwargs):
        if self._event is None or self._event.is_set():
            self._event = Event()

        HdyBaseScheduler.start(self, *args, **kwargs)
        self._thread = Thread(target=self._main_loop, name='APScheduler')
        self._thread.daemon = self._daemon
        self._thread.start()

    def shutdown(self, *args, **kwargs):
        super(HdyBackgroundScheduler, self).shutdown(*args, **kwargs)
        self._thread.join()
        del self._thread


class HdyJob(Job):
    __slots__ = ('ip',)

    def _modify(self, **changes):
        """
        Validates the changes to the Job and makes the modifications if and only if all of them
        validate.

        """
        approved = {}

        if 'id' in changes:
            value = changes.pop('id')
            if not isinstance(value, six.string_types):
                raise TypeError("id must be a nonempty string")
            if hasattr(self, 'id'):
                raise ValueError('The job ID may not be changed')
            approved['id'] = value

        if 'func' in changes or 'args' in changes or 'kwargs' in changes:
            func = changes.pop('func') if 'func' in changes else self.func
            args = changes.pop('args') if 'args' in changes else self.args
            kwargs = changes.pop('kwargs') if 'kwargs' in changes else self.kwargs

            if isinstance(func, six.string_types):
                func_ref = func
                func = ref_to_obj(func)
            elif callable(func):
                try:
                    func_ref = obj_to_ref(func)
                except ValueError:
                    # If this happens, this Job won't be serializable
                    func_ref = None
            else:
                raise TypeError('func must be a callable or a textual reference to one')

            if not hasattr(self, 'name') and changes.get('name', None) is None:
                changes['name'] = get_callable_name(func)

            if isinstance(args, six.string_types) or not isinstance(args, Iterable):
                raise TypeError('args must be a non-string iterable')
            if isinstance(kwargs, six.string_types) or not isinstance(kwargs, Mapping):
                raise TypeError('kwargs must be a dict-like object')

            check_callable_args(func, args, kwargs)

            approved['func'] = func
            approved['func_ref'] = func_ref
            approved['args'] = args
            approved['kwargs'] = kwargs

        if 'name' in changes:
            value = changes.pop('name')
            if not value or not isinstance(value, six.string_types):
                raise TypeError("name must be a nonempty string")
            approved['name'] = value

        if 'misfire_grace_time' in changes:
            value = changes.pop('misfire_grace_time')
            if value is not None and (not isinstance(value, six.integer_types) or value <= 0):
                raise TypeError('misfire_grace_time must be either None or a positive integer')
            approved['misfire_grace_time'] = value

        if 'coalesce' in changes:
            value = bool(changes.pop('coalesce'))
            approved['coalesce'] = value

        if 'max_instances' in changes:
            value = changes.pop('max_instances')
            if not isinstance(value, six.integer_types) or value <= 0:
                raise TypeError('max_instances must be a positive integer')
            approved['max_instances'] = value

        if 'trigger' in changes:
            trigger = changes.pop('trigger')
            if not isinstance(trigger, BaseTrigger):
                raise TypeError('Expected a trigger instance, got %s instead' %
                                trigger.__class__.__name__)

            approved['trigger'] = trigger

        if 'executor' in changes:
            value = changes.pop('executor')
            if not isinstance(value, six.string_types):
                raise TypeError('executor must be a string')
            approved['executor'] = value

        if 'next_run_time' in changes:
            value = changes.pop('next_run_time')
            approved['next_run_time'] = convert_to_datetime(value, self._scheduler.timezone,
                                                            'next_run_time')

        if 'ip' in changes:
            value = changes.pop('ip')
            if not isinstance(value, six.string_types):
                raise TypeError('ip must be a string')
            approved['ip'] = value

        if changes:
            raise AttributeError('The following are not modifiable attributes of Job: %s' %
                                 ', '.join(changes))

        for key, value in six.iteritems(approved):
            setattr(self, key, value)

    def __getstate__(self):
        # Don't allow this Job to be serialized if the function reference could not be determined
        if not self.func_ref:
            raise ValueError(
                'This Job cannot be serialized since the reference to its callable (%r) could not '
                'be determined. Consider giving a textual reference (module:function name) '
                'instead.' % (self.func,))

        # Instance methods cannot survive serialization as-is, so store the "self" argument
        # explicitly
        func = self.func
        if ismethod(func) and not isclass(func.__self__) and obj_to_ref(func) == self.func_ref:
            args = (func.__self__,) + tuple(self.args)
        else:
            args = self.args

        return {
            'version': 1,
            'id': self.id,
            'func': self.func_ref,
            'trigger': self.trigger,
            'executor': self.executor,
            'args': args,
            'kwargs': self.kwargs,
            'name': self.name,
            'misfire_grace_time': self.misfire_grace_time,
            'coalesce': self.coalesce,
            'max_instances': self.max_instances,
            'next_run_time': self.next_run_time,
            'ip': self.ip
        }

    def __setstate__(self, state):
        if state.get('version', 1) > 1:
            raise ValueError('Job has version %s, but only version 1 can be handled' %
                             state['version'])

        self.id = state['id']
        self.func_ref = state['func']
        self.func = ref_to_obj(self.func_ref)
        self.trigger = state['trigger']
        self.executor = state['executor']
        self.args = state['args']
        self.kwargs = state['kwargs']
        self.name = state['name']
        self.misfire_grace_time = state['misfire_grace_time']
        self.coalesce = state['coalesce']
        self.max_instances = state['max_instances']
        self.next_run_time = state['next_run_time']
        self.ip = state['ip']


class HdyMongoDBJobStore(MongoDBJobStore):
    def get_due_jobs(self, now):
        timestamp = datetime_to_utc_timestamp(now)
        return self._get_jobs({'next_run_time': {'$lte': timestamp}, 'ip': self.ip})

    def _get_jobs(self, conditions):
        jobs = []
        failed_job_ids = []
        for document in self.collection.find(conditions, ['_id', 'job_state', 'ip'],
                                             sort=[('next_run_time', ASCENDING)]):
            try:
                jobs.append(self._reconstitute_job(document['job_state']))
            except BaseException:
                self._logger.exception('Unable to restore job "%s" -- removing it',
                                       document['_id'])
                failed_job_ids.append(document['_id'])

        # Remove all the jobs we failed to restore
        if failed_job_ids:
            self.collection.remove({'_id': {'$in': failed_job_ids}})

        return jobs

    def _reconstitute_job(self, job_state, ip=None):
        job_state = pickle.loads(job_state)
        job = HdyJob.__new__(HdyJob)
        if 'ip' not in job_state and ip:
            job_state[ip] = ip
        job.__setstate__(job_state)
        job._scheduler = self._scheduler
        job._jobstore_alias = self._alias
        return job

    @property
    def ip(self):
        if not hasattr(self, '_ip'):
            self._ip = get_host_ip()
        return self._ip

    def add_job(self, job):
        try:
            self.collection.insert_one({
                '_id': job.id,
                'ip': job.ip,
                'next_run_time': datetime_to_utc_timestamp(job.next_run_time),
                'job_state': Binary(pickle.dumps(job.__getstate__(), self.pickle_protocol))
            })
        except DuplicateKeyError:
            raise ConflictingIdError(job.id)

    def lookup_job(self, job_id):
        document = self.collection.find_one(job_id, ['job_state', 'ip'])
        return self._reconstitute_job(document['job_state'], document['ip']) if document else None

    def update_job(self, job):
        """
        当replace_existing设置为True时，默认是没有更新ip地址的，如果需要更新ip则在changes中添加:
            'ip': job.ip
        """
        try:
            changes = {
                'next_run_time': datetime_to_utc_timestamp(job.next_run_time),
                'job_state': Binary(pickle.dumps(job.__getstate__(), self.pickle_protocol)),
                # 'ip': job.ip  # 新加的任务替换时是否替换已有的ip
            }
            result = self.collection.update_one({'_id': job.id}, {'$set': changes})
            if result and result.matched_count == 0:
                raise JobLookupError(job.id)
        except Exception as e:
            print(e)

