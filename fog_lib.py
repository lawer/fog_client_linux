"""Utility code for fog_client"""
import cuisine as c
import requests
import re
import logging
import sched
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

    def get_data(self, service, binary=False, **kwargs):
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
    """Schedules functions per future execution"""
    def __init__(self):
        super(Scheduler, self).__init__()
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def schedule(self, func, interval, args=None, kwargs=None):
        args = args or []
        kwargs = kwargs or {}

        def func_scheduled(self, func, args, kwargs, interval):
            func(*args, **kwargs)
            self.schedule(func, interval, args, kwargs)
        self.scheduler.enter(interval, 1, func_scheduled,
                            (self, func, args, kwargs, interval))

    def run(self):
        self.scheduler.run()


def file_read(filename):
    contents = open(filename, 'r').read()
    return contents


def file_write(filename, contents):
    f = open(filename, 'w')
    f.write(contents)


def file_update(filename, updater):
    with open(filename, 'r') as f_r:
        contents = f_r.read()
        updated = updater(contents)
    with open(filename, 'w') as f_w:
        f_w.write(updated)


def obtain_logins():
    from logsparser.lognormalizer import LogNormalizer as LN

    normalizer = LN('/usr/local/share/logsparser/normalizers')
    auth_logs = open('/var/log/auth.log', 'r')

    logs = [{'raw': l} for l in auth_logs]
    map(normalizer.lognormalize, logs)

    logins = (log for log in logs
              if log.get('action') == 'open'
              or log.get('action') == 'close')

    logins_users = (log for log in logins
                    if log.get('program') != 'sudo'
                    and log.get('program') != 'cron')

    return logins_users


def logged_in():
    """Returns True is an user is logged in.
    At the moment only works on Ubuntu 12.04
    """
    try:
        logins_ligthdm = (log for log in obtain_logins()
                          if log.get('program') == 'lightdm'
                          and log.get('user') != 'lightdm')
        reversed_logins = reversed(list(logins_ligthdm))
        for log in reversed_logins:
            if log.get('action') == 'open':
                return True
            else:
                return False
    except OSError:
        return True


def shutdown(mode="reboot", allow_reboot=True):
    """Shutdowns or reboots the computer if allow reboot == True."""
    allow_reboot=False
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
                        c.run("reboot -f")
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
                if 'ether' in line)
        return macs

def get_hostname():
    """Return current hostname"""
    with c.mode_local():
        host = c.run("hostname")
        return host.strip()


def set_hostname(host):
    """Sets hostname to :host"""
    def updater(contents):
        return contents.replace(old, host)
    with c.mode_local():
        old = get_hostname()
        c.run("hostname " + host)
        file_write("/etc/hostname", host)
        file_update("/etc/hosts", updater=updater)
        logging.info("Hostname changed from %s to %s", old, host)


def ensure_hostname(host):
    "Ensures that hostname is :host"
    old = get_hostname()
    if old != host:
        with c.mode_sudo():
            set_hostname(host)
            c.run("install-salt")
        return True, True
    else:
        logging.info("Hostname was not changed")
        return False, False
