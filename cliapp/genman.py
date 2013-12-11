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
import re


class ManpageGenerator(object):

    '''Fill in a manual page template from an OptionParser instance.'''

    def __init__(self, template, parser, arg_synopsis, cmd_synopsis):
        self.template = template
        self.parser = parser
        self.arg_synopsis = arg_synopsis
        self.cmd_synopsis = cmd_synopsis

    def sort_options(self, options):
        return sorted(options,
                      key=lambda o: (o._long_opts + o._short_opts)[0])

    def option_list(self, container):
        return self.sort_options(container.option_list)

    @property
    def options(self):
        return self.option_list(self.parser)

    def format_template(self):
        sections = (('SYNOPSIS', self.format_synopsis()),
                    ('OPTIONS', self.format_options()))
        text = self.template
        for section, contents in sections:
            pattern = '\n.SH %s\n' % section
            text = text.replace(pattern, pattern + contents)
        return text

    def format_synopsis(self):
        lines = []
        lines += ['.nh']
        lines += ['.B %s' % self.esc_dashes(self.parser.prog)]

        all_options = self.option_list(self.parser)
        for group in self.parser.option_groups:
            all_options += self.option_list(group)
        for option in self.sort_options(all_options):
            for spec in self.format_option_for_synopsis(option):
                lines += ['.RB [ %s ]' % spec]

        if self.cmd_synopsis:
            lines += ['.PP']
            for cmd in sorted(self.cmd_synopsis):
                lines += ['.br',
                          '.B %s' % self.esc_dashes(self.parser.prog),
                          '.RI [ options ]',
                          self.esc_dashes(cmd)]
                lines += self.format_argspec(self.cmd_synopsis[cmd])
        elif self.arg_synopsis:
            lines += self.format_argspec(self.arg_synopsis)

        lines += ['.hy']
        return ''.join('%s\n' % line for line in lines)

    def format_option_for_synopsis(self, option):
        if option.metavar:
            suffix = '\\fR=\\fI%s' % self.esc_dashes(option.metavar)
        else:
            suffix = ''
        for name in option._short_opts + option._long_opts:
            yield '%s%s' % (self.esc_dashes(name), suffix)

    def format_options(self):
        lines = []

        for option in self.sort_options(self.parser.option_list):
            lines += self.format_option_for_options(option)

        for group in self.parser.option_groups:
            lines += ['.SS "%s"' % group.title]
            for option in self.sort_options(group.option_list):
                lines += self.format_option_for_options(option)

        return ''.join('%s\n' % line for line in lines)

    def format_option_for_options(self, option):
        lines = []
        lines += ['.TP']
        shorts = [self.esc_dashes(x) for x in option._short_opts]
        if option.metavar:
            longs = ['%s =\\fI%s' % (self.esc_dashes(x), option.metavar)
                     for x in option._long_opts]
        else:
            longs = ['%s' % self.esc_dashes(x)
                     for x in option._long_opts]
        lines += ['.BR ' + ' ", " '.join(shorts + longs)]
        lines += [self.esc_dots(self.expand_default(option).strip())]
        return lines

    def expand_default(self, option):
        default = self.parser.defaults.get(option.dest)
        if default is optparse.NO_DEFAULT or default is None:
            default = 'none'
        else:
            default = str(default)
        return option.help.replace('%default', default)

    def esc_dashes(self, optname):
        return '\\-'.join(optname.split('-'))

    def esc_dots(self, line):
        if line.startswith('.'):
            return '\\' + line
        else:
            return line

    def format_argspec(self, argspec):
        roman = re.compile(r'[^A-Z]+')
        italic = re.compile(r'[A-Z]+')
        words = ['.RI']
        while argspec:
            m = roman.match(argspec)
            if m:
                words += [self.esc_dashes(m.group(0))]
                argspec = argspec[m.end():]
            else:
                words += ['""']
            m = italic.match(argspec)
            if m:
                words += [self.esc_dashes(m.group(0))]
                argspec = argspec[m.end():]
            else:
                words += ['""']
        return [' '.join(words)]

