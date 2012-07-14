#!/usr/bin/env python
import logging
import logging.handlers
import time
import itertools as it
from components import client_hostname, client_snapin
from fog_lib import get_macs, load_conf, setup_logger


def main():
    logger = get_logger("fog_client")
    macs = get_macs()
    services = [client_hostname, client_snapin]

    conf = load_conf('/etc/fog_client.ini', {"fog_host": "localhost",
                                             "snapin_dir": "/tmp/"})

    print "service started"
    logger.info("Service started")
    for mac in macs:
        logger.info("Detected mac: " + mac)

    while True:
        time.sleep(5)
        for func, mac in it.product(services, macs)
            func(mac, conf)

if __name__ == '__main__':
    main()
