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


__version__ = '1.20120630'


from settings import Settings
from runcmd import runcmd, runcmd_unchecked
from app import Application, AppException

# The plugin system
from hook import Hook, FilterHook
from hookmgr import HookManager
from plugin import Plugin
from pluginmgr import PluginManager


__all__ = locals()
