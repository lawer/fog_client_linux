import cuisine as c
import subprocess
from fog_lib import fog_request, fog_response_dict
import logging
logger = logging.getLogger("fog_client")

from fog_lib import load_conf
conf = load_conf('/etc/fog_client.ini')
FOG_HOST = conf.get("GENERAL", "fog_host")
SNAPIN_DIR = conf.get("GENERAL", "snapin_dir")
FOG_OK = "#!ok"


def check_snapin(mac):
    r = fog_request("snapins.checkin", {"mac": mac})
    snapin = fog_response_dict(r)
    return snapin if snapin["status"] == FOG_OK else None


def download_snapin(mac, name, job, dirname=SNAPIN_DIR):
    r = fog_request("snapins.file",
                    {"mac": mac, "taskid": job})
    with c.mode_local():
        with c.mode_sudo():
            filename = dirname + name
            with open(filename, "wb") as snapin_file:
                snapin_file.write(r.content)
                return filename


def exec_snapin(name, run_with="", args="",
                run_with_args=""):
    with c.mode_local():
        with c.mode_sudo():
            c.file_ensure(name, mode="700")
            line = " ".join([run_with, run_with_args, name, args])
            print line
            r_code = subprocess.call(line, shell=True)
            return r_code


def client_snapin(mac, fog_host, snapin_dir):
    snapin = check_snapin(mac)
    if snapin:
        jobid = snapin["jobtaskid"]
        filename = download_snapin(mac, snapin["snapinfilename"],
                                   jobid, snapin_dir)
        r_code = exec_snapin(name=filename,
                             run_with=snapin["snapinrunwith"],
                             args=snapin["snapinargs"],
                             run_with_args=snapin["snapinrunwithargs"])
        r = fog_request("snapins.checkin",
                        {"mac": mac, "taskid": jobid, "exitcode": r_code})

        logger.info("Installed " + snapin["snapinfilename"] +
                    " with returncode " + str(r_code))

        if snapin["snapinbounce"] == 1:
            pass  # reboot()
        if r.text == FOG_OK:
            return True
    else:
        logger.info("No snapins to install on mac " + mac)
