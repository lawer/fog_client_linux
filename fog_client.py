#!/usr/bin/env python
import time
import baker
import scheduler
import datetime
import functools
from components import (client_hostname, client_snapin,
                        client_task_reboot, client_green_fog)
from fog_lib import get_macs, load_conf, get_logger, shutdown, fog_request
logger = get_logger("fog_client")


def call(func, fog_host, *args, **kwargs):
    for mac in get_macs():
#        logger.info("Detected mac: " + mac)
        status, reboot = func(fog_host, mac, *args)
        # logger.info("Service did changes={status} "
        #             "action needed={reboot}".format(
        #             status=status, reboot=reboot))
    return status, reboot


@baker.command
def hostname(fog_host="localhost"):
    """Sets local hostname to the value set in fog server"""
    status, reboot = call(client_hostname, fog_host)


@baker.command
def green_fog(fog_host="localhost", allow_reboot=False):
    """Shutdowns or reboots the computer at times set in fog server"""
    status, reboot = call(client_green_fog, fog_host, allow_reboot)


@baker.command
def task_reboot(fog_host="localhost", allow_reboot=False):
    """Reboots the computer if there is an imaging task waiting"""
    status, reboot = call(client_task_reboot, fog_host, allow_reboot)


@baker.command
def snapins(fog_host="localhost", snapin_dir='/tmp', allow_reboot=False):
    """Downloads and installs the first snapin waiting in the server

       Subsequential runs of the command could be needed.
    """
    status, reboot = call(client_snapin, fog_host, snapin_dir, allow_reboot)


@baker.command
def daemon(fog_host="localhost", snapin_dir='/tmp', allow_reboot=False,
           config_file='/etc/fog_client.ini', interval=5):
    """Starts the service in daemon mode.
    By default configuration is loaded from /etc/fog.ini.
    """
    try:
        conf = load_conf(config_file, {"fog_host": "localhost",
                                       "snapin_dir": "/tmp/",
                                       "allow_reboot": "false",
                                       "interval": "5"})
        fog_host = conf.get("GENERAL", "fog_host")
        snapin_dir = conf.get("GENERAL", "fog_host")
        allow_reboot = conf.getboolean("GENERAL", "allow_reboot")
        interval = conf.getint("GENERAL", "interval")
    except:
        logger.error("Configuration couldn't be loaded. Using defaults")

    s = scheduler.Scheduler()
    s.schedule(name="hostname",
               start_time=datetime.datetime.now(),
               calc_next_time=scheduler.every_x_secs(interval),
               func=functools.partial(hostname, fog_host=fog_host))
    s.schedule(name="green_fog",
               start_time=datetime.datetime.now(),
               calc_next_time=scheduler.every_x_secs(interval),
               func=functools.partial(green_fog, fog_host=fog_host,
                                      allow_reboot=allow_reboot))
    s.schedule(name="task_reboot",
               start_time=datetime.datetime.now(),
               calc_next_time=scheduler.every_x_secs(interval),
               func=functools.partial(task_reboot, fog_host=fog_host,
                                      allow_reboot=allow_reboot))
    s.schedule(name="snapins",
               start_time=datetime.datetime.now(),
               calc_next_time=scheduler.every_x_secs(interval),
               func=functools.partial(snapins, fog_host=fog_host,
                                      snapin_dir=snapin_dir,
                                      allow_reboot=allow_reboot))
    s.run()

if __name__ == '__main__':
    baker.run()
