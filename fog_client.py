#!/usr/bin/env python
"""Client for fog service made in python
Currently only tested in ubuntu 12.04+"""
import cliapp
import filelock

import components
from fog_lib import get_macs, Scheduler

import logging


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

        requests_log = logging.getLogger("requests")
        requests_log.setLevel(logging.WARNING)

        logger.addHandler(handler)

    def _load_settings(self):
        self.fog_host = self.settings["fog_host"]
        self.allow_reboot = self.settings["allow_reboot"]
        self.snapin_dir = self.settings["snapin_dir"]
        self.interval = self.settings["interval"]

    def cmd_snapins(self, args):
        """Downloads and installs the first snapin waiting in the server
           Subsequential runs of the command could be needed.
        """
        self._load_settings()
        return [components.snapins(self.fog_host, mac,
                                   self.snapin_dir, self.allow_reboot)
                for mac in get_macs()]

    def cmd_logins(self, args):
        """Sets in server logins and loguts
        """
        self._load_settings()
        return [components.logins(self.fog_host, mac) for mac in get_macs()]

    def cmd_daemon(self, args):
        """Starts the service in daemon mode.
        By default configuration is loaded from /etc/fog_client.ini.
        """
        self._load_settings()

        arguments = [args]

        commands = [self.subcommands[index] for index in self.subcommands
                    if index not in ("all", "daemon", "help", "help-all")]

        scheduler = Scheduler()
        for command in commands:
            scheduler.schedule(command, self.interval, arguments)

        scheduler.run()

    def cmd_all(self, args):
        """Execs all commands.
        """
        try:
            with filelock.FileLock("/tmp/fog_client.lock", timeout=10):
                self._load_settings()
                arguments = [args]

                commands = [self.subcommands[index]
                            for index in self.subcommands
                            if index not in (
                                "all", "daemon", "help", "help-all"
                            )]

                for command in commands:
                    command(arguments)

        except filelock.FileLockException:
            print "Locked"


if __name__ == '__main__':
    client_app = FogClientApp(version="0.6.4", description="""
Client for fog service made in python

Currently only tested in ubuntu 12.04+""")
    client_app.settings.config_files = ["/etc/fog_client.ini"]
    client_app.run()
