"""Gets the hostname set in fog server for this host and applys it locally
if needed"""

import cuisine as c
from fog_lib import FogRequester
import logging


class HostnameRequester(FogRequester):
    """Gets hostname data for fog server"""
    def _handler(self, text):
        """Process data from fog server and returns hostname"""
        if self.FOG_OK in text:
            lines = text.splitlines()
            _, hostname = lines[0].split('=')
            return hostname
        else:
            raise ValueError("Hostname is not registered in fog Server")

    def get_hostname_data(self):
        "Returns hostname saved on fog server"
        text = self.get_data(service="hostname")
        return self._handler(text)


def get_hostname():
    """Return current hostname"""
    with c.mode_local():
        host = c.run("hostname")
        return host.strip()


def set_hostname(host):
    """Sets hostname to :host"""
    with c.mode_local():
        old = get_hostname()
        c.run("hostname " + host)
        c.file_write("/etc/hostname", host)
        hosts_old = c.file_read("/etc/hosts")
        hosts_new = hosts_old.replace(old, host)
        c.file_write("/etc/hosts", hosts_new)
        logging.info("Hostname changed from %s to %s", old, host)


def ensure_hostname(host):
    "Ensures that hostname is :host"
    old = get_hostname()
    if old != host:
        with c.mode_sudo():
            set_hostname(host)
        return True, True
    else:
        logging.info("Hostname was not changed")
        return False, False


def client_hostname(fog_host, mac):
    """Main function for this module"""
    fog_server = HostnameRequester(fog_host=fog_host, mac=mac)
    action, reboot = False, False
    try:
        hostname = fog_server.get_hostname_data()
        action, reboot = ensure_hostname(hostname)
    except IOError as ex:
        logging.error(ex)
    except ValueError as ex:
        logging.error(ex)
    # except Exception as ex:
    #     logging.error(ex)
    return action, reboot
 