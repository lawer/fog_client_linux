#!/usr/bin/env python
import logging
import logging.handlers
import time
from components import client_hostname
from components import client_snapin
from fog_lib import get_macs, load_conf, setup_logger

def main():
    logger = setup_logger("fog_client")
    macs = get_macs()

    conf = load_conf('/etc/fog_client.ini')
    fog_host = conf.get("GENERAL", "fog_host")
    snapin_dir = conf.get("GENERAL", "snapin_dir")

    print "service started"
    logger.info("Service started")
    for mac in macs:
        logger.info("Detected mac: " + mac)

    while True:
        time.sleep(5)
        for mac in macs:
            client_hostname(mac, fog_host)
            client_snapin(mac, fog_host, snapin_dir)

if __name__ == '__main__':
    main()
