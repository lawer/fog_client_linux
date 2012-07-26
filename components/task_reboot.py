from fog_lib import logged_in, get_client_instance
import logging
logger = logging.getLogger("fog_client")

FOG_OK = "#!ok"


def client_task_reboot(fog_host, mac, allow_reboot):
    client_instance = get_client_instance(fog_host=fog_host,
                                          mac=mac)
    success, text = client_instance("jobs")
    if success:
        data = text.splitlines()[0]
        if data == FOG_OK:
            logger.info("Image task pending")
            if logged_in():
                logger.info("Client logged in, not rebooting")
                status, reboot = True, False
            else:
                logger.info("No client logged in, rebooting")
                status, reboot = True, True
                if allow_reboot:
                    shutdown(mode=reboot)
        else:
            logger.info("No Image tasks pending.")
            status, reboot = False, False
    else:
        logger.info("Error communicating with fog server on " + fog_host)
        status, reboot = False, False
    return status, reboot
