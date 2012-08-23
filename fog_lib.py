import cuisine as c
import requests
import re
import os
import ConfigParser
import logging
import functools
import baker
import sched
import datetime
import time


class FogRequester(object):
    """Encapsulates the logic for communicating with the fog server

    Returns the text response from the fog server.
    """

    FOG_OK = "#!ok"

    def __init__(self, mac, fog_host):
        super(FogRequester, self).__init__()
        self.mac = mac
        self.fog_host = fog_host

    def get_data(self, service, binary=False, *args, **kwargs):
        try:
            params = {"mac": self.mac}
            params.update(kwargs)

            response = requests.get("http://{}/fog/service/{}.php".format(
                                    self.fog_host, service),
                                    params=params)
            if binary:
                return response.content
            return response.text
        except requests.exceptions.ConnectionError:
            raise IOError("Error communicating with fog server on "
                          + self.fog_host)


class Scheduler(object):
    """Schedules functions por future execution"""
    def __init__(self):
        super(Scheduler, self).__init__()
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def schedule(self, func, interval, args=[], kwargs={}):
        def func_scheduled(self, func, args, kwargs, interval):
            func(*args, **kwargs)
            self.schedule(func, interval, args, kwargs)
        self.scheduler.enter(interval, 1, func_scheduled,
                            (self, func, args, kwargs, interval))

    def run(self):
        self.scheduler.run()


def logged_in():
    """Returns True is an user is logged in.
    At the moment only works on Ubuntu 12.04
    """
    try:
        if ':0' in os.listdir('/var/run/lightdm/root'):
            return True
        else:
            return False
    except OSError:
        return True


def load_conf(filename, defaults={}):
    """Loads a ConfigParser config file.
    If the file doesn't exists its created anew with default values
    """
    conf = ConfigParser.SafeConfigParser(defaults)

    obert = conf.read(filename)

    if not obert:
        with open(filename, 'w') as conf_file:
            conf.add_section('GENERAL')
            conf.write(conf_file)
    return conf


def shutdown(mode="reboot", allow_reboot=False):
    """Shutdowns or reboots the computer if allow reboot == True."""
    if logged_in():
        logging.info("Logged in, not rebooting")
        status, reboot = True, False
    else:
        logging.info("Not logged in, rebooting")
        status, reboot = True, True
        if allow_reboot:
            with c.mode_local():
                with c.mode_sudo():
                    if mode == "reboot":
                        c.run("reboot")
                    else:
                        c.run("halt")
    return status, reboot


def get_macs():
    """Returns all MAC adresses of the NIC cards installed on the computer"""
    mac_re = "([a-fA-F0-9]{2}[:|\-]?){6}"
    mac_re_comp = re.compile(mac_re)
    with c.mode_local():
        ifconfig = c.run("ifconfig")
        macs = (mac_re_comp.search(line).group()
                for line in ifconfig.splitlines()
                if 'HW' in line and 'eth' in line)
        return macs
