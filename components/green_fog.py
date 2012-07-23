from fog_lib import logged_in
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


def has_task(data, ):
    now = datetime.datetime.now()
    hour, minute, task_type = data.split('@')

    task_time = datetime.datetime(now.year, now.month, now.day,
                                  int(hour), int(minute), 0)
    interval = task_time - datetime.datetime.now()
    hours = interval.total_seconds() // 3600

    date_due, hour_due = task_time.isoformat().split('T')
    task = True if hours <= 1 and hours > 0 else False
    return hour_due, task, task_type


def client_green_fog(client_instance, conf):
    success, data = client_instance(service="greenfog", handler=handler)
    if success:
        hour, task, task_type = has_task(data)
        if task:
            if logged_in():
                logger.info("Green task pending, logged in, not rebooting")
                status, reboot = True, False
            else:
                logger.info("Green task pending, not logged in, rebooting")
                status, reboot = True, True
        else:
            logger.info("Task due at " + hour)
            status, reboot = True, False
    else:
        logger.info("No green fog task pending.")
        status, reboot = False, False
    return status, reboot
