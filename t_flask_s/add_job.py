from flask import current_app

from hdy_flask_apschnduler.utils import hdy_add_job
from t_flask_s.run import RUN_SERVER_LIST  # 这个导包会引入current_app


jobs = [
    {'id': 'test_2', 'name': '测试2', 'ip': RUN_SERVER_LIST[0],
     'func': 'task:test_2', 'trigger': 'interval', 'seconds': 10}
]


if __name__ == '__main__':
    """测试后端干预任务"""
    current_app.apscheduler.start(paused=True)
    # res = current_app.apscheduler.get_jobs()

    hdy_add_job(current_app.apscheduler, RUN_SERVER_LIST, jobs)  # 添加任务，封装有特殊处理
    res = current_app.apscheduler.pause_job('test_1')  # 暂停
    res = current_app.apscheduler.resume_job('test_1')  # 恢复
    res = current_app.apscheduler.remove_job('test_3')  # 删除
    res = current_app.apscheduler.run_job('test_15')  # 立即执行一次
    res = current_app.apscheduler.remove_all_jobs()  # 删除所有任务
    print(res)

