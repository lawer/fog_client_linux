import cuisine as c
import subprocess
from fog_lib import FogRequester, shutdown
import logging


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
            keys_values_processed = (process(x) for x in keys_values)
            snapin_dict = dict(keys_values_processed)
            return snapin_dict
        else:
            raise ValueError("No snapins pending")

    def get_snapin_data(self):
        service = "snapins.checkin"
        text = self.get_data(service=service)
        snapin_dict = self._handler(text)
        return snapin_dict

    def download_snapin(self, snapin):
        data = self.get_data(service="snapins.file",
                             binary=True,
                             taskid=snapin.task_id)
        return data

    def confirm_snapin(self, snapin):
        data = self.get_data(service="snapins.checkin",
                             taskid=snapin.task_id,
                             exitcode=snapin.return_code)
        return data == self.FOG_OK


class Snapin(object):
    """docstring for Snapin"""
    def __init__(self, snapin_dict, snapin_dir, fog_requester):
        super(Snapin, self).__init__()
        self.snapin_dir = snapin_dir
        self.filename = snapin_dict["filename"]
        self.task_id = snapin_dict["jobtaskid"]
        self.args = snapin_dict["args"]
        self.run_with = snapin_dict["runwith"]
        self.run_with_args = snapin_dict["runwithargs"]
        self.reboot = True if snapin_dict["bounce"] == 1 else False
        self.fog_requester = fog_requester
        self.return_code = 0

    @property
    def complete_filename(self):
        if self.snapin_dir[-1] != '/':
            dirname_slash = self.snapin_dir + '/'
        else:
            dirname_slash = self.snapin_dir
        return dirname_slash + self.filename

    def _download(self):
        data = self.fog_requester.download_snapin(self)
        with open(self.complete_filename, "wb") as snapin_file:
            snapin_file.write(data)

    def _execute(self):
        with c.mode_local():
            c.file_ensure(self.complete_filename, mode="700")

        line = " ".join([self.run_with, self.run_with_args,
                        self.complete_filename, self.args])
        r_code = subprocess.call(line, shell=True)
        self.return_code = r_code

    def _confirm(self):
        self.fog_requester.confirm_snapin(self)

    def install(self):
        with c.mode_sudo():
            self._download()
            self._execute()
            self._confirm()


def client_snapin(fog_host, mac, snapin_dir, allow_reboot=False):
    fog_requester = SnapinRequester(fog_host=fog_host, mac=mac)
    action, reboot = False, False
    try:
        snapin_dict = fog_requester.get_snapin_data()
        snapin = Snapin(snapin_dict, snapin_dir, fog_requester)
        snapin.install()
        logging.info("Installed " + snapin.complete_filename +
                     " with returncode " + str(snapin.return_code))
        action, reboot = True, snapin.reboot
        if allow_reboot and reboot:
            shutdown(mode="reboot")
    except IOError as e:
        logging.info(e)
    except ValueError as e:
        logging.info(e)
    return action, reboot
