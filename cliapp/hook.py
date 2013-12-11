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


'''Hooks with callbacks.

In order to de-couple parts of the application, especially when plugins
are used, hooks can be used. A hook is a location in the application
code where plugins may want to do something. Each hook has a name and
a list of callbacks. The application defines the name and the location
where the hook will be invoked, and the plugins (or other parts of the
application) will register callbacks.

'''


class Hook(object):

    '''A hook.'''

    def __init__(self):
        self.callbacks = []

    def add_callback(self, callback):
        '''Add a callback to this hook.

        Return an identifier that can be used to remove this callback.

        '''

        if callback not in self.callbacks:
            self.callbacks.append(callback)
        return callback

    def call_callbacks(self, *args, **kwargs):
        '''Call all callbacks with the given arguments.'''
        for callback in self.callbacks:
            callback(*args, **kwargs)

    def remove_callback(self, callback_id):
        '''Remove a specific callback.'''
        if callback_id in self.callbacks:
            self.callbacks.remove(callback_id)


class FilterHook(Hook):

    '''A hook which filters data through callbacks.

    Every hook of this type accepts a piece of data as its first argument
    Each callback gets the return value of the previous one as its
    argument. The caller gets the value of the final callback.

    Other arguments (with or without keywords) are passed as-is to
    each callback.

    '''

    def call_callbacks(self, data, *args, **kwargs):
        for callback in self.callbacks:
            data = callback(data, *args, **kwargs)
        return data

