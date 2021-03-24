# coding=UTF-8
"""
__title__ = ''
__author__ = 'Administrator'
__mtime__ = '2021/3/18 0018'
"""
import datetime
import random
import time


def test_1():
    print("start test_1: %s" % datetime.datetime.now())
    print('end test_1: %s' % datetime.datetime.now())


def test_2():
    print("start test_2: %s" % datetime.datetime.now())
    time.sleep(2)
    print('end test_2: %s' % datetime.datetime.now())


# @scheduler.task('cron', id='do_job_2', minute='*')
def test_3():
    print("start test_3: %s" % datetime.datetime.now())
    time.sleep(3)
    print('end test_3: %s' % datetime.datetime.now())


def test_6():
    print("start test_6: %s" % datetime.datetime.now())
    time.sleep(6)
    print('end test_6: %s' % datetime.datetime.now())


def test_9():
    print("start test_9: %s" % datetime.datetime.now())
    time.sleep(9)
    print('end test_9: %s' % datetime.datetime.now())


def test_15():
    print("start test_15: %s" % datetime.datetime.now())
    time.sleep(15)
    print('end test_15: %s' % datetime.datetime.now())


def test_24():
    print("start test_24: %s" % datetime.datetime.now())
    time.sleep(24)
    print('end test_24: %s' % datetime.datetime.now())


def test_39():
    print("start test_39: %s" % datetime.datetime.now())
    time.sleep(39)
    print('end test_39: %s' % datetime.datetime.now())
