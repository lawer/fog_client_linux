import cuisine as c
import subprocess
from fog_lib import fog_request, fog_response_dict
import logging
logger = logging.getLogger("fog_client")

FOG_OK = "#!ok"


def check_snapin(mac, fog_host):
    r = fog_request("snapins.checkin", fog_host, {"mac": mac})
    snapin = fog_response_dict(r)
    return snapin if snapin["status"] == FOG_OK else None


def download_snapin(mac, fog_host, name, job, dirname):
    r = fog_request("snapins.file", fog_host,
                    {"mac": mac, "taskid": job})
    dirname_slash = dirname + '/' if dirname[-1] != '/' else dirname 
    filename = dirname_slash + name
    with open(filename, "wb") as snapin_file:
        snapin_file.write(r.content)
    return filename


def exec_snapin(name, snapin):
    with c.mode_local():
        c.file_ensure(name, mode="700")

    line = " ".join([snapin["runwith"], snapin["runwithargs"], 
                    name, snapin["args"]])
    r_code = subprocess.call(line, shell=True)
    logger.info("Installed " + snapin["filename"] +
                " with returncode " + str(r_code))
    post_snapin_ok(mac, fog_host, snapin["jobtaskid"], r_code)
    return r_code

def post_snapin_ok(mac, fog_host, taskid, r_code):
    r = fog_request("snapins.checkin", fog_host, 
                    {"mac": mac, "taskid": taskid, "exitcode": r_code})
    return r.text == FOG_OK

def client_snapin(mac, conf):
    fog_host = conf.get("GENERAL", "fog_host")
    snapin_dir = conf.get("GENERAL", "snapin_dir")

    snapin = check_snapin(mac, fog_host)
    if snapin:
        jobid = snapin["jobtaskid"]
        filename = download_snapin(mac, fog_host, snapin["filename"],
                                   jobid, snapin_dir)
        r_code = exec_snapin(filename, snapin)
        reboot = True if snapin["bounce"] == 1 else False 
        return r_code == 0, reboot
    else:
        logger.info("No snapins to install on mac " + mac)
        return False, False
