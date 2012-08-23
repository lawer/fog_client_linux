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

from cliapp import Plugin


class PluginTests(unittest.TestCase):

    def setUp(self):
        self.plugin = Plugin()
        
    def test_name_is_class_name(self):
        self.assertEqual(self.plugin.name, 'Plugin')

    def test_description_is_empty_string(self):
        self.assertEqual(self.plugin.description, '')

    def test_version_is_zeroes(self):
        self.assertEqual(self.plugin.version, '0.0.0')

    def test_required_application_version_is_zeroes(self):
        self.assertEqual(self.plugin.required_application_version, '0.0.0')

    def test_enable_raises_exception(self):
        self.assertRaises(Exception, self.plugin.enable)

    def test_disable_raises_exception(self):
        self.assertRaises(Exception, self.plugin.disable)

    def test_enable_wrapper_calls_enable(self):
        self.plugin.enable = lambda: setattr(self, 'enabled', True)
        self.plugin.enable_wrapper()
        self.assert_(self.enabled, True)

    def test_disable_wrapper_calls_disable(self):
        self.plugin.disable = lambda: setattr(self, 'disabled', True)
        self.plugin.disable_wrapper()
        self.assert_(self.disabled, True)

