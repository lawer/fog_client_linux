import cuisine as c
import logging
from fog_lib import fog_request
logger = logging.getLogger("fog_client")

FOG_OK = "#!ok"

def get_hostname():
    with c.mode_local():
        host = c.run("hostname")
        return host


def set_hostname(host):
    with c.mode_local():
        with c.mode_sudo():
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


def client_hostname(mac, conf):
    fog_host = conf.get("GENERAL", "fog_host")

    client_instance = functools.partial(fog_request, fog_host=fog_host, mac=mac)

    r = client_instance("hostname")
    data = r.text.splitlines()[0]
    try:
        status, hostname = data.split('=')
        if status == FOG_OK:
            return ensure_hostname(hostname)
    except ValueError:
        return False, False
