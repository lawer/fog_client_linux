#!/usr/bin/env python
import logging
import logging.handlers
import time
from components.hostname import client_hostname
from components.snapins import client_snapin
from fog_lib import get_macs, load_conf


def main():
    macs = get_macs()

    conf = load_conf('/etc/fog_client.ini')
    fog_host = conf.get("GENERAL", "fog_host")
    snapin_dir = conf.get("GENERAL", "snapin_dir")

    logger.info("Service started")
    for mac in macs:
        logger.info("Detected mac: " + mac)

    while True:
        time.sleep(5)
        for mac in macs:
            client_hostname(mac, fog_host)
            client_snapin(mac, fog_host, snapin_dir)

if __name__ == '__main__':
    requests_log = logging.getLogger("requests")
    requests_log.setLevel(logging.WARNING)

    logger = logging.getLogger("fog_client")
    logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler('/var/log/fog.log',
                                                   maxBytes=8192,
                                                   backupCount=5,
                                                   mode='w')
    formatter = logging.Formatter(fmt='%(levelname)s:%(asctime)s:%(message)s',
                                  datefmt='%d/%m/%Y-%I:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    main()
