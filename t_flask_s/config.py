from pymongo import MongoClient
from hdy_flask_apschnduler.hdy_scheduler import HdyMongoDBJobStore


class Config(object):
    mongodb_client = MongoClient('mongodb://yeteng:123456@192.168.99.100:53015/yt_test', serverSelectionTimeoutMS=3000)
    SCHEDULER_JOBSTORES = {
        'default': HdyMongoDBJobStore(database='yt_test', client=mongodb_client)
    }

    SCHEDULER_EXECUTORS = {
        'default': {'type': 'threadpool', 'max_workers': 10},  # 默认配置
        'process': {'type': 'processpool', 'max_workers': 2},  # 多进程，用于计算密集型任务
    }

    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': True,
        'max_instances': 1
    }

    SCHEDULER_API_ENABLED = True
