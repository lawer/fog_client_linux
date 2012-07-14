import cuisine as c
import subprocess
from fog_lib import fog_request, fog_response_dict
import functools
import logging
logger = logging.getLogger("fog_client")

FOG_OK = "#!ok"


def check_snapin(instance):
    r = instance("snapins.checkin")
    snapin = fog_response_dict(r)
    return snapin if snapin["status"] == FOG_OK else None


def download_snapin(instance, dirname, snapin):
    dirname_slash = dirname + '/' if dirname[-1] != '/' else dirname 
    filename = dirname_slash + snapin["filename"]
    with open(filename, "wb") as snapin_file:
        r = instance("snapins.file", taskid=snapin["jobtaskid"])
        snapin_file.write(r.content)
    return filename


def exec_snapin(name, snapin):
    with c.mode_local():
        c.file_ensure(name, mode="700")

    line = " ".join([snapin["runwith"], snapin["runwithargs"], 
                    name, snapin["args"]])
    r_code = subprocess.call(line, shell=True)
    return r_code

def confirm_snapin(instance, snapin, return_code):
    r = instance("snapins.checkin", taskid=snapin["jobtaskid"], 
                 exitcode=return_code)
    return r.text == FOG_OK

def install_snapin(instance, snapin, snapin_dir):
        filename = download_snapin(instance, snapin_dir, snapin)
        return_code = exec_snapin(filename, snapin)
        confirm_snapin(instance, snapin, return_code)
        reboot = True if snapin["bounce"] == 1 else False 
        return return_code, return_code == 0, reboot

def client_snapin(mac, conf):
    fog_host = conf.get("GENERAL", "fog_host")
    snapin_dir = conf.get("GENERAL", "snapin_dir")
    
    instance = functools.partial(fog_request, fog_host=fog_host, mac=mac)

    snapin = check_snapin(instance)
    if snapin:
        return_code, action, reboot = install_snapin(instance=instance,
                                                     snapin=snapin,
                                                     snapin_dir=snapin_dir)
        logger.info("Installed " + snapin["filename"] +
                    " with returncode " + str(return_code))
    else:
        logger.info("No snapins to install on mac " + mac)
        action, reboot = False, False
    return action, reboot

    
