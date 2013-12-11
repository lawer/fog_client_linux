from fog_lib import FogRequester, shutdown
import logging


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


def client_task_reboot(fog_host, mac, allow_reboot):
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
