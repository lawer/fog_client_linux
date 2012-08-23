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
        for method_name in self._subcommand_methodnames():
            cmd = self._unnormalize_cmd(method_name)
            self.subcommands[cmd] = getattr(self, method_name)
        
        self.settings = cliapp.Settings(progname, version, 
                                        usage=self._format_usage,
                                        description=self._format_description,
                                        epilog=epilog)

        self.plugin_subdir = 'plugins'
        
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

    def _run(self, args=None, stderr=sys.stderr, log=logging.critical):
        try:
            self.add_settings()
            self.setup_plugin_manager()
            
            # A little bit of trickery here to make --no-default-configs and
            # --config=foo work right: we first parse the command line once,
            # and pick up any config files. Then we read configs. Finally,
            # we re-parse the command line to allow any options to override
            # config file settings.
            self.setup()
            self.enable_plugins()
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
        except AppException, e:
            log(traceback.format_exc())
            stderr.write('ERROR: %s\n' % str(e))
            sys.exit(1)
        except SystemExit, e:
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
    
    def add_subcommand(self, name, func, arg_synopsis=None):
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

    def _format_usage(self):
        '''Format usage, possibly also subcommands, if any.'''
        if self.subcommands:
            lines = []
            prefix = 'Usage:'
            for cmd in sorted(self.subcommands.keys()):
                args = self.cmd_synopsis.get(cmd, '')
                lines.append('%s %%prog [options] %s %s' % (prefix, cmd, args))
                prefix = ' ' * len(prefix)
            return '\n'.join(lines)
        else:
            return None

    def _format_description(self):
        '''Format OptionParser description, with subcommand support.'''
        if self.subcommands:
            paras = []
            for cmd in sorted(self.subcommands.keys()):
                paras.append(self._format_subcommand_description(cmd))
            cmd_desc = '\n\n'.join(paras)
            return '%s\n\n%s' % (self._description or '', cmd_desc)
        else:
            return self._description

    def _format_subcommand_description(self, cmd): # pragma: no cover

        def remove_empties(lines):
            while lines and not lines[0].strip():
                del lines[0]

        def split_para(lines):
            para = []
            while lines and lines[0].strip():
                para.append(lines[0].strip())
                del lines[0]
            return para

        indent = ' ' * 4
        method = self.subcommands[cmd]
        doc = method.__doc__ or ''
        lines = doc.splitlines()
        remove_empties(lines)
        if lines:
            heading = '* %s -- %s' % (cmd, lines[0])
            result = [heading]
            del lines[0]
            remove_empties(lines)
            while lines:
                result.append('')
                para_lines = split_para(lines)
                para_text = ' '.join(para_lines)
                result.append(para_text)
                remove_empties(lines)
            return '\n'.join(result)
        else:
            return '* %s' % cmd
        
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
            handler = logging.handlers.SysLogHandler(address='/dev/log')
        elif self.settings['log'] and self.settings['log'] != 'none':
            handler = LogHandler(
                            self.settings['log'],
                            perms=int(self.settings['log-mode'], 8),
                            maxBytes=self.settings['log-max'], 
                            backupCount=self.settings['log-keep'],
                            delay=False)
        else:
            handler = logging.FileHandler('/dev/null')
            # reduce amount of pointless I/O
            level = logging.FATAL

        fmt = '%(asctime)s %(levelname)s %(message)s'
        datefmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter(fmt, datefmt)
        handler.setFormatter(formatter)

        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(level)

    def log_config(self):
        logging.info('%s version %s starts' % 
                     (self.settings.progname, self.settings.version))
        logging.debug('sys.argv: %s' % sys.argv)
        logging.debug('environment variables:')
        for name in os.environ:
            logging.debug('environment: %s=%s' % (name, os.environ[name]))
        cp = self.settings.as_cp()
        f = StringIO.StringIO()
        cp.write(f)
        logging.debug('Config:\n%s' % f.getvalue())

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

        return self.settings.parse_args(args, configs_only=configs_only,
                                         arg_synopsis=self.arg_synopsis,
                                         cmd_synopsis=self.cmd_synopsis)

    def setup(self):
        '''Prepare for process_args.
        
        This method is called just before process_args. By default it
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
            if args[0] in self.subcommands:
                method = self.subcommands[args[0]]
                method(args[1:])
            else:
                raise SystemExit('unknown subcommand %s' % args[0])
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
        f = open('/proc/self/status')
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

        if kind == 'none':
            return

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

