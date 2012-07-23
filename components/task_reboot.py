from fog_lib import logged_in
import logging
logger = logging.getLogger("fog_client")

FOG_OK = "#!ok"

def client_task_reboot(client_instance, conf):
    r = client_instance("jobs")
    data = r.text.splitlines()[0]
    if data == FOG_OK:
        if logged_in():
            logger.info("Image task pending, client logged in, not rebooting")
            status, reboot = True, False
        else:
            logger.info("Image task pending, no client logged in, rebooting")
            status, reboot = True, True
    else:
        logger.info("No Image tasks pending.")
        status, reboot = False, False
    return status, reboot