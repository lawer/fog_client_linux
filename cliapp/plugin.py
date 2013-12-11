# Copyright (C) 2009-2012  Lars Wirzenius
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


'''A generic plugin manager.

The plugin manager finds files with plugins and loads them. It looks
for plugins in a number of locations specified by the caller. To add
a plugin to be loaded, it is enough to put it in one of the locations,
and name it *_plugin.py. (The naming convention is to allow having
other modules as well, such as unit tests, in the same locations.)

'''


import imp
import inspect
import os


class Plugin(object):

    '''Base class for plugins.

    A plugin MUST NOT have any side effects when it is instantiated.
    This is necessary so that it can be safely loaded by unit tests,
    and so that a user interface can allow the user to disable it,
    even if it is installed, with no ill effects. Any side effects
    that would normally happen should occur in the enable() method,
    and be undone by the disable() method. These methods must be
    callable any number of times.

    The subclass MAY define the following attributes:

    * name
    * description
    * version
    * required_application_version

    name is the user-visible identifier for the plugin. It defaults
    to the plugin's classname.

    description is the user-visible description of the plugin. It may
    be arbitrarily long, and can use pango markup language. Defaults
    to the empty string.

    version is the plugin version. Defaults to '0.0.0'. It MUST be a
    sequence of integers separated by periods. If several plugins with
    the same name are found, the newest version is used. Versions are
    compared integer by integer, starting with the first one, and a
    missing integer treated as a zero. If two plugins have the same
    version, either might be used.

    required_application_version gives the version of the minimal
    application version the plugin is written for. The first integer
    must match exactly: if the application is version 2.3.4, the
    plugin's required_application_version must be at least 2 and
    at most 2.3.4 to be loaded. Defaults to 0.

    '''

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def description(self):
        return ''

    @property
    def version(self):
        return '0.0.0'

    @property
    def required_application_version(self):
        return '0.0.0'

    def setup(self):
        '''Setup plugin.

        This is called at plugin load time. It should not yet enable the
        plugin (the ``enable`` method does that), but it might do things
        like add itself into a hook that adds command line arguments
        to the application.

        '''

    def enable_wrapper(self):
        '''Enable plugin.

        The plugin manager will call this method, which then calls the
        enable method. Plugins should implement the enable method.
        The wrapper method is there to allow an application to provide
        an extended base class that does some application specific
        magic when plugins are enabled or disabled.

        '''

        self.enable()

    def disable_wrapper(self):
        '''Corresponds to enable_wrapper, but for disabling a plugin.'''
        self.disable()

    def enable(self):
        '''Enable the plugin.'''
        raise NotImplemented()

    def disable(self):
        '''Disable the plugin.'''
        raise NotImplemented()

