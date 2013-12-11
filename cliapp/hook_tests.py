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


import unittest

from cliapp import Hook, FilterHook


class HookTests(unittest.TestCase):

    def setUp(self):
        self.hook = Hook()

    def callback(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def test_has_no_callbacks_by_default(self):
        self.assertEqual(self.hook.callbacks, [])

    def test_adds_callback(self):
        self.hook.add_callback(self.callback)
        self.assertEqual(self.hook.callbacks, [self.callback])

    def test_adds_callback_only_once(self):
        self.hook.add_callback(self.callback)
        self.hook.add_callback(self.callback)
        self.assertEqual(self.hook.callbacks, [self.callback])

    def test_calls_callback(self):
        self.hook.add_callback(self.callback)
        self.hook.call_callbacks('bar', kwarg='foobar')
        self.assertEqual(self.args, ('bar',))
        self.assertEqual(self.kwargs, { 'kwarg': 'foobar' })

    def test_removes_callback(self):
        cb_id = self.hook.add_callback(self.callback)
        self.hook.remove_callback(cb_id)
        self.assertEqual(self.hook.callbacks, [])


class FilterHookTests(unittest.TestCase):

    def setUp(self):
        self.hook = FilterHook()

    def callback(self, data, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return data + ['callback']

    def test_returns_argument_if_no_callbacks(self):
        self.assertEqual(self.hook.call_callbacks(['foo']), ['foo'])

    def test_calls_callback_and_returns_modified_data(self):
        self.hook.add_callback(self.callback)
        data = self.hook.call_callbacks([])
        self.assertEqual(data, ['callback'])

    def test_calls_callback_with_extra_args(self):
        self.hook.add_callback(self.callback)
        self.hook.call_callbacks(['data'], 'extra', kwextra='kwextra')
        self.assertEqual(self.args, ('extra',))
        self.assertEqual(self.kwargs, { 'kwextra': 'kwextra' })

