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


import ConfigParser
import optparse
import os
import re
import sys

import cliapp
from cliapp.genman import ManpageGenerator

class Setting(object):

    action = 'store'
    type = 'string'
    nargs = 1
    choices = None

    def __init__(self, names, default, help, metavar=None, group=None):
        self.names = names
        self.set_value(default)
        self.help = help
        self.metavar = metavar or self.default_metavar()
        self.group = group

    def default_metavar(self):
        return None

    def get_value(self):
        return self._string_value
        
    def set_value(self, value):
        self._string_value = value
        
    def call_get_value(self):
        return self.get_value()
        
    def call_set_value(self, value):
        self.set_value(value)

    value = property(call_get_value, call_set_value)

    def has_value(self):
        return self.value is not None

    def parse_value(self, string):
        self.value = string

    def format(self): # pragma: no cover
        return str(self.value)


class StringSetting(Setting):

    def default_metavar(self):
        return self.names[0].upper()


class StringListSetting(Setting):

    action = 'append'
    
    def __init__(self, names, default, help, metavar=None, group=None):
        Setting.__init__(self, names, [], help, metavar=metavar, group=group)
        self.default = default
        self.using_default_value = True

    def default_metavar(self):
        return self.names[0].upper()

    def get_value(self):
        if self._string_value.strip():
            return [s.strip() for s in self._string_value.split(',')]
        else:
            return self.default
        
    def set_value(self, strings):
        self._string_value = ','.join(strings)
        self.using_default_value = False

    def has_value(self):
        return self.value != []
        
    def parse_value(self, string):
        self.value = [s.strip() for s in string.split(',')]
        
    def format(self): # pragma: no cover
        return ', '.join(self.value)


class ChoiceSetting(Setting):

    type = 'choice'
    
    def __init__(self, names, choices, help, metavar=None, group=None):
        Setting.__init__(self, names, choices[0], help, metavar=metavar,
                         group=group)
        self.choices = choices

    def default_metavar(self):
        return self.names[0].upper()

    
class BooleanSetting(Setting):

    action = 'store_true'
    nargs = None
    type = None

    _trues = ['yes', 'on', '1', 'true']
    _false = 'no'

    def get_value(self):
        return self._string_value.lower() in self._trues
        
    def set_value(self, value):
        def is_true():
            if value is True or value is False:
                return value
            if type(value) in [str, unicode]:
                return value.lower() in self._trues
            return value
        if is_true():
            self._string_value = self._trues[0]
        else:
            self._string_value = self._false


class ByteSizeSetting(Setting):

    def parse_human_size(self, size):
        '''Parse a size using suffix into plain bytes.'''
        
        m = re.match(r'''(?P<number>\d+(\.\d+)?) \s* 
                         (?P<unit>k|ki|m|mi|g|gi|t|ti)? b? \s*$''',
                     size.lower(), flags=re.X)
        if not m:
            return 0
        else:
            number = float(m.group('number'))
            unit = m.group('unit')
            units = {
                'k': 10**3,
                'm': 10**6,
                'g': 10**9,
                't': 10**12,
                'ki': 2**10,
                'mi': 2**20,
                'gi': 2**30,
                'ti': 2**40,
            }
            return long(number * units.get(unit, 1))

    def default_metavar(self):
        return 'SIZE'

    def get_value(self):
        return long(self._string_value)
        
    def set_value(self, value):
        if type(value) == str:
            value = self.parse_human_size(value)
        self._string_value = str(value)


class IntegerSetting(Setting):

    type = 'int'

    def default_metavar(self):
        return self.names[0].upper()

    def get_value(self):
        return long(self._string_value)
        
    def set_value(self, value):
        self._string_value = str(value)


class FormatHelpParagraphs(optparse.IndentedHelpFormatter):

    def _format_text(self, text): # pragma: no cover
        '''Like the default, except handle paragraphs.'''
        
        def format_para(lines):
            para = '\n'.join(lines)
            return optparse.IndentedHelpFormatter._format_text(self,  para)
        
        paras = []
        cur = []
        for line in text.splitlines():
            if line.strip():
                cur.append(line)
            elif cur:
                paras.append(format_para(cur))
                cur = []
        if cur:
            paras.append(format_para(cur))
        return '\n\n'.join(paras)


class Settings(object):

    '''Settings for a cliapp application.

    You probably don't need to create a settings object yourself,
    since ``cliapp.Application`` does it for you.
    
    Settings are read from configuration files, and parsed from the
    command line. Every setting has a type, name, and help text,
    and may have a default value as well.
    
    For example::
    
        settings.boolean(['verbose', 'v'], 'show what is going on')
        
    This would create a new setting, ``verbose``, with a shorter alias
    ``v``. On the command line, the options ``--verbose`` and
    ``-v`` would work equally well. There can be any number of aliases. 

    The help text is shown if the user uses ``--help`` or
    ``--generate-manpage``.
    You can use the ``metavar`` keyword argument to set the name shown
    in the generated option lists; the default name is whatever
    ``optparse`` decides (i.e., name of option).
    
    Use ``load_configs`` to read configuration files, and
    ``parse_args`` to parse command line arguments.
    
    The current value of a setting can be accessed by indexing
    the settings class::
    
        settings['verbose']

    The list of configuration files for the appliation is stored
    in ``config_files``. Add or remove from the list if you wish.
    The files need to exist: those that don't are silently ignored.
    
    '''

    def __init__(self, progname, version, usage=None, description=None, 
                 epilog=None):
        self._settingses = dict()
        self._canonical_names = list()

        self.version = version
        self.progname = progname
        self.usage = usage
        self.description = description
        self.epilog = epilog
        
        self._add_default_settings()
        
        self._config_files = None
        self._cp = ConfigParser.ConfigParser()

    def _add_default_settings(self):
        self.string(['output'], 
                    'write output to FILE, instead of standard output',
                    metavar='FILE')

        self.string(['log'], 
                    'write log entries to FILE (default is to not write log '
                        'files at all); use "syslog" to log to system log, '
                        'or "none" to disable logging',
                    metavar='FILE')
        self.choice(['log-level'], 
                    ['debug', 'info', 'warning', 'error', 'critical', 'fatal'],
                    'log at LEVEL, one of debug, info, warning, '
                        'error, critical, fatal (default: %default)',
                    metavar='LEVEL')
        self.bytesize(['log-max'], 
                      'rotate logs larger than SIZE, '
                        'zero for never (default: %default)',
                      metavar='SIZE', default=0)
        self.integer(['log-keep'], 'keep last N logs (%default)',
                     metavar='N', default=10)
        self.string(['log-mode'], 
                    'set permissions of new log files to MODE (octal; '
                        'default %default)',
                    metavar='MODE', default='0600')

        self.choice(['dump-memory-profile'],
                    ['simple', 'none', 'meliae', 'heapy'],
                    'make memory profiling dumps using METHOD, which is one '
                        'of: none, simple, meliae, or heapy '
                        '(default: %default)',
                    metavar='METHOD')

    def _add_setting(self, setting):
        '''Add a setting to self._cp.'''

        self._canonical_names.append(setting.names[0])
        for name in setting.names:
            self._settingses[name] = setting

    def string(self, names, help, default='', **kwargs):
        '''Add a setting with a string value.'''
        self._add_setting(StringSetting(names, default, help, **kwargs))

    def string_list(self, names, help, default=None, **kwargs):
        '''Add a setting which have multiple string values.
        
        An example would be an option that can be given multiple times
        on the command line, e.g., "--exclude=foo --exclude=bar".
        
        '''

        self._add_setting(StringListSetting(names, default or [], help,
                                            **kwargs))

    def choice(self, names, possibilities, help, **kwargs):
        '''Add a setting which chooses from list of acceptable values.
        
        An example would be an option to set debugging level to be
        one of a set of accepted names: debug, info, warning, etc.
        
        The default value is the first possibility.
        
        '''

        self._add_setting(ChoiceSetting(names, possibilities, help, **kwargs))

    def boolean(self, names, help, default=False, **kwargs):
        '''Add a setting with a boolean value.'''
        self._add_setting(BooleanSetting(names, default, help, **kwargs))

    def bytesize(self, names, help, default=0, **kwargs):
        '''Add a setting with a size in bytes.
        
        The user can use suffixes for kilo/mega/giga/tera/kibi/mibi/gibi/tibi.
        
        '''
        
        self._add_setting(ByteSizeSetting(names, default, help, **kwargs))

    def integer(self, names, help, default=0, **kwargs):
        '''Add an integer setting.'''
        self._add_setting(IntegerSetting(names, default, help, **kwargs))

    def __getitem__(self, name):
        return self._settingses[name].value

    def __setitem__(self, name, value):
        self._settingses[name].value = value

    def __contains__(self, name):
        return name in self._settingses
        
    def __iter__(self):
        '''Iterate over canonical settings names.'''
        for name in self._canonical_names:
            yield name

    def keys(self):
        '''Return canonical settings names.'''
        return self._canonical_names[:]

    def require(self, name):
        '''Raise exception if setting has not been set.
        
        Option must have a value, and a default value is OK.
        
        '''
        
        if not self._settingses[name].has_value():
            raise cliapp.AppException('Setting %s has no value, '
                                        'but one is required' % name)
        
    def _option_names(self, names):
        '''Turn setting names into option names.
        
        Names with a single letter are short options, and get prefixed
        with one dash. The rest get prefixed with two dashes.
        
        '''

        return ['--%s' % name if len(name) > 1 else '-%s' % name
                for name in names]

    def _destname(self, name):
        name = '_'.join(name.split('-'))
        return name

    def build_parser(self, configs_only=False, arg_synopsis=None,
                     cmd_synopsis=None):
        '''Build OptionParser for parsing command line.'''

        maybe = lambda func: (lambda *args: None) if configs_only else func

        def getit(x):
            if x is None or type(x) in [str, unicode]:
                return x
            else:
                return x()
        usage = getit(self.usage)
        description = getit(self.description)
        p = optparse.OptionParser(prog=self.progname, version=self.version,
                                  formatter=FormatHelpParagraphs(),
                                  usage=usage,
                                  description=description,
                                  epilog=self.epilog)
        
        def dump_setting_names(*args): # pragma: no cover
            for name in self._canonical_names:
                sys.stdout.write('%s\n' % name)
            sys.exit(0)

        p.add_option('--dump-setting-names',
                     action='callback',
                     nargs=0,
                     callback=maybe(dump_setting_names),
                     help='write out all names of settings and quit')

        def call_dump_config(*args): # pragma: no cover
            self.dump_config(sys.stdout)
            sys.exit(0)

        p.add_option('--dump-config',
                     action='callback',
                     nargs=0,
                     callback=maybe(call_dump_config),
                     help='write out the entire current configuration')

        def reset_configs(option, opt_str, value, parser):
            self.config_files = []

        p.add_option('--no-default-configs',
                     action='callback',
                     nargs=0,
                     callback=reset_configs,
                     help='clear list of configuration files to read')

        def append_to_configs(option, opt_str, value, parser):
            self.config_files.append(value)

        p.add_option('--config',
                     action='callback',
                     nargs=1,
                     type='string',
                     callback=append_to_configs,
                     help='add FILE to config files',
                     metavar='FILE')

        def list_config_files(*args): # pragma: no cover
            for filename in self.config_files:
                print filename
            sys.exit(0)

        p.add_option('--list-config-files',
                     action='callback',
                     nargs=0,
                     callback=maybe(list_config_files),
                     help='list all possible config files')

        self._arg_synopsis = arg_synopsis
        self._cmd_synopsis = cmd_synopsis
        p.add_option('--generate-manpage',
                     action='callback',
                     nargs=1,
                     type='string',
                     callback=maybe(self._generate_manpage),
                     help='fill in manual page TEMPLATE',
                     metavar='TEMPLATE')

        def set_value(option, opt_str, value, parser, setting):
            if setting.action == 'append':
                if setting.using_default_value:
                    setting.value = [value]
                else:
                    setting.value += [value]
            elif setting.action == 'store_true':
                setting.value = True
            else:
                assert setting.action == 'store'
                setting.value = value

        def add_option(obj, s):
            option_names = self._option_names(s.names)
            obj.add_option(*option_names, 
                           action='callback',
                           callback=maybe(set_value),
                           callback_args=(s,),
                           type=s.type,
                           nargs=s.nargs,
                           choices=s.choices,
                           help=s.help,
                           metavar=s.metavar)
        
        for name in self._canonical_names:
            s = self._settingses[name]
            if s.group is None:
                add_option(p, s)
                p.set_defaults(**{self._destname(name): s.value})

        groups = {}
        for name in self._canonical_names:
            s = self._settingses[name]
            if s.group is not None:
                groups[s.group] = groups.get(s.group, []) + [(name, s)]

        groupnames = sorted(groups.keys())
        for groupname in groupnames:
            group = optparse.OptionGroup(p, groupname)
            p.add_option_group(group)
            for name, s in groups[groupname]:
                add_option(group, s)
                p.set_defaults(**{self._destname(name): s.value})

        return p

    def parse_args(self, args, parser=None, suppress_errors=False,
                    configs_only=False, arg_synopsis=None,
                    cmd_synopsis=None):
        '''Parse the command line.
        
        Return list of non-option arguments. ``args`` would usually
        be ``sys.argv[1:]``.
        
        '''

        p = parser or self.build_parser(configs_only=configs_only,
                                        arg_synopsis=arg_synopsis,
                                        cmd_synopsis=cmd_synopsis)

        if suppress_errors:
            p.error = lambda msg: sys.exit(1)

        options, args = p.parse_args(args)
        return args

    @property
    def _default_config_files(self):
        '''Return list of default config files to read.
        
        The names of the files are dependent on the name of the program,
        as set in the progname attribute.
        
        The files may or may not exist.
        
        '''
        
        configs = []
        
        configs.append('/etc/%s.conf' % self.progname)
        configs += self._listconfs('/etc/%s' % self.progname)
        configs.append(os.path.expanduser('~/.%s.conf' % self.progname))
        configs += self._listconfs(
                        os.path.expanduser('~/.config/%s' % self.progname))
        
        return configs

    def _listconfs(self, dirname, listdir=os.listdir):
        '''Return list of pathnames to config files in dirname.
        
        Config files are expectd to have names ending in '.conf'.
        
        If dirname does not exist or is not a directory, 
        return empty list.
        
        '''
        
        if not os.path.isdir(dirname):
            return []

        basenames = listdir(dirname)
        basenames.sort(key=lambda s: [ord(c) for c in s])
        return [os.path.join(dirname, x)
                for x in basenames
                if x.endswith('.conf')]

    def _get_config_files(self):
        if self._config_files is None:
            self._config_files = self._default_config_files
        return self._config_files

    def _set_config_files(self, config_files):
        self._config_files = config_files
        
    config_files = property(_get_config_files, _set_config_files)

    def set_from_raw_string(self, name, raw_string):
        '''Set value of a setting from a raw, unparsed string value.'''
        s = self._settingses[name]
        s.parse_value(raw_string)
        return s

    def load_configs(self, open=open):
        '''Load all config files in self.config_files.
        
        Silently ignore files that do not exist.
        
        '''

        cp = ConfigParser.ConfigParser()
        cp.add_section('config')

        for pathname in self.config_files:
            try:
                f = open(pathname)
            except IOError:
                pass
            else:
                cp.readfp(f)
                f.close()

        for name in cp.options('config'):
            value = cp.get('config', name)
            s = self.set_from_raw_string(name, value)
            if hasattr(s, 'using_default_value'):
                s.using_default_value = True

        # Remember the ConfigParser for use in as_cp later on.
        self._cp = cp

    def _generate_manpage(self, o, os, value, p): # pragma: no cover
        template = open(value).read()
        generator = ManpageGenerator(template, p, self._arg_synopsis,
                                     self._cmd_synopsis)
        sys.stdout.write(generator.format_template())
        sys.exit(0)

    def as_cp(self):
        '''Return a ConfigParser instance with current values of settings.'''
        cp = ConfigParser.ConfigParser()
        cp.add_section('config')
        for name in self._canonical_names:
            cp.set('config', name, self._settingses[name].format())

        for section in self._cp.sections():
            if section != 'config':
                cp.add_section(section)
                for option in self._cp.options(section):
                    value = self._cp.get(section, option)
                    cp.set(section, option, value)

        return cp

    def dump_config(self, output): # pragma: no cover
        cp = self.as_cp()
        cp.write(output)

