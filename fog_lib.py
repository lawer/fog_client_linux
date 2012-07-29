import cuisine as c
import requests
import re
import os
import ConfigParser
import logging
import logging.handlers
import functools
import baker
logger = logging.getLogger("fog_client")

FOG_OK = "#!ok"


def get_client_instance(mac, fog_host):
    client_instance = functools.partial(fog_request,
                                        fog_host=fog_host,
                                        mac=mac)
    return client_instance


def logged_in():
    try:
        if ':0' in os.listdir('/var/run/lightdm/root'):
            return True
        else:
            return False
    except OSError:
        return True


def get_logger(name):
    requests_log = logging.getLogger("requests")
    requests_log.setLevel(logging.WARNING)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt="%(levelname)s:%(asctime)s:%(message)s",
                                  datefmt='%d/%m/%Y-%I:%M:%S')
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    filename = "/var/log/" + name + ".log"
    try:
        rfh = logging.handlers.RotatingFileHandler(filename,
                                                   maxBytes=8192,
                                                   backupCount=5,
                                                   mode='w')
        rfh.setFormatter(formatter)
        logger.addHandler(rfh)

    except IOError:
        logging.error("Can't open %s, logging only to stdout" % (filename))
    return logger


def load_conf(filename, defaults={}):
    conf = ConfigParser.SafeConfigParser(defaults)

    obert = conf.read(filename)

    if not obert:
        with open(filename, 'w') as conf_file:
            conf.add_section('GENERAL')
            conf.write(conf_file)
    return conf


def shutdown(mode="reboot", allow_reboot=False):
    if logged_in():
        logger.info("Logged in, not rebooting")
        status, reboot = True, False
    else:
        logger.info("Not logged in, rebooting")
        status, reboot = True, True
        if allow_reboot:
            with c.mode_local():
                if mode == "reboot":
                    c.run("reboot")
                else:
                    c.run("halt")
    return status, reboot


def fog_request(service, fog_host, handler=None, *args, **kwargs):
    try:
        r = requests.get("http://{}/fog/service/{}.php".format(
                         fog_host, service),
                         params=kwargs)
        return r.text
    except requests.exceptions.ConnectionError:
        logger.error("Error connecting to fog server at" + fog_host)
        raise IOError


def get_macs():
    mac_re = "([a-fA-F0-9]{2}[:|\-]?){6}"
    mac_re_comp = re.compile(mac_re)
    with c.mode_local():
        ifconfig = c.run("ifconfig")
        macs = [mac_re_comp.search(line).group()
                for line in ifconfig.splitlines()
                if 'HW' in line and 'eth' in line]
        return macs
