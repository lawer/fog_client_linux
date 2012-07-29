from fog_lib import logged_in, get_client_instance
import logging
logger = logging.getLogger("fog_client")

FOG_OK = "#!ok"


def client_task_reboot(fog_host, mac, allow_reboot):
    client_instance = get_client_instance(fog_host=fog_host,
                                          mac=mac)
    try:
        text = client_instance("jobs")
        data = text.splitlines()[0]
        if data == FOG_OK:
            shutdown(mode=reboot, allow_reboot=allow_reboot)
        else:
            logger.info("No Image tasks pending.")
            status, reboot = False, False
    except IOError:
        logger.info("Error communicating with fog server on " + fog_host)
        status, reboot = False, False
    return status, reboot
