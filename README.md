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