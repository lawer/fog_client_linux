import cuisine as c
import requests
import re
import os
import logging
import logging.handlers

FOG_OK = "#!ok"

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
    rfh = logging.handlers.RotatingFileHandler("/var/log/" + name + ".log",
                                               maxBytes=8192,
                                               backupCount=5,
                                               mode='w')
    ch = logging.StreamHandler()
    formatter = logging.Formatter(fmt="%(levelname)s:%(asctime)s:%(message)s",
                                  datefmt='%d/%m/%Y-%I:%M:%S')
    rfh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(rfh)
    logger.addHandler(ch)
    return logger


def load_conf(filename, defaults={}):
    import ConfigParser
    conf = ConfigParser.SafeConfigParser(defaults)

    obert = conf.read(filename)

    if not obert:
        with open(filename, 'w') as conf_file:
            conf.add_section('GENERAL')
            conf.write(conf_file)
    return conf


def shutdown(mode="reboot"):
    with c.mode_local():
        if mode=="reboot":
            c.run("reboot")
        else:
            c.run("halt") 


def fog_request(service, fog_host, handler=None, *args, **kwargs):
    r = requests.get("http://{}/fog/service/{}.php".format(
                    fog_host, service),
                    params=kwargs)
    if handler is not None:
        return handler(r.text)
    else:
        return r


def fog_response_dict(r):
    status = r.text.splitlines()[0]
    data_dict = {}
    if status == FOG_OK:
        data = r.text.splitlines()[1:]
        data_list = map(lambda x: x.split("="), data)
        data_lower = map(lambda x: (x[0].lower().replace('snapin',''), x[1]), 
                                   data_list)
        data_dict = dict(data_lower)
        print data_dict
    data_dict["status"] = status
    return data_dict


def get_macs():
    mac_re = "([a-fA-F0-9]{2}[:|\-]?){6}"
    mac_re_comp = re.compile(mac_re)
    with c.mode_local():
        ifconfig = c.run("ifconfig")
        macs = [mac_re_comp.search(line).group()
                for line in ifconfig.splitlines()
                if 'HW' in line and 'eth' in line]
        return macs
