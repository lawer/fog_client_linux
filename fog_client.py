#!/usr/bin/env python
import baker
from components import (client_hostname, client_snapin,
                        client_task_reboot, client_green_fog)
from fog_lib import get_macs, load_conf, get_logger, Scheduler
logger = get_logger("fog_client")


DEFAULTS = {"fog_host": "localhost",
            "snapin_dir": "/tmp/",
            "allow_reboot": "false",
            "interval": "5"}
CONF = load_conf("/etc/fog_client.ini", DEFAULTS)
FOG_HOST = CONF.get("GENERAL", "fog_host")
ALLOW_REBOOT = CONF.getboolean("GENERAL", "allow_reboot")
SNAPIN_DIR = CONF.get("GENERAL", "fog_host")
INTERVAL = CONF.getint("GENERAL", "interval")


@baker.command
def hostname(fog_host=FOG_HOST):
    """Sets local hostname to the value set in fog server"""
    return [client_hostname(fog_host, mac) for mac in get_macs()]


@baker.command
def green_fog(fog_host=FOG_HOST, allow_reboot=ALLOW_REBOOT):
    """Shutdowns or reboots the computer at times set in fog server"""
    return [client_green_fog(fog_host, mac, allow_reboot)
            for mac in get_macs()]


@baker.command
def task_reboot(fog_host=FOG_HOST, allow_reboot=ALLOW_REBOOT):
    """Reboots the computer if there is an imaging task waiting"""
    return [client_task_reboot(fog_host, mac, allow_reboot)
            for mac in get_macs()]


@baker.command
def snapins(fog_host=FOG_HOST, snapin_dir=SNAPIN_DIR,
            allow_reboot=ALLOW_REBOOT):
    """Downloads and installs the first snapin waiting in the server

       Subsequential runs of the command could be needed.
    """
    return [client_snapin(fog_host, mac, snapin_dir, allow_reboot)
            for mac in get_macs()]


@baker.command
def daemon(fog_host=FOG_HOST, snapin_dir=SNAPIN_DIR,
           allow_reboot=ALLOW_REBOOT, interval=INTERVAL):
    """Starts the service in daemon mode.
    By default configuration is loaded from /etc/fog.ini.
    """
    scheduler = Scheduler()
    scheduler.schedule(hostname, interval, {"fog_host": fog_host})
    scheduler.schedule(green_fog, interval, {"fog_host": fog_host,
                                             "allow_reboot": allow_reboot})
    scheduler.schedule(task_reboot, interval, {"fog_host": fog_host,
                                               "allow_reboot": allow_reboot})
    scheduler.schedule(snapins, interval, {"fog_host": fog_host,
                                           "allow_reboot": allow_reboot,
                                           "snapin_dir": snapin_dir})

    scheduler.run()
if __name__ == '__main__':
    baker.run()
