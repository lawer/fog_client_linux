from fog_lib import logged_in
from fog_lib import get_client_instance
import datetime
import base64
import logging
logger = logging.getLogger("fog_client")

FOG_OK = "#!ok"


def handler(text):
    if text == '':
        return False, None
    else:
        return True, base64.b64decode(text)


def has_task(data):
    now = datetime.datetime.now()
    hour, minute, task_type = data.split('@')

    task_time = datetime.datetime(now.year, now.month, now.day,
                                  int(hour), int(minute), 0)
    interval = task_time - datetime.datetime.now()
    hours = interval.total_seconds() // 3600

    date_due, hour_due = task_time.isoformat().split('T')
    task = True if hours <= 1 and hours > 0 else False
    task_type = "reboot" if task == 'r' else 'halt'
    return hour_due, task, task_type


def client_green_fog(fog_host, mac, allow_reboot):
    client_instance = get_client_instance(fog_host=fog_host,
                                          mac=mac)
    success, text = client_instance(service="greenfog")
    if success:
        fog_success, task_data = handler(text)
        if fog_success:
            hour, task, task_type = has_task(task_data)
            if task:
                logger.info("Green task pending,")
                if logged_in():
                    logger.info("Logged in, not rebooting")
                    status, reboot = True, False
                else:
                    logger.info("Not logged in, rebooting")
                    status, reboot = True, True
                    if allow_reboot:
                        shutdown(mode=task_type)
            else:
                logger.info("Task due at " + hour)
                status, reboot = True, False
        else:
            logger.info("No green fog task pending.")
            status, reboot = False, False
    else:
        logger.info("Error communicating with fog server on " + fog_host)
        status, reboot = False, False
    return status, reboot
