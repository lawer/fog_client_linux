import cuisine as c
from fog_lib import get_client_instance
import logging
logger = logging.getLogger("fog_client")

FOG_OK = "#!ok"


def get_hostname():
    with c.mode_local():
        host = c.run("hostname")
        return host


def set_hostname(host):
    with c.mode_local():
        old = get_hostname()
        c.run("hostname " + host)
        c.file_write("/etc/hostname", host)
        hosts_old = c.file_read("/etc/hosts")
        hosts_new = hosts_old.replace(old, host)
        c.file_write("/etc/hosts", hosts_new)
        logger.info("Hostname changed from %s to %s" % (old, host))


def ensure_hostname(host):
    old = get_hostname()
    if old != host:
        set_hostname(host)
        return True, True
    else:
        logger.info("Hostname was not changed")
        return False, False


def handler(text):
    if FOG_OK in text:
        lines = text.splitlines()
        status, hostname = lines[0].split('=')
        return True, hostname
    else:
        return False, None


def client_hostname(fog_host, mac, allow_reboot=False):
    client_instance = get_client_instance(fog_host=fog_host,
                                          mac=mac)
    success, text = client_instance(service="hostname")
    if success:
        fog_success, hostname = handler(text)
        if fog_success:
            return ensure_hostname(hostname)
    else:
        logger.error("Error communicating with fog server on " + fog_host)
    return False, False
