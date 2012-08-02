import cuisine as c
import subprocess
from fog_lib import FogRequester
import functools
import logging
logger = logging.getLogger("fog_client")


class SnapinRequester(FogRequester):
    """docstring for SnapinRequester"""
    def _handler(self, text):
        def process(x):
            key = x[0].lower().replace('snapin', '')
            value = x[1]
            return key, value

        lines = text.splitlines()
        status, data = lines[0], lines[1:]
        if status == self.FOG_OK:
            keys_values = (element.split("=") for element in data)
            keys_values_processed = (process(x) for x in data_list)
            snapin_dict = dict(keys_values_processed)
            return snapin_dict
        else:
            raise ValueError("No snapins pending")

    def get_data(self):
        service = "snapins.checkin"
        text = super(SnapinRequester, self).get_data(service=service)
        snapin_dict = self._handler(text)

    def download_snapin(self, snapin):
        with open(snapin.complete_filename, "wb") as snapin_file:
            data = super(SnapinRequester, self).get_data(
                service="snapins.file",
                taskid=snapin.task_id
            )
            snapin_file.write(data)
        return filename


class Snapin(object):
    """docstring for Snapin"""
    def __init__(self, snapin_dict, snapin_dir, fog_requester):
        super(Snapin, self).__init__()
        self.snapin_dir = snapin_dir
        self.snapin_dict = snapin_dict
        self.filename = snapin_dict["filename"]
        self.task_id = snapin_dict["jobtaskid"]
        self.args = snapin_dict["args"]
        self.run_with = snapin_dict["runwith"]
        self.run_with_args = snapin_dict["runwithargs"]
        self.reboot = True if snapin_dict["bounce"] == 1 else False
        self.fog_requester = fog_requester

    @property
    def complete_filename(self):
        if self.snapin_dir[-1] != '/':
            dirname_slash = self.snapin_dir + '/'
        else:
            dirname_slash = self.snapin_dir
        return dirname_slash + self.filename

    def download(self):
        self.fog_requester.download_snapin(snapin)

    def execute(self):
        with c.mode_local():
            c.file_ensure(self.complete_filename, mode="700")

        line = " ".join([self.run_with, self.run_with_args,
                        self.complete_filename, self.args])
        r_code = subprocess.call(line, shell=True)
        return r_code

    def confirm(self):
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
    fog_server = SnapinRequester(fog_host=fog_host, mac=mac)
    try:
        snapin_dict = fog_server.get_data()
        snapin = Snapin(snapin_dict, snapin_dir, fog_server)
    #   return_code, action, reboot = install_snapin(instance=client_instance,
    #                                                  snapin=snapin,
    #                                                  snapin_dir=snapin_dir)
    #     logger.info("Installed " + snapin["filename"] +
    #                 " with returncode " + str(return_code))
    # else:
    #     logger.info("No snapins to install")
    #     action, reboot = False, False
    except IOError as e:
        logger.info(e)
        action, reboot = False, False
    except ValueError as e:
        logger.info(e)
        action, reboot = False, False
    return action, reboot
