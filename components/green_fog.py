from fog_lib import FogRequester, shutdown
import datetime
import base64
import logging
logger = logging.getLogger("fog_client")


class GreenFogRequester(FogRequester):
    """docstring for GreenFogRequester"""
    def _handler(self, text):
        if text != '':
            return base64.b64decode(text)
        else:
            raise ValueError("No jobs pending")

    def get_green_fog_data(self):
        text = self.get_data(service="greenfog")
        hour, minute, task_type = self._handler(text).split('@')
        return hour, minute, task_type


class GreenFogTask(object):
    """docstring for GreenFogTask"""
    def __init__(self, hour, minute, task_type):
        super(GreenFogTask, self).__init__()
        self._hour = hour
        self._minute = minute
        self.task_type = "reboot" if task_type == 'r' else 'halt'
        self.time_object = self._construct_time_object()
        self.date, self.hour = self.time_object.isoformat().split('T')

    @property
    def due_now(self):
        hours_to_task = self._hours_to(self.time_object)
        return hours_to_task <= 1 and hours_to_task > 0

    def _construct_time_object(self):
        now = datetime.datetime.now()
        task_time = datetime.datetime(now.year, now.month, now.day,
                                      int(self._hour), int(self._minute), 0)
        return task_time

    def _hours_to(self, task_time):
        interval = task_time - datetime.datetime.now()
        hours = interval.total_seconds() // 3600
        return hours


def client_green_fog(fog_host, mac, allow_reboot):
    fog_server = GreenFogRequester(fog_host=fog_host,
                                   mac=mac)
    status, reboot = False, False
    try:
        hour, minute, task_type = fog_server.get_green_fog_data()
        task = GreenFogTask(hour, minute, task_type)
        if task.due_now:
            logger.info("Green Fog task pending,")
            status, reboot = shutdown(mode=task.task_type,
                                      allow_reboot=allow_reboot)
        else:
            logger.info("Green Fog Task due at " + task.hour)
            status, reboot = False, False
    except IOError as e:
        logger.info(e)
    except ValueError as e:
        logger.info(e)
    return status, reboot
