import cuisine as c
import logging
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


def handler(text):
    if FOG_OK not in text:
        return False, None
    else:
        lines = text.splitlines()
        status, hostname = lines[0].split('=')
        return True, hostname


def client_hostname(client_instance, conf):
    success, hostname = client_instance(service="hostname",
                                        handler=handler)
    if success:
        return ensure_hostname(hostname)
    else:
        return False, False
