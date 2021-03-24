import socket


def get_host_ip():
    """利用UDP协议获取本地ip"""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        if s:
            s.close()
    return ip


def hdy_add_job(hdy_scheduler, run_server_list, jobs):
    """校验ip，添加job，统一的入口"""
    host_ip = get_host_ip()
    if host_ip not in run_server_list:
        raise Exception('%s not in ip_list, please check the config!' % host_ip)

    for job in jobs:
        job['replace_existing'] = True
        hdy_scheduler.add_job(**job)
