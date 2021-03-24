import socket
from flask import Flask

from hdy_flask_apschnduler.hdy_scheduler import HdyAPScheduler
from hdy_flask_apschnduler.utils import get_host_ip, hdy_add_job
from t_flask_s.config import Config
RUN_SERVER_LIST = ['192.168.10.7', '127.0.0.1']

jobs = [
    {'id': 'test_1', 'name': '测试1', 'ip': RUN_SERVER_LIST[0],
     'func': 'task:test_1', 'trigger': 'interval', 'seconds': 20},

    {'id': 'test_3', 'name': '测试3', 'ip': RUN_SERVER_LIST[0], 'executor': 'process',
     'func': 'task:test_3', 'trigger': 'interval', 'seconds': 4},

    {'id': 'test_6', 'name': '测试6', 'ip': RUN_SERVER_LIST[0],
     'func': 'task:test_6', 'trigger': 'interval', 'seconds': 10},

    {'id': 'test_9', 'name': '测试9', 'ip': RUN_SERVER_LIST[0],
     'func': 'task:test_9', 'trigger': 'interval', 'seconds': 10},

    {'id': 'test_15', 'name': '每天0点、8点到23点，每个小时执行一次测试15', 'ip': RUN_SERVER_LIST[0],
     'func': 'task:test_15', 'trigger': 'cron', 'hour': '0,8-23', 'minute': 0},

    {'id': 'test_24', 'name': '每分钟的15秒执行测试24', 'ip': RUN_SERVER_LIST[1],
     'func': 'task:test_24', 'trigger': 'cron', 'second': 15},


    {'id': 'test_39', 'name': '每个小时的5-59分，每分钟执行测试39', 'ip': RUN_SERVER_LIST[0],
     'func': 'task:test_39', 'trigger': 'cron', 'minute': '5-59'},
]


hdy_scheduler = HdyAPScheduler()
app = Flask(__name__)
app.config.from_object(Config())
hdy_scheduler.init_app(app)
ctx = app.app_context()
ctx.push()

if __name__ == '__main__':
    # 绑定一个无用端口，防止任务重复启动
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 47200))
    except socket.error:
        print("!!!scheduler already started, DO NOTHING")
    else:
        hdy_add_job(hdy_scheduler, RUN_SERVER_LIST, jobs)
        hdy_scheduler.start()
        app.run()
