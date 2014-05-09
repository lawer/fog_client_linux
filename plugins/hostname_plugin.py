"""Gets the hostname set in fog server for this host and applys it locally
if needed"""

import logging

import cliapp
from fog_lib import (get_macs, FogRequester, ensure_hostname)


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


class HostnamePlugin(cliapp.Plugin):
    def enable(self):
        self.app.add_subcommand("hostname", self.cmd_hostname)

    def _client_hostname(self, fog_host, mac):
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

    def cmd_hostname(self, args):
        """Sets local hostname to the value saved in fog server"""
        fog_host = self.app.settings["fog_host"]
        return [self._client_hostname(fog_host, mac) for mac in get_macs()]
