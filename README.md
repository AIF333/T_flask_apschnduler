##### 说明：        

* 通过继承和调整部分方法，使flask_apschnduler支持分布式，动态修改mongo表任务对应的ip可支持任务自动分发到对应的机器

##### 实现原理：

* 增加ip字段，判断配置的ip是否和服务器真实ip一致，如果是则可以执行定时任务

##### 局限：   

* 基于 Flask-APScheduler==1.12.1 APScheduler==3.7.0 版本
* SCHEDULER_JOBSTORES只支持mongodb的存储，其他类型都不支持



##### 代码说明：
* hdy_flask_apschnduler
  * hdy_scheduler.py   为对源码的继承和修改，让支持ip字段
* t_flask_s
  * run.py  主启动脚本
  * add_job.py 测试动态添加任务，修改任务状态
  * config.py  配置文件，里面记录了mongodb的设置信息，需要自己调整
* task 测试的任务



**其他说明：**

* 在实际的项目里，由于定时任务只是一个功能模块，在启动时可能会有current_app未绑定，或者多线程下找不到current_app，解决参考：

* ```python
  # coding=UTF-8
  """
  __title__ = '服务端定时任务调用方法'
  __author__ = 'yeteng'
  __mtime__ = '2021/3/30 0030'
  """
  
  import init_environ  # @UnusedImport
  import datetime
  import socket
  import time
  
  from flask import current_app as app
  
  from micserver.exapscheduler.tasks.clean_data import clean_expired_data
  from micserver.exapscheduler.tasks.task_yt import test_1, test_3, test_6, test_9, test_15, test_24, test_39
  
  """说明：
  一、id必须唯一，建议用func名; 如果任务是第一次生成，则ip默认是生成任务的主机ip
  
  二、所有定时任务都放在 micserver/exapscheduler/scheduler_tasks 下
  
  三、支持三种trigger调度：
      interval 按时间间隔执行：
          eg: 'seconds': 20  # 每隔20s执行
          支持参数：weeks, days, hours, minutes, 其他详细参考 class IntervalTrigger(BaseTrigger):
          说明：任务第一次启动时是不会立即执行的，如：'seconds': 20，则是启动后20s才开始运行
               如果需要启动时立即运行可以指定： next_run_time=datetime.datetime.now()
  
      cron 定时执行：
          eg: 'hour': 22, 'minute': 30  # 每天22:30分执行
          支持参数：year, month, day, week, day_of_week, hour, minute, second, 其他详细参考 class CronTrigger(BaseTrigger):
          说明： day_of_week 值[0-6] == [周一到周日]
  
      date 指定时间运行一次(不常用)：
          eg: run_date=datetime.datetime.now()  # 立即执行一次
              run_date=datetime(2021, 11, 6, 16, 30, 5)  # 指定时间运行一次， 其他详细参考 class DateTrigger(BaseTrigger):
  
  四、executor指定：
      默认不配置，用多线程执行，如果是计算型或时效性高的任务可以配置 'executor': 'process'
      说明： 配置process, 一台服务器不要超过3个, 建议增加启动等待时间(10s, window测试默认1s可能不够) 'misfire_grace_time': 5
      
  五、配置例子：
  jobs = [
      {'id': 'test_1', 'name': '每隔5s执行测试1,并传入两个参数',
       'func': test_1, 'args': ['hello', 'word'], 'trigger': 'interval', 'seconds': 5},
  
      {'id': 'test_3', 'name': '每分钟的10s执行测试3',
       'func': test_3, 'trigger': 'cron', 'second': 10},
  
      {'id': 'test_6', 'name': '每隔10s测试6(多进程)', 'executor': 'process',
       'func': test_6, 'trigger': 'interval', 'seconds': 30, 'misfire_grace_time': 5},
  
      {'id': 'test_9', 'name': '每隔10s测试9',
       'func': test_9, 'trigger': 'interval', 'seconds': 10},
  
      {'id': 'test_15', 'name': '每天0点、8点到23点，每个小时执行一次测试15',
       'func': test_15, 'trigger': 'cron', 'hour': '0,8-23', 'minute': 0},
  
      {'id': 'test_24', 'name': '每分钟的15秒执行测试24,服务器启动时立即执行一次',
       'func': test_24, 'trigger': 'cron', 'second': 15, 'next_run_time': datetime.datetime.now()},
  
      {'id': 'test_39', 'name': '每个小时的5-59分，每分钟执行测试39',
       'func': test_39, 'trigger': 'cron', 'minute': '5-59'}
  ]
  """
  
  jobs = [
      {'id': 'clean_expired_data', 'name': '每天凌晨1点清理过期无效数据', 'executor': 'process',
       'func': clean_expired_data, 'trigger': 'cron', 'hour': 1, 'minute': 0, 'misfire_grace_time': 5},
  ]
  
  
  if __name__ == '__main__':
      # 绑定一个无用端口，防止任务重复启动
      try:
          sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          sock.bind(("127.0.0.1", 47200))
      except socket.error:
          print("!!!scheduler already started, DO NOTHING")
      else:
          # 很重要，不然任务在新的线程或进程下没有上下文环境
          with app.app_context():
              for job in jobs:
                  app.apscheduler.hdy_add_job(job)
              app.apscheduler.hdy_start(main_start=True)
              while True:
                  time.sleep(10)
  
  ```

  