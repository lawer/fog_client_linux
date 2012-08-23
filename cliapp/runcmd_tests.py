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


import optparse
import os
import StringIO
import sys
import tempfile
import unittest

import cliapp


def devnull(msg):
    pass


class ApplicationTests(unittest.TestCase):

    def test_runcmd_executes_true(self):
        self.assertEqual(cliapp.runcmd(['true']), '')
    
    def test_runcmd_raises_error_on_failure(self):
        self.assertRaises(cliapp.AppException, cliapp.runcmd, ['false'])
    
    def test_runcmd_returns_stdout_of_command(self):
        self.assertEqual(cliapp.runcmd(['echo', 'hello', 'world']),
                         'hello world\n')
    
    def test_runcmd_returns_stderr_of_command(self):
        exit, out, err = cliapp.runcmd_unchecked(['ls', 'notexist'])
        self.assertNotEqual(exit, 0)
        self.assertEqual(out, '')
        self.assertNotEqual(err, '')

    def test_runcmd_pipes_stdin_through_command(self):
        self.assertEqual(cliapp.runcmd(['cat'], feed_stdin='hello, world'),
                         'hello, world')

    def test_runcmd_pipes_stdin_through_two_commands(self):
        self.assertEqual(cliapp.runcmd(
                            ['cat'], ['cat'], feed_stdin='hello, world'),
                         'hello, world')

    def test_runcmd_pipes_stdin_through_command_with_lots_of_data(self):
        data = 'x' * (1024**2)
        self.assertEqual(cliapp.runcmd(['cat'], feed_stdin=data), data)

    def test_runcmd_ignores_failures_on_request(self):
        self.assertEqual(cliapp.runcmd(['false'], ignore_fail=True), '')

    def test_runcmd_obeys_cwd(self):
        self.assertEqual(cliapp.runcmd(['pwd'], cwd='/'), '/\n')

    def test_runcmd_unchecked_returns_values_on_success(self):
        self.assertEqual(cliapp.runcmd_unchecked(['echo', 'foo']), 
                         (0, 'foo\n', ''))

    def test_runcmd_unchecked_returns_values_on_failure(self):
        self.assertEqual(cliapp.runcmd_unchecked(['false']), 
                         (1, '', ''))

    def test_runcmd_unchecked_runs_simple_pipeline(self):
        self.assertEqual(cliapp.runcmd_unchecked(
                            ['echo', 'foo'], ['wc', '-c']),
                         (0, '4\n', ''))

    def test_runcmd_unchecked_runs_longer_pipeline(self):
        self.assertEqual(cliapp.runcmd_unchecked(['echo', 'foo'], 
                                                 ['cat'],
                                                 ['wc', '-c']),
                         (0, '4\n', ''))

    def test_runcmd_redirects_stdin_from_file(self):
        fd, filename = tempfile.mkstemp()
        os.write(fd, 'foobar')
        os.lseek(fd, 0, os.SEEK_SET)
        self.assertEqual(cliapp.runcmd_unchecked(['cat'], stdin=fd),
                         (0, 'foobar', ''))
        os.close(fd)
                            
    def test_runcmd_redirects_stdout_to_file(self):
        fd, filename = tempfile.mkstemp()
        exit, out, err = cliapp.runcmd_unchecked(['echo', 'foo'], stdout=fd)
        os.close(fd)
        with open(filename) as f:
            data = f.read()
        self.assertEqual(exit, 0)
        self.assertEqual(data, 'foo\n')
                            
    def test_runcmd_redirects_stderr_to_file(self):
        fd, filename = tempfile.mkstemp()
        exit, out, err = cliapp.runcmd_unchecked(['ls', 'notexist'], stderr=fd)
        os.close(fd)
        with open(filename) as f:
            data = f.read()
        self.assertNotEqual(exit, 0)
        self.assertNotEqual(data, '')


