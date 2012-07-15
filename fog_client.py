#!/usr/bin/env python
import time
import itertools as it
import functools
from components import (client_hostname, client_snapin, 
                        client_task_reboot, client_green_fog)
from fog_lib import get_macs, load_conf, get_logger, shutdown, fog_request


def main():
    logger = get_logger("fog_client")
    macs = get_macs()
    services = [client_hostname, client_snapin, 
                client_task_reboot, client_green_fog]

    conf = load_conf('/etc/fog_client.ini', {"fog_host": "localhost",
                                             "snapin_dir": "/tmp/",
                                             "allow_reboot": "false",
                                             "interval": "5"})
    fog_host = conf.get("GENERAL", "fog_host")
    allow_reboot = conf.getboolean("GENERAL", "allow_reboot")
    interval = conf.getint("GENERAL", "interval")

    logger.info("Service started")
    for mac in macs:
        logger.info("Detected mac: " + mac)

    while True:
        time.sleep(interval)
        for func, mac in it.product(services, macs):
            client_instance = functools.partial(fog_request, 
                                                fog_host=fog_host, 
                                                mac=mac)
            status, reboot = func(client_instance, conf)
            logger.info("Service did changes={status} "
                        "action needed={reboot}".format(
                        status=status, reboot=reboot))
            if allow_reboot and reboot:
                if reboot=="reboot" or reboot==True:
                    shutdown(mode="reboot")
                else:
                    shutdown(mode="halt")


if __name__ == '__main__':
    main()
