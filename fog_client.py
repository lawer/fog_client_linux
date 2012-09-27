#!/usr/bin/env python
"""Client for fog service made in python
Currently only tested in ubuntu 12.04+"""
import cliapp
import logging
import components
from fog_lib import get_macs, Scheduler


class FogClientApp(cliapp.Application):
    """Class used por cliapp customizations"""
    def add_settings(self):
        self.settings.string(['fog_host'],
                             'Hostname or ip of the fog server (default: '
                             'localhost).',
                             default='localhost')
        self.settings.string(['snapin_dir'],
                             'Directory where snapin files are saved (default:'
                             '/tmp/).',
                             default='/tmp/')
        self.settings.boolean(['allow_reboot'],
                              'Permit reboots or shutdowns if needed (default:'
                              'False).',
                              default=False)
        self.settings.integer(['interval'],
                              'Sets interval between service execution '
                              '(default: 5).',
                              default=5)

    def setup_logging(self):
        "Set up logging"
        cliapp.Application.setup_logging(self)

        logger = logging.getLogger()
        handler = logging.StreamHandler()
        fmt = '%(asctime)s %(levelname)s %(message)s'
        datefmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter(fmt, datefmt)
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    def cmd_hostname(self, args):
        """Sets local hostname to the value saved in fog server"""
        fog_host = self.settings["fog_host"]
        return [components.hostname(fog_host, mac) for mac in get_macs()]

    def cmd_green_fog(self, args):
        """Shutdowns or reboots the computer at times set in fog server"""
        fog_host = self.settings["fog_host"]
        allow_reboot = self.settings["allow_reboot"]
        return [components.green_fog(fog_host, mac, allow_reboot)
                for mac in get_macs()]

    def cmd_task_reboot(self, args):
        """Reboots the computer if there is an imaging task waiting"""
        fog_host = self.settings["fog_host"]
        allow_reboot = self.settings["allow_reboot"]
        return [components.task_reboot(fog_host, mac, allow_reboot)
                for mac in get_macs()]

    def cmd_snapins(self, args):
        """Downloads and installs the first snapin waiting in the server
           Subsequential runs of the command could be needed.
        """
        fog_host = self.settings["fog_host"]
        allow_reboot = self.settings["allow_reboot"]
        snapin_dir = self.settings["snapin_dir"]
        return [components.snapins(fog_host, mac, snapin_dir, allow_reboot)
                for mac in get_macs()]

    def cmd_daemon(self, args):
        """Starts the service in daemon mode.
        By default configuration is loaded from /etc/fog_client.ini.
        """
        interval = self.settings["interval"]
        arguments = [args]

        scheduler = Scheduler()
        scheduler.schedule(self.cmd_hostname, interval, arguments)
        scheduler.schedule(self.cmd_green_fog, interval, arguments)
        scheduler.schedule(self.cmd_task_reboot, interval, arguments)
        scheduler.schedule(self.cmd_snapins, interval, arguments)
        scheduler.run()

if __name__ == '__main__':
    client_app = FogClientApp(version="0.4", description="""
Client for fog service made in python

Currently only tested in ubuntu 12.04+""")
    client_app.settings.config_files = ["/etc/fog_client.ini"]
    client_app.run()
