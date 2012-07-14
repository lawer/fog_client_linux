import cuisine as c
import requests
import re
import logging

def setup_logger(name):
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


def load_conf(filename):
    import ConfigParser
    conf = ConfigParser.SafeConfigParser({"fog_host": "localhost",
                                          "snapin_dir": "/tmp/"})

    obert = conf.read('/etc/fog_client.ini')

    if not obert:
        with open('/etc/fog_client.ini', 'w') as conf_file:
            conf.add_section('GENERAL')
            conf.write(conf_file)
    return conf

conf = load_conf('/etc/fog_client.ini')
FOG_HOST = conf.get("GENERAL", "fog_host")
SNAPIN_DIR = conf.get("GENERAL", "snapin_dir")
FOG_OK = "#!ok"


def reboot():
    with c.mode_local():
        with c.mode_sudo():
            c.run("reboot")


def fog_request(service, args=None, fog_host=FOG_HOST):
    r = requests.get("http://%s/fog/service/%s.php" % (fog_host, service),
                     params=args)
    return r


def fog_response_dict(r):
    status = r.text.splitlines()[0]
    data_dict = {}
    if status == FOG_OK:
        data = r.text.splitlines()[1:]
        data_list = map(lambda x: x.split("="), data)
        data_lower = map(lambda x: (x[0].lower(), x[1]), data_list)
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
                if 'HW' in line]
        return macs
