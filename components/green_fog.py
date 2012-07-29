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


def construct_time_object(hour, minute):
    now = datetime.datetime.now()
    task_time = datetime.datetime(now.year, now.month, now.day,
                                  int(hour), int(minute), 0)
    return task_time


def hours_to_task(task_time):
    interval = task_time - datetime.datetime.now()
    hours = interval.total_seconds() // 3600
    return hours


def process_task_data(data):
    hour, minute, task_type = data.split('@')

    task_time = construct_time_object(hour, minute)
    hours = hours_to_task(task_time)

    date_due, hour_due = task_time.isoformat().split('T')
    task = True if hours <= 1 and hours > 0 else False
    task_type = "reboot" if task == 'r' else 'halt'

    return task, task_type, hour_due


def client_green_fog(fog_host, mac, allow_reboot):
    client_instance = get_client_instance(fog_host=fog_host,
                                          mac=mac)
    try:
        fog_data = client_instance(service="greenfog")
        fog_success, task_data = handler(fog_data)
        if fog_success:
            task, task_type, hour = process_task_data(task_data)
            if task:
                logger.info("Green task pending,")
                status, reboot = shutdown(mode=task_type,
                                          allow_reboot=allow_reboot)
            else:
                logger.info("Task due at " + hour)
                status, reboot = True, False
        else:
            logger.info("No green fog task pending.")
            status, reboot = False, False
    except IOError:
        logger.info("Error communicating with fog server on " + fog_host)
        status, reboot = False, False
    return status, reboot
