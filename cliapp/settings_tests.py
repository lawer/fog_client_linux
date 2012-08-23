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


import optparse
import StringIO
import sys
import unittest

import cliapp


class SettingsTests(unittest.TestCase):

    def setUp(self):
        self.settings = cliapp.Settings('appname', '1.0')
        
    def test_has_progname(self):
        self.assertEqual(self.settings.progname, 'appname')
        
    def test_sets_progname(self):
        self.settings.progname = 'foo'
        self.assertEqual(self.settings.progname, 'foo')
        
    def test_has_version(self):
        self.assertEqual(self.settings.version, '1.0')

    def test_sets_usage_from_func(self):
        s = cliapp.Settings('appname', '1.0', usage=lambda: 'xyzzy')
        p = s.build_parser()
        self.assert_('xyzzy' in p.usage)

    def test_adds_default_options_and_settings(self):
        self.assert_('output' in self.settings)
        self.assert_('log' in self.settings)
        self.assert_('log-level' in self.settings)

    def test_iterates_over_canonical_settings_names(self):
        known = ['output', 'log', 'log-level']
        self.assertEqual(sorted(x for x in self.settings if x in known),
                         sorted(known))

    def test_keys_returns_canonical_names(self):
        known = ['output', 'log', 'log-level']
        self.assertEqual(sorted(x for x in self.settings.keys() if x in known),
                         sorted(known))

    def test_parses_options(self):
        self.settings.string(['foo'], 'foo help', group='foo')
        self.settings.boolean(['bar'], 'bar help')
        self.settings.parse_args(['--foo=foovalue', '--bar'])
        self.assertEqual(self.settings['foo'], 'foovalue')
        self.assertEqual(self.settings['bar'], True)

    def test_does_not_have_foo_setting_by_default(self):
        self.assertFalse('foo' in self.settings)

    def test_raises_keyerror_for_getting_unknown_setting(self):
        self.assertRaises(KeyError, self.settings.__getitem__, 'foo')

    def test_raises_keyerror_for_setting_unknown_setting(self):
        self.assertRaises(KeyError, self.settings.__setitem__, 'foo', 'bar')

    def test_adds_string_setting(self):
        self.settings.string(['foo'], 'foo help')
        self.assert_('foo' in self.settings)

    def test_adds_string_list_setting(self):
        self.settings.string_list(['foo'], 'foo help')
        self.assert_('foo' in self.settings)

    def test_string_list_is_empty_list_by_default(self):
        self.settings.string_list(['foo'], '')
        self.settings.parse_args([])
        self.assertEqual(self.settings['foo'], [])

    def test_string_list_parses_one_item(self):
        self.settings.string_list(['foo'], '')
        self.settings.parse_args(['--foo=foo'])
        self.assertEqual(self.settings['foo'], ['foo'])

    def test_string_list_parses_two_items(self):
        self.settings.string_list(['foo'], '')
        self.settings.parse_args(['--foo=foo', '--foo', 'bar'])
        self.assertEqual(self.settings['foo'], ['foo', 'bar'])

    def test_string_list_uses_nonempty_default_if_given(self):
        self.settings.string_list(['foo'], '', default=['bar'])
        self.settings.parse_args([])
        self.assertEqual(self.settings['foo'], ['bar'])

    def test_string_list_uses_ignores_default_if_user_provides_values(self):
        self.settings.string_list(['foo'], '', default=['bar'])
        self.settings.parse_args(['--foo=pink', '--foo=punk'])
        self.assertEqual(self.settings['foo'], ['pink', 'punk'])

    def test_adds_choice_setting(self):
        self.settings.choice(['foo'], ['foo', 'bar'], 'foo help')
        self.assert_('foo' in self.settings)

    def test_choice_defaults_to_first_one(self):
        self.settings.choice(['foo'], ['foo', 'bar'], 'foo help')
        self.settings.parse_args([])
        self.assertEqual(self.settings['foo'], 'foo')

    def test_choice_accepts_any_valid_value(self):
        self.settings.choice(['foo'], ['foo', 'bar'], 'foo help')
        self.settings.parse_args(['--foo=foo'])
        self.assertEqual(self.settings['foo'], 'foo')
        self.settings.parse_args(['--foo=bar'])
        self.assertEqual(self.settings['foo'], 'bar')

    def test_choice_raises_error_for_unacceptable_value(self):
        self.settings.choice(['foo'], ['foo', 'bar'], 'foo help')
        self.assertRaises(SystemExit,
                          self.settings.parse_args, ['--foo=xyzzy'],
                          suppress_errors=True)

    def test_adds_boolean_setting(self):
        self.settings.boolean(['foo'], 'foo help')
        self.assert_('foo' in self.settings)
        
    def test_boolean_setting_is_false_by_default(self):
        self.settings.boolean(['foo'], 'foo help')
        self.assertFalse(self.settings['foo'])
        
    def test_sets_boolean_setting_to_true_for_many_true_values(self):
        self.settings.boolean(['foo'], 'foo help')
        self.settings['foo'] = True
        self.assert_(self.settings['foo'])
        self.settings['foo'] = 1
        self.assert_(self.settings['foo'])
        
    def test_sets_boolean_setting_to_false_for_many_false_values(self):
        self.settings.boolean(['foo'], 'foo help')
        self.settings['foo'] = False
        self.assertFalse(self.settings['foo'])
        self.settings['foo'] = 0
        self.assertFalse(self.settings['foo'])
        self.settings['foo'] = ()
        self.assertFalse(self.settings['foo'])
        self.settings['foo'] = []
        self.assertFalse(self.settings['foo'])
        self.settings['foo'] = ''
        self.assertFalse(self.settings['foo'])

    def test_sets_boolean_to_true_from_config_file(self):
        def fake_open(filename):
            return StringIO.StringIO('[config]\nfoo = yes\n')
        self.settings.boolean(['foo'], 'foo help')
        self.settings.load_configs(open=fake_open)
        self.assertEqual(self.settings['foo'], True)
        
    def test_sets_boolean_to_false_from_config_file(self):
        def fake_open(filename):
            return StringIO.StringIO('[config]\nfoo = False\n')
        self.settings.boolean(['foo'], 'foo help')
        self.settings.load_configs(open=fake_open)
        self.assertEqual(self.settings['foo'], False)
        
    def test_adds_bytesize_setting(self):
        self.settings.bytesize(['foo'], 'foo help')
        self.assert_('foo' in self.settings)

    def test_parses_bytesize_option(self):
        self.settings.bytesize(['foo'], 'foo help')

        self.settings.parse_args(args=['--foo=xyzzy'])
        self.assertEqual(self.settings['foo'], 0)

        self.settings.parse_args(args=['--foo=123'])
        self.assertEqual(self.settings['foo'], 123)

        self.settings.parse_args(args=['--foo=123k'])
        self.assertEqual(self.settings['foo'], 123 * 1000)

        self.settings.parse_args(args=['--foo=123m'])
        self.assertEqual(self.settings['foo'], 123 * 1000**2)

        self.settings.parse_args(args=['--foo=123g'])
        self.assertEqual(self.settings['foo'], 123 * 1000**3)

        self.settings.parse_args(args=['--foo=123t'])
        self.assertEqual(self.settings['foo'], 123 * 1000**4)

        self.settings.parse_args(args=['--foo=123kib'])
        self.assertEqual(self.settings['foo'], 123 * 1024)

        self.settings.parse_args(args=['--foo=123mib'])
        self.assertEqual(self.settings['foo'], 123 * 1024**2)

        self.settings.parse_args(args=['--foo=123gib'])
        self.assertEqual(self.settings['foo'], 123 * 1024**3)

        self.settings.parse_args(args=['--foo=123tib'])
        self.assertEqual(self.settings['foo'], 123 * 1024**4)
        
    def test_adds_integer_setting(self):
        self.settings.integer(['foo'], 'foo help')
        self.assert_('foo' in self.settings)

    def test_parses_integer_option(self):
        self.settings.integer(['foo'], 'foo help', default=123)

        self.settings.parse_args(args=[])
        self.assertEqual(self.settings['foo'], 123)

        self.settings.parse_args(args=['--foo=123'])
        self.assertEqual(self.settings['foo'], 123)

    def test_has_list_of_default_config_files(self):
        defaults = self.settings._default_config_files
        self.assert_(isinstance(defaults, list))
        self.assert_(len(defaults) > 0)

    def test_listconfs_returns_empty_list_for_nonexistent_directory(self):
        self.assertEqual(self.settings._listconfs('notexist'), [])

    def test_listconfs_lists_config_files_only(self):
        def mock_listdir(dirname):
            return ['foo.conf', 'foo.notconf']
        names = self.settings._listconfs('.', listdir=mock_listdir)
        self.assertEqual(names, ['./foo.conf'])

    def test_listconfs_sorts_names_in_C_locale(self):
        def mock_listdir(dirname):
            return ['foo.conf', 'bar.conf']
        names = self.settings._listconfs('.', listdir=mock_listdir)
        self.assertEqual(names, ['./bar.conf', './foo.conf'])

    def test_has_config_files_attribute(self):
        self.assertEqual(self.settings.config_files,
                         self.settings._default_config_files)

    def test_has_config_files_list_can_be_changed(self):
        self.settings.config_files += ['./foo']
        self.assertEqual(self.settings.config_files,
                         self.settings._default_config_files + ['./foo'])

    def test_loads_config_files(self):
    
        def mock_open(filename, mode=None):
            return StringIO.StringIO('''\
[config]
foo = yeehaa
''')
    
        self.settings.string(['foo'], 'foo help')
        self.settings.config_files = ['whatever.conf']
        self.settings.load_configs(open=mock_open)
        self.assertEqual(self.settings['foo'], 'yeehaa')

    def test_loads_string_list_from_config_files(self):
    
        def mock_open(filename, mode=None):
            return StringIO.StringIO('''\
[config]
foo = yeehaa
bar = ping, pong
''')
    
        self.settings.string_list(['foo'], 'foo help')
        self.settings.string_list(['bar'], 'bar help')
        self.settings.config_files = ['whatever.conf']
        self.settings.load_configs(open=mock_open)
        self.assertEqual(self.settings['foo'], ['yeehaa'])
        self.assertEqual(self.settings['bar'], ['ping', 'pong'])

    def test_handles_defaults_with_config_files(self):
    
        def mock_open(filename, mode=None):
            return StringIO.StringIO('''\
[config]
''')
    
        self.settings.string(['foo'], 'foo help', default='foo')
        self.settings.string_list(['bar'], 'bar help', default=['bar'])
        self.settings.config_files = ['whatever.conf']
        self.settings.load_configs(open=mock_open)
        self.assertEqual(self.settings['foo'], 'foo')
        self.assertEqual(self.settings['bar'], ['bar'])

    def test_handles_overridden_defaults_with_config_files(self):
    
        def mock_open(filename, mode=None):
            return StringIO.StringIO('''\
[config]
foo = yeehaa
bar = ping, pong
''')
    
        self.settings.string(['foo'], 'foo help', default='foo')
        self.settings.string_list(['bar'], 'bar help', default=['bar'])
        self.settings.config_files = ['whatever.conf']
        self.settings.load_configs(open=mock_open)
        self.assertEqual(self.settings['foo'], 'yeehaa')
        self.assertEqual(self.settings['bar'], ['ping', 'pong'])

    def test_handles_values_from_config_files_overridden_on_command_line(self):
    
        def mock_open(filename, mode=None):
            return StringIO.StringIO('''\
[config]
foo = yeehaa
bar = ping, pong
''')
    
        self.settings.string(['foo'], 'foo help', default='foo')
        self.settings.string_list(['bar'], 'bar help', default=['bar'])
        self.settings.config_files = ['whatever.conf']
        self.settings.load_configs(open=mock_open)
        self.settings.parse_args(['--foo=red', '--bar=blue', '--bar=white'])
        self.assertEqual(self.settings['foo'], 'red')
        self.assertEqual(self.settings['bar'], ['blue', 'white'])

    def test_load_configs_ignore_errors_opening_a_file(self):
        
        def mock_open(filename, mode=None):
            raise IOError()
            
        self.assertEqual(self.settings.load_configs(open=mock_open), None)

    def test_adds_config_file_with_dash_dash_config(self):
        self.settings.parse_args(['--config=foo.conf'])
        self.assertEqual(self.settings.config_files,
                         self.settings._default_config_files + ['foo.conf'])

    def test_ignores_default_configs(self):
        self.settings.parse_args(['--no-default-configs'])
        self.assertEqual(self.settings.config_files, [])

    def test_ignores_then_adds_configs_works(self):
        self.settings.parse_args(['--no-default-configs', '--config=foo.conf'])
        self.assertEqual(self.settings.config_files, ['foo.conf'])

    def test_require_raises_error_if_string_unset(self):
        self.settings.string(['foo'], 'foo help', default=None)
        self.assertRaises(cliapp.AppException, self.settings.require, 
                          'foo')

    def test_require_is_ok_with_set_string(self):
        self.settings.string(['foo'], 'foo help', default=None)
        self.settings['foo'] = 'bar'
        self.assertEqual(self.settings.require('foo'), None)

    def test_require_is_ok_with_default_string(self):
        self.settings.string(['foo'], 'foo help', default='foo default')
        self.assertEqual(self.settings.require('foo'), None)

    def test_require_raises_error_if_string_list_unset(self):
        self.settings.string_list(['foo'], 'foo help')
        self.assertRaises(cliapp.AppException, self.settings.require, 'foo')

    def test_require_is_ok_with_set_string_list(self):
        self.settings.string(['foo'], 'foo help')
        self.settings['foo'] = ['foo', 'bar']
        self.assertEqual(self.settings.require('foo'), None)

    def test_require_is_ok_with_default_string_list(self):
        self.settings.string(['foo'], 'foo help', default=['foo'])
        self.assertEqual(self.settings.require('foo'), None)

    def test_require_is_ok_with_unset_choice(self):
        self.settings.choice(['foo'], ['foo', 'bar'], 'foo help')
        self.assertEqual(self.settings.require('foo'), None)

    def test_require_is_ok_with_unset_boolean(self):
        self.settings.boolean(['foo'], 'foo help')
        self.assertEqual(self.settings.require('foo'), None)

    def test_require_is_ok_with_unset_bytesize(self):
        self.settings.bytesize(['foo'], 'foo help')
        self.assertEqual(self.settings.require('foo'), None)

    def test_require_is_ok_with_unset_integer(self):
        self.settings.integer(['foo'], 'foo help')
        self.assertEqual(self.settings.require('foo'), None)

    def test_exports_configparser_with_settings(self):
        self.settings.integer(['foo'], 'foo help', default=1)
        self.settings.string(['bar'], 'bar help', default='yo')
        cp = self.settings.as_cp()
        self.assertEqual(cp.get('config', 'foo'), '1')
        self.assertEqual(cp.get('config', 'bar'), 'yo')

    def test_exports_all_config_sections_via_as_cp(self):
    
        def mock_open(filename, mode=None):
            return StringIO.StringIO('''\
[config]
foo = yeehaa

[other]
bar = dodo
''')
    
        self.settings.string(['foo'], 'foo help', default='foo')
        self.settings.config_files = ['whatever.conf']
        self.settings.load_configs(open=mock_open)
        cp = self.settings.as_cp()

        self.assertEqual(sorted(cp.sections()), ['config', 'other'])
        self.assertEqual(cp.get('config', 'foo'), 'yeehaa')
        self.assertEqual(cp.options('other'), ['bar'])
        self.assertEqual(cp.get('other', 'bar'), 'dodo')

