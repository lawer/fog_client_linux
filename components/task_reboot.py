from fog_lib import FogRequester, shutdown
import logging
logger = logging.getLogger("fog_client")


class TaskRebootRequester(FogRequester):
    """docstring for HostnameRequester"""
    def _handler(self, text):
        data = text.splitlines()[0]
        if self.FOG_OK in data:
            return True
        else:
            return False

    def get_data(self):
        text = super(TaskRebootRequester, self).get_data(service="jobs")
        return self._handler(text)


def client_task_reboot(fog_host, mac, allow_reboot):
    fog_server = TaskRebootRequester(fog_host=fog_host,
                                     mac=mac)
    try:
        if fog_server.get_data():
            shutdown(mode=reboot, allow_reboot=allow_reboot)
        else:
            logger.info("No Image tasks pending.")
            status, reboot = False, False
    except IOError:
        logger.info("Error communicating with fog server on " + fog_host)
        status, reboot = False, False
    return status, reboot
