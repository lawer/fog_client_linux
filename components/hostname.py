import cuisine as c
from fog_lib import FogRequester
import logging
logger = logging.getLogger("fog_client")


class HostnameRequester(FogRequester):
    """docstring for HostnameRequester"""
    def _handler(self, text):
        if self.FOG_OK in text:
            lines = text.splitlines()
            status, hostname = lines[0].split('=')
            return hostname
        else:
            raise ValueError("Hostname is not registered in fog Server")

    def get_hostname_data(self):
        text = self.get_data(service="hostname")
        return self._handler(text)


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
        with c.mode_sudo():
            set_hostname(host)
        return True, True
    else:
        logger.info("Hostname was not changed")
        return False, False


def client_hostname(fog_host, mac, allow_reboot=False):
    fog_server = HostnameRequester(fog_host=fog_host, mac=mac)
    action, reboot = False, False
    try:
        hostname = fog_server.get_hostname_data()
        action, reboot = ensure_hostname(hostname)
    except IOError as e:
        logger.error(e)
    except ValueError as e:
        logger.error(e)
    finally:
        return action, reboot
