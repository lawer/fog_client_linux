import cuisine as c
import subprocess
from fog_lib import get_client_instance
import functools
import logging
logger = logging.getLogger("fog_client")

FOG_OK = "#!ok"


def snapin_from_response(text):
    split_list = lambda lst: (lst[0], lst[1:])
    status, data = split_list(text.splitlines())
    data_dict = {}
    if status == FOG_OK:
        data_list = map(lambda x: x.split("="), data)
        data_lower = map(lambda x: (x[0].lower().replace('snapin', ''), x[1]),
                         data_list)
        data_dict = dict(data_lower)
        print data_dict
    data_dict["status"] = status
    return data_dict


def get_snapin(client_instance):
    try:
        result = client_instance("snapins.checkin")
        snapin = snapin_from_response(result)
        if snapin["status"] == FOG_OK:
            return snapin
    except IOError:
        return None


def download_snapin(client_instance, dirname, snapin):
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
    succes, text = instance("snapins.checkin", taskid=snapin["jobtaskid"],
                            exitcode=return_code)
    return text == FOG_OK


def install_snapin(client_instance, snapin, snapin_dir):
        filename = download_snapin(client_instance, snapin_dir, snapin)
        return_code = exec_snapin(filename, snapin)
        confirm_snapin(client_instance, snapin, return_code)
        reboot = True if snapin["bounce"] == 1 else False
        return return_code, return_code == 0, reboot


def client_snapin(fog_host, mac, snapin_dir, allow_reboot=False):
    client_instance = get_client_instance(fog_host=fog_host,
                                          mac=mac)
    snapin = get_snapin(client_instance)
    if snapin:
        return_code, action, reboot = install_snapin(instance=client_instance,
                                                     snapin=snapin,
                                                     snapin_dir=snapin_dir)
        logger.info("Installed " + snapin["filename"] +
                    " with returncode " + str(return_code))
    else:
        logger.info("No snapins to install on mac")
        action, reboot = False, False
    return action, reboot
