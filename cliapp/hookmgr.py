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


class HookManager(object):

    '''Manage the set of hooks the application defines.'''

    def __init__(self):
        self.hooks = {}

    def new(self, name, hook):
        '''Add a new hook to the manager.

        If a hook with that name already exists, nothing happens.

        '''

        if name not in self.hooks:
            self.hooks[name] = hook

    def add_callback(self, name, callback):
        '''Add a callback to a named hook.'''
        return self.hooks[name].add_callback(callback)

    def remove_callback(self, name, callback_id):
        '''Remove a specific callback from a named hook.'''
        self.hooks[name].remove_callback(callback_id)

    def call(self, name, *args, **kwargs):
        '''Call callbacks for a named hook, using given arguments.'''
        return self.hooks[name].call_callbacks(*args, **kwargs)

