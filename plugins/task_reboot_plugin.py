import logging

import cliapp
from fog_lib import FogRequester, shutdown, get_macs


class TaskRebootRequester(FogRequester):
    """docstring for HostnameRequester"""
    def _handler(self, text):
        data = text.splitlines()[0]
        if self.FOG_OK in data:
            return True
        raise ValueError("No Image tasks pending.")

    def get_task_reboot_data(self):
        text = self.get_data(service="jobs")
        return self._handler(text)


class TaskRebootPlugin(cliapp.Plugin):
    def enable(self):
        self.app.add_subcommand("task_reboot", self.cmd_task_reboot)

    def _client_task_reboot(self, fog_host, mac, allow_reboot):
        fog_server = TaskRebootRequester(fog_host=fog_host,
                                         mac=mac)
        status, reboot = False, False
        try:
            task = fog_server.get_task_reboot_data()
            if task:
                status, reboot = shutdown(mode=reboot,
                                          allow_reboot=allow_reboot)

        except IOError as e:
            logging.info(e)
        except ValueError as e:
            logging.info(e)
        return status, reboot

    def cmd_task_reboot(self, args):
        """Reboots the computer if there is an imaging task waiting"""
        fog_host = self.app.settings["fog_host"]
        allow_reboot = self.app.settings["allow_reboot"]
        return [self._client_task_reboot(fog_host, allow_reboot, mac)
                for mac in get_macs()]
