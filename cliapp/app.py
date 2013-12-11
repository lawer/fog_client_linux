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


import errno
import gc
import inspect
import logging
import logging.handlers
import os
import StringIO
import sys
import traceback
import time
import platform
import textwrap

import cliapp


class AppException(Exception):

    '''Base class for application specific exceptions.

    Any exceptions that are subclasses of this one get printed as
    nice errors to the user. Any other exceptions cause a Python
    stack trace to be written to stderr.

    '''

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class LogHandler(logging.handlers.RotatingFileHandler): # pragma: no cover

    '''Like RotatingFileHandler, but set permissions of new files.'''

    def __init__(self, filename, perms=0600, *args, **kwargs):
        self._perms = perms
        logging.handlers.RotatingFileHandler.__init__(self, filename,
                                                      *args, **kwargs)

    def _open(self):
        if not os.path.exists(self.baseFilename):
            flags = os.O_CREAT | os.O_WRONLY
            fd = os.open(self.baseFilename, flags, self._perms)
            os.close(fd)
        return logging.handlers.RotatingFileHandler._open(self)


class Application(object):

    '''A framework for Unix-like command line programs.

    The user should subclass this base class for each application.
    The subclass does not need code for the mundane, boilerplate
    parts that are the same in every utility, and can concentrate on the
    interesting part that is unique to it.

    To start the application, call the `run` method.

    The ``progname`` argument sets tne name of the program, which is
    used for various purposes, such as determining the name of the
    configuration file.

    Similarly, ``version`` sets the version number of the program.

    ``description`` and ``epilog`` are included in the output of
    ``--help``. They are formatted to fit the screen. Unlike the
    default behavior of ``optparse``, empty lines separate
    paragraphs.

    '''

    def __init__(self, progname=None, version='0.0.0', description=None,
                 epilog=None):
        self.fileno = 0
        self.global_lineno = 0
        self.lineno = 0
        self._description = description
        if not hasattr(self, 'arg_synopsis'):
            self.arg_synopsis = '[FILE]...'
        if not hasattr(self, 'cmd_synopsis'):
            self.cmd_synopsis = {}

        self.subcommands = {}
        self.subcommand_aliases = {}
        self.hidden_subcommands = set()
        for method_name in self._subcommand_methodnames():
            cmd = self._unnormalize_cmd(method_name)
            self.subcommands[cmd] = getattr(self, method_name)

        self.settings = cliapp.Settings(progname, version,
                                        usage=self._format_usage,
                                        description=self._format_description,
                                        epilog=epilog)

        self.plugin_subdir = 'plugins'

        # For meliae memory dumps.
        self.memory_dump_counter = 0
        self.last_memory_dump = 0

        # For process duration.
        self._started = os.times()[-1]

    def add_settings(self):
        '''Add application specific settings.'''

    def run(self, args=None, stderr=sys.stderr, sysargv=sys.argv,
            log=logging.critical):
        '''Run the application.'''

        def run_it():
            self._run(args=args, stderr=stderr, log=log)

        if self.settings.progname is None and sysargv:
            self.settings.progname = os.path.basename(sysargv[0])
        envname = '%s_PROFILE' % self._envname(self.settings.progname)
        profname = os.environ.get(envname, '')
        if profname: # pragma: no cover
            import cProfile
            cProfile.runctx('run_it()', globals(), locals(), profname)
        else:
            run_it()

    def _envname(self, progname):
        '''Create an environment variable name of the name of a program.'''

        basename = os.path.basename(progname)
        if '.' in basename:
            basename = basename.split('.')[0]

        ok = 'abcdefghijklmnopqrstuvwxyz0123456789'
        ok += ok.upper()

        return ''.join(x.upper() if x in ok else '_' for x in basename)

    def _set_process_name(self): # pragma: no cover
        comm = '/proc/self/comm'
        if platform.system() == 'Linux' and os.path.exists(comm):
            with open('/proc/self/comm', 'w', 0) as f:
                f.write(self.settings.progname[:15])

    def _run(self, args=None, stderr=sys.stderr, log=logging.critical):
        try:
            self._set_process_name()
            self.add_settings()
            self.setup_plugin_manager()

            # A little bit of trickery here to make --no-default-configs and
            # --config=foo work right: we first parse the command line once,
            # and pick up any config files. Then we read configs. Finally,
            # we re-parse the command line to allow any options to override
            # config file settings.
            self.setup()
            self.enable_plugins()
            if self.subcommands:
                self.add_default_subcommands()
            args = sys.argv[1:] if args is None else args
            self.parse_args(args, configs_only=True)
            self.settings.load_configs()
            args = self.parse_args(args)

            self.setup_logging()
            self.log_config()

            if self.settings['output']:
                self.output = open(self.settings['output'], 'w')
            else:
                self.output = sys.stdout

            self.process_args(args)
            self.cleanup()
            self.disable_plugins()
        except cliapp.UnknownConfigVariable, e: # pragma: no cover
            stderr.write('ERROR: %s\n' % str(e))
            sys.exit(1)
        except AppException, e:
            log(traceback.format_exc())
            stderr.write('ERROR: %s\n' % str(e))
            sys.exit(1)
        except SystemExit, e:
            if e.code is not None and type(e.code) != int:
                log(str(e))
                stderr.write('ERROR: %s\n' % str(e))
            sys.exit(e.code if type(e.code) == int else 1)
        except KeyboardInterrupt, e:
            sys.exit(255)
        except IOError, e: # pragma: no cover
            if e.errno == errno.EPIPE and e.filename is None:
                # We're writing to stdout, and it broke. This almost always
                # happens when we're being piped to less, and the user quits
                # less before we finish writing everything out. So we ignore
                # the error in that case.
                sys.exit(1)
            log(traceback.format_exc())
            stderr.write('ERROR: %s\n' % str(e))
            sys.exit(1)
        except OSError, e: # pragma: no cover
            log(traceback.format_exc())
            if hasattr(e, 'filename') and e.filename:
                stderr.write('ERROR: %s: %s\n' % (e.filename, e.strerror))
            else:
                stderr.write('ERROR: %s\n' % e.strerror)
            sys.exit(1)
        except BaseException, e: # pragma: no cover
            log(traceback.format_exc())
            stderr.write(traceback.format_exc())
            sys.exit(1)

        logging.info('%s version %s ends normally' %
                     (self.settings.progname, self.settings.version))

    def compute_setting_values(self, settings):
        '''Compute setting values after configs and options are parsed.

        You can override this method to implement a default value for
        a setting that is dependent on another setting. For example,
        you might have settings "url" and "protocol", where protocol
        gets set based on the schema of the url, unless explicitly
        set by the user. So if the user sets just the url, to
        "http://www.example.com/", the protocol would be set to
        "http". If the user sets both url and protocol, the protocol
        does not get modified by compute_setting_values.

        '''

    def add_subcommand(
        self, name, func, arg_synopsis=None, aliases=None, hidden=False):
        '''Add a subcommand.

        Normally, subcommands are defined by add ``cmd_foo`` methods
        to the application class. However, sometimes it is more convenient
        to have them elsewhere (e.g., in plugins). This method allows
        doing that.

        The callback function must accept a list of command line
        non-option arguments.

        '''

        if name not in self.subcommands:
            self.subcommands[name] = func
            self.cmd_synopsis[name] = arg_synopsis
            self.subcommand_aliases[name] = aliases or []
            if hidden: # pragma: no cover
                self.hidden_subcommands.add(name)

    def add_default_subcommands(self):
        if 'help' not in self.subcommands:
            self.add_subcommand('help', self.help)
        if 'help-all' not in self.subcommands:
            self.add_subcommand('help-all', self.help_all)

    def get_subcommand_help_formatter(self, *a, **kw): # pragma: no cover
        '''Return class to format subcommand documentation.

        The class will be used to format the full docstring of a
        subcommand description, but not other help texts.

        The class must have a compatible interface with
        cliapp.TextFormat.

        This method exists for those applications who want to change
        how help texts are formatted, e.g., to allow Markdown or
        reStructuredText.

        '''

        return cliapp.TextFormat(*a, **kw)

    def _help_helper(self, args, show_all): # pragma: no cover
        try:
            width = int(os.environ.get('COLUMNS', '78'))
        except ValueError:
            width = 78


        if args:
            cmd = args[0]
            if cmd not in self.subcommands:
                raise cliapp.AppException('Unknown subcommand %s' % cmd)
            usage = self._format_usage_for(cmd)
            fmt = self.get_help_text_formatter(width=width)
            description = fmt.format(self._format_subcommand_help(cmd))
            text = '%s\n\n%s' % (usage, description)
        else:
            usage = self._format_usage(all=show_all)
            fmt = cliapp.TextFormat(width=width)
            description = fmt.format(self._format_description(all=show_all))
            text = '%s\n\n%s' % (usage, description)

        text = self.settings.progname.join(text.split('%prog'))
        self.output.write(text)

    def help(self, args): # pragma: no cover
        '''Print help.'''
        self._help_helper(args, False)

    def help_all(self, args): # pragma: no cover
        '''Print help, including hidden subcommands.'''
        self._help_helper(args, True)

    def _subcommand_methodnames(self):
        return [x
                 for x in dir(self)
                 if x.startswith('cmd_') and
                    inspect.ismethod(getattr(self, x))]

    def _normalize_cmd(self, cmd):
        return 'cmd_%s' % cmd.replace('-', '_')

    def _unnormalize_cmd(self, method):
        assert method.startswith('cmd_')
        return method[len('cmd_'):].replace('_', '-')

    def _format_usage(self, all=False):
        '''Format usage, possibly also subcommands, if any.'''
        if self.subcommands:
            lines = []
            prefix = 'Usage:'
            for cmd in sorted(self.subcommands.keys()):
                if all or cmd not in self.hidden_subcommands:
                    args = self.cmd_synopsis.get(cmd, '') or ''
                    lines.append(
                        '%s %%prog [options] %s %s' % (prefix, cmd, args))
                    prefix = ' ' * len(prefix)
            return '\n'.join(lines)
        else:
            return None

    def _format_usage_for(self, cmd): # pragma: no cover
        args = self.cmd_synopsis.get(cmd, '') or ''
        return 'Usage: %%prog [options] %s %s' % (cmd, args)

    def _format_description(self, all=False):
        '''Format OptionParser description, with subcommand support.'''
        if self.subcommands:
            summaries = []
            for cmd in sorted(self.subcommands.keys()):
                if all or cmd not in self.hidden_subcommands:
                    summaries.append(self._format_subcommand_summary(cmd))
            cmd_desc = ''.join(summaries)
            return '%s\n%s' % (self._description or '', cmd_desc)
        else:
            return self._description

    def _format_subcommand_summary(self, cmd): # pragma: no cover
        method = self.subcommands[cmd]
        doc = method.__doc__ or ''
        lines = doc.splitlines()
        if lines:
            summary = lines[0].strip()
        else:
            summary = ''
        return '* %%prog %s: %s\n' % (cmd, summary)

    def _format_subcommand_help(self, cmd): # pragma: no cover
        method = self.subcommands[cmd]
        doc = method.__doc__ or ''
        t = doc.split('\n', 1)
        if len(t) == 1:
            return doc
        else:
            first, rest = t
            return first + '\n' + textwrap.dedent(rest)

    def setup_logging(self): # pragma: no cover
        '''Set up logging.'''

        level_name = self.settings['log-level']
        levels = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL,
            'fatal': logging.FATAL,
        }
        level = levels.get(level_name, logging.INFO)

        if self.settings['log'] == 'syslog':
            handler = self.setup_logging_handler_for_syslog()
        elif self.settings['log'] and self.settings['log'] != 'none':
            handler = LogHandler(
                            self.settings['log'],
                            perms=int(self.settings['log-mode'], 8),
                            maxBytes=self.settings['log-max'],
                            backupCount=self.settings['log-keep'],
                            delay=False)
            fmt = '%(asctime)s %(levelname)s %(message)s'
            datefmt = '%Y-%m-%d %H:%M:%S'
            formatter = logging.Formatter(fmt, datefmt)
            handler.setFormatter(formatter)
        else:
            handler = self.setup_logging_handler_to_none()
            # reduce amount of pointless I/O
            level = logging.FATAL

        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(level)

    def setup_logging_handler_for_syslog(self): # pragma: no cover
        '''Setup a logging.Handler for logging to syslog.'''

        handler = logging.handlers.SysLogHandler(address='/dev/log')
        progname = '%%'.join(self.settings.progname.split('%'))
        fmt = progname + ": %(levelname)s %(message)s"
        formatter = logging.Formatter(fmt)
        handler.setFormatter(formatter)

        return handler

    def setup_logging_handler_to_none(self): # pragma: no cover
        '''Setup a logging.Handler that does not log anything anywhere.'''

        handler = logging.FileHandler('/dev/null')
        return handler

    def setup_logging_handler_to_file(self): # pragma: no cover
        '''Setup a logging.Handler for logging to a named file.'''

        handler = LogHandler(
                        self.settings['log'],
                        perms=int(self.settings['log-mode'], 8),
                        maxBytes=self.settings['log-max'],
                        backupCount=self.settings['log-keep'],
                        delay=False)
        fmt = self.setup_logging_format()
        datefmt = self.setup_logging_timestamp()
        formatter = logging.Formatter(fmt, datefmt)
        handler.setFormatter(formatter)

        return handler

    def setup_logging_format(self): # pragma: no cover
        '''Return format string for log messages.'''
        return '%(asctime)s %(levelname)s %(message)s'

    def setup_logging_timestamp(self): # pragma: no cover
        '''Return timestamp format string for log message.'''
        return '%Y-%m-%d %H:%M:%S'

    def log_config(self):
        logging.info('%s version %s starts' %
                     (self.settings.progname, self.settings.version))
        logging.debug('sys.argv: %s' % sys.argv)

        logging.debug('current working directory: %s' % os.getcwd())
        logging.debug('uid: %d' % os.getuid())
        logging.debug('effective uid: %d' % os.geteuid())
        logging.debug('gid: %d' % os.getgid())
        logging.debug('effective gid: %d' % os.getegid())

        logging.debug('environment variables:')
        for name in os.environ:
            logging.debug('environment: %s=%s' % (name, os.environ[name]))
        cp = self.settings.as_cp()
        f = StringIO.StringIO()
        cp.write(f)
        logging.debug('Config:\n%s' % f.getvalue())
        logging.debug('Python version: %s' % sys.version)

    def app_directory(self):
        '''Return the directory where the application class is defined.

        Plugins are searched relative to this directory, in the subdirectory
        specified by self.plugin_subdir.

        '''

        module_name = self.__class__.__module__
        module = sys.modules[module_name]
        dirname = os.path.dirname(module.__file__) or '.'
        return dirname

    def setup_plugin_manager(self):
        '''Create a plugin manager.'''
        self.pluginmgr = cliapp.PluginManager()
        dirname = os.path.join(self.app_directory(), self.plugin_subdir)
        self.pluginmgr.locations = [dirname]

    def enable_plugins(self): # pragma: no cover
        '''Load plugins.'''
        for plugin in self.pluginmgr.plugins:
            plugin.app = self
            plugin.setup()
        self.pluginmgr.enable_plugins()

    def disable_plugins(self):
        self.pluginmgr.disable_plugins()

    def parse_args(self, args, configs_only=False):
        '''Parse the command line.

        Return list of non-option arguments.

        '''

        return self.settings.parse_args(
            args, configs_only=configs_only, arg_synopsis=self.arg_synopsis,
            cmd_synopsis=self.cmd_synopsis,
            compute_setting_values=self.compute_setting_values)

    def setup(self):
        '''Prepare for process_args.

        This method is called just before enabling plugins. By default it
        does nothing, but subclasses may override it with a suitable
        implementation. This is easier than overriding process_args
        itself.

        '''

    def cleanup(self):
        '''Clean up after process_args.

        This method is called just after process_args. By default it
        does nothing, but subclasses may override it with a suitable
        implementation. This is easier than overriding process_args
        itself.

        '''

    def process_args(self, args):
        '''Process command line non-option arguments.

        The default is to call process_inputs with the argument list,
        or to invoke the requested subcommand, if subcommands have
        been defined.

        '''


        if self.subcommands:
            if not args:
                raise SystemExit('must give subcommand')

            cmd = args[0]
            if cmd not in self.subcommands:
                for name in self.subcommand_aliases:
                    if cmd in self.subcommand_aliases[name]:
                        cmd = name
                        break
                else:
                    raise SystemExit('unknown subcommand %s' % args[0])

            method = self.subcommands[cmd]
            method(args[1:])
        else:
            self.process_inputs(args)

    def process_inputs(self, args):
        '''Process all arguments as input filenames.

        The default implementation calls process_input for each
        input filename. If no filenames were given, then
        process_input is called with ``-`` as the argument name.
        This implements the usual Unix command line practice of
        reading from stdin if no inputs are named.

        The attributes ``fileno``, ``global_lineno``, and ``lineno`` are set,
        and count files and lines. The global line number is the
        line number as if all input files were one.

        '''

        for arg in args or ['-']:
            self.process_input(arg)

    def open_input(self, name, mode='r'):
        '''Open an input file for reading.

        The default behaviour is to open a file named on the local
        filesystem. A subclass might override this behavior for URLs,
        for example.

        The optional mode argument speficies the mode in which the file
        gets opened. It should allow reading. Some files should perhaps
        be opened in binary mode ('rb') instead of the default text mode.

        '''

        if name == '-':
            return sys.stdin
        else:
            return open(name, mode)

    def process_input(self, name, stdin=sys.stdin):
        '''Process a particular input file.

        The ``stdin`` argument is meant for unit test only.

        '''

        self.fileno += 1
        self.lineno = 0
        f = self.open_input(name)
        for line in f:
            self.global_lineno += 1
            self.lineno += 1
            self.process_input_line(name, line)
        if f != stdin:
            f.close()

    def process_input_line(self, filename, line):
        '''Process one line of the input file.

        Applications that are line-oriented can redefine only this method in
        a subclass, and should not need to care about the other methods.

        '''

    def runcmd(self, *args, **kwargs): # pragma: no cover
        return cliapp.runcmd(*args, **kwargs)

    def runcmd_unchecked(self, *args, **kwargs): # pragma: no cover
        return cliapp.runcmd_unchecked(*args, **kwargs)

    def _vmrss(self): # pragma: no cover
        '''Return current resident memory use, in KiB.'''
        if platform.system() != 'Linux':
            return 0
        try:
            f = open('/proc/self/status')
        except IOError:
            return 0
        rss = 0
        for line in f:
            if line.startswith('VmRSS'):
                rss = line.split()[1]
        f.close()
        return rss

    def dump_memory_profile(self, msg): # pragma: no cover
        '''Log memory profiling information.

        Get the memory profiling method from the dump-memory-profile
        setting, and log the results at DEBUG level. ``msg`` is a
        message the caller provides to identify at what point the profiling
        happens.

        '''

        kind = self.settings['dump-memory-profile']
        interval = self.settings['memory-dump-interval']

        if kind == 'none':
            return

        now = time.time()
        if self.last_memory_dump + interval > now:
            return
        self.last_memory_dump = now

        # Log wall clock and CPU times for self, children.
        utime, stime, cutime, cstime, elapsed_time = os.times()
        duration = elapsed_time - self._started
        logging.debug('process duration: %s s' % duration)
        logging.debug('CPU time, in process: %s s' % utime)
        logging.debug('CPU time, in system: %s s' % stime)
        logging.debug('CPU time, in children: %s s' % cutime)
        logging.debug('CPU time, in system for children: %s s' % cstime)

        logging.debug('dumping memory profiling data: %s' % msg)
        logging.debug('VmRSS: %s KiB' % self._vmrss())

        if kind == 'simple':
            return

        # These are fairly expensive operations, so we only log them
        # if we're doing expensive stuff anyway.
        logging.debug('# objects: %d' % len(gc.get_objects()))
        logging.debug('# garbage: %d' % len(gc.garbage))

        if kind == 'heapy':
            from guppy import hpy
            h = hpy()
            logging.debug('memory profile:\n%s' % h.heap())
        elif kind == 'meliae':
            filename = 'obnam-%d.meliae' % self.memory_dump_counter
            logging.debug('memory profile: see %s' % filename)
            from meliae import scanner
            scanner.dump_all_objects(filename)
            self.memory_dump_counter += 1

