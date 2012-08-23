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

from cliapp import HookManager, FilterHook


class HookManagerTests(unittest.TestCase):

    def setUp(self):
        self.hooks = HookManager()
        self.hooks.new('foo', FilterHook())
        
    def callback(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def test_has_no_tests_initially(self):
        hooks = HookManager()
        self.assertEqual(hooks.hooks, {})
        
    def test_adds_new_hook(self):
        self.assert_(self.hooks.hooks.has_key('foo'))
        
    def test_adds_callback(self):
        self.hooks.add_callback('foo', self.callback)
        self.assertEqual(self.hooks.hooks['foo'].callbacks, [self.callback])

    def test_removes_callback(self):
        cb_id = self.hooks.add_callback('foo', self.callback)
        self.hooks.remove_callback('foo', cb_id)
        self.assertEqual(self.hooks.hooks['foo'].callbacks, [])

    def test_calls_callbacks(self):
        self.hooks.add_callback('foo', self.callback)
        self.hooks.call('foo', 'bar', kwarg='foobar')
        self.assertEqual(self.args, ('bar',))
        self.assertEqual(self.kwargs, { 'kwarg': 'foobar' })

    def test_call_returns_value_of_callbacks(self):
        self.hooks.new('bar', FilterHook())
        self.hooks.add_callback('bar', lambda data: data + 1)
        self.assertEqual(self.hooks.call('bar', 1), 2)

