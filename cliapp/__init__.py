# Copyright (C) 2011  Lars Wirzenius
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


'''Framework for Unix command line programs

cliapp makes it easier to write typical Unix command line programs, by
taking care of the common tasks they need to do, such as parsing the
command line, reading configuration files, setting up logging,
iterating over lines of input files, and so on.

Homepage: http://liw.fi/cliapp/

'''


__version__ = '1.20140315'


from fmt import TextFormat
from app import Application, AppException
from settings import (Settings, log_group_name, config_group_name,
                      perf_group_name, UnknownConfigVariable)
from runcmd import runcmd, runcmd_unchecked, shell_quote, ssh_runcmd

# The plugin system
from hook import Hook, FilterHook
from hookmgr import HookManager
from plugin import Plugin
from pluginmgr import PluginManager


__all__ = locals()
