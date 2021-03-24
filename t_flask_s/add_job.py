from flask import current_app

from hdy_flask_apschnduler.utils import hdy_add_job
from t_flask_s.run import RUN_SERVER_LIST  # 这个导包会引入current_app


jobs = [
    {'id': 'test_2', 'name': '测试2', 'ip': RUN_SERVER_LIST[0],
     'func': 'task:test_2', 'trigger': 'interval', 'seconds': 10}
]


if __name__ == '__main__':
    """测试动态添加任务，后端干预任务"""
    hdy_add_job(current_app.apscheduler, RUN_SERVER_LIST, jobs)
    current_app.apscheduler.start(paused=True)

    res = current_app.apscheduler.get_job(id='test_1')
    print(res.__getstate__())
    res = current_app.apscheduler.get_jobs()
    res = current_app.apscheduler.pause_job('test_1')
    res = current_app.apscheduler.resume_job('test_1')
    res = current_app.apscheduler.remove_job('test_2')
    res = current_app.apscheduler.remove_job('test_3')
    res = current_app.apscheduler.run_job('test_15')  # 立即执行一次
    res = current_app.apscheduler.remove_all_jobs()
    print(res)

