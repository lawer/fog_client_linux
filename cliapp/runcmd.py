# Copyright (C) 2011, 2012  Lars Wirzenius
# Copyright (C) 2012  Codethink Limited
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
import fcntl
import logging
import os
import select
import subprocess

import cliapp


def runcmd(argv, *args, **kwargs):
    '''Run external command or pipeline.

    Example: ``runcmd(['grep', 'foo'], ['wc', '-l'],
                      feed_stdin='foo\nbar\n')``

    Return the standard output of the command.

    Raise ``cliapp.AppException`` if external command returns
    non-zero exit code. ``*args`` and ``**kwargs`` are passed
    onto ``subprocess.Popen``.

    '''

    our_options = (
        ('ignore_fail', False),
        ('log_error', True),
    )
    opts = {}
    for name, default in our_options:
        opts[name] = default
        if name in kwargs:
            opts[name] = kwargs[name]
            del kwargs[name]

    exit, out, err = runcmd_unchecked(argv, *args, **kwargs)
    if exit != 0:
        msg = 'Command failed: %s\n%s' % (' '.join(argv), err)
        if opts['ignore_fail']:
            if opts['log_error']:
                logging.info(msg)
        else:
            if opts['log_error']:
                logging.error(msg)
            raise cliapp.AppException(msg)
    return out

def runcmd_unchecked(argv, *argvs, **kwargs):
    '''Run external command or pipeline.

    Return the exit code, and contents of standard output and error
    of the command.

    See also ``runcmd``.

    '''

    argvs = [argv] + list(argvs)
    logging.debug('run external command: %s' % repr(argvs))

    def pop_kwarg(name, default):
        if name in kwargs:
            value = kwargs[name]
            del kwargs[name]
            return value
        else:
            return default

    feed_stdin = pop_kwarg('feed_stdin', '')
    pipe_stdin = pop_kwarg('stdin', subprocess.PIPE)
    pipe_stdout = pop_kwarg('stdout', subprocess.PIPE)
    pipe_stderr = pop_kwarg('stderr', subprocess.PIPE)

    try:
        pipeline = _build_pipeline(argvs,
                                   pipe_stdin,
                                   pipe_stdout,
                                   pipe_stderr,
                                   kwargs)
        return _run_pipeline(pipeline, feed_stdin, pipe_stdin,
                              pipe_stdout, pipe_stderr)
    except OSError, e: # pragma: no cover
        if e.errno == errno.ENOENT and e.filename is None:
            e.filename = argv[0]
            raise e
        else:
            raise

def _build_pipeline(argvs, pipe_stdin, pipe_stdout, pipe_stderr, kwargs):
    procs = []
    for i, argv in enumerate(argvs):
        if i == 0 and i == len(argvs) - 1:
            stdin = pipe_stdin
            stdout = pipe_stdout
            stderr = pipe_stderr
        elif i == 0:
            stdin = pipe_stdin
            stdout = subprocess.PIPE
            stderr = pipe_stderr
        elif i == len(argvs) - 1:
            stdin = procs[-1].stdout
            stdout = pipe_stdout
            stderr = pipe_stderr
        else:
            stdin = procs[-1].stdout
            stdout = subprocess.PIPE
            stderr = pipe_stderr
        p = subprocess.Popen(argv, stdin=stdin, stdout=stdout,
                             stderr=stderr, close_fds=True, **kwargs)
        procs.append(p)

    return procs

def _run_pipeline(procs, feed_stdin, pipe_stdin, pipe_stdout, pipe_stderr):

    stdout_eof = False
    stderr_eof = False
    out = []
    err = []
    pos = 0
    io_size = 1024

    def set_nonblocking(fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
        flags = flags | os.O_NONBLOCK
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)

    if feed_stdin and pipe_stdin == subprocess.PIPE:
        set_nonblocking(procs[0].stdin.fileno())
    if pipe_stdout == subprocess.PIPE:
        set_nonblocking(procs[-1].stdout.fileno())
    if pipe_stderr == subprocess.PIPE:
        set_nonblocking(procs[-1].stderr.fileno())

    def still_running():
        for p in procs:
            p.poll()
        for p in procs:
            if p.returncode is None:
                return True
        if pipe_stdout == subprocess.PIPE and not stdout_eof:
            return True
        if pipe_stderr == subprocess.PIPE and not stderr_eof:
            return True # pragma: no cover
        return False

    while still_running():
        rlist = []
        if not stdout_eof and pipe_stdout == subprocess.PIPE:
            rlist.append(procs[-1].stdout)
        if not stderr_eof and pipe_stderr == subprocess.PIPE:
            rlist.append(procs[-1].stderr)

        wlist = []
        if pipe_stdin == subprocess.PIPE and pos < len(feed_stdin):
            wlist.append(procs[0].stdin)

        if rlist or wlist:
            try:
                r, w, x = select.select(rlist, wlist, [])
            except select.error, e: # pragma: no cover
                err, msg = e.args
                if err == errno.EINTR:
                    break
                raise
        else:
            break # Let's not busywait waiting for processes to die.

        if procs[0].stdin in w and pos < len(feed_stdin):
            data = feed_stdin[pos : pos+io_size]
            procs[0].stdin.write(data)
            pos += len(data)
            if pos >= len(feed_stdin):
                procs[0].stdin.close()

        if procs[-1].stdout in r:
            data = procs[-1].stdout.read(io_size)
            if data:
                out.append(data)
            else:
                stdout_eof = True

        if procs[-1].stderr in r:
            data = procs[-1].stderr.read(io_size)
            if data:
                err.append(data)
            else:
                stderr_eof = True

    while still_running():
        for p in procs:
            if p.returncode is None:
                p.wait()

    errorcodes = [p.returncode for p in procs if p.returncode != 0] or [0]
    return errorcodes[-1], ''.join(out), ''.join(err)



def shell_quote(s):
    '''Return a shell-quoted version of s.'''

    lower_ascii = 'abcdefghijklmnopqrstuvwxyz'
    upper_ascii = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    digits = '0123456789'
    punctuation = '-_/=.,:'
    safe = set(lower_ascii + upper_ascii + digits + punctuation)

    quoted = []
    for c in s:
        if c in safe:
            quoted.append(c)
        elif c == "'":
            quoted.append('"\'"')
        else:
            quoted.append("'%c'" % c)

    return ''.join(quoted)


def ssh_runcmd(target, argv, **kwargs): # pragma: no cover
    '''Run command in argv on remote host target.

    This is similar to runcmd, but the command is run on the remote
    machine. The command is given as an argv array; elements in the
    array are automatically quoted so they get passed to the other
    side correctly.

    An optional ``tty=`` parameter can be passed to ``ssh_runcmd`` in
    order to force or disable pseudo-tty allocation. This is often
    required to run ``sudo`` on another machine and might be useful
    in other situations as well. Supported values are ``tty=True`` for
    forcing tty allocation, ``tty=False`` for disabling it and
    ``tty=None`` for not passing anything tty related to ssh.

    With the ``tty`` option,
    ``cliapp.runcmd(['ssh', '-tt', 'user@host', '--', 'sudo', 'ls'])``
    can be written as
    ``cliapp.ssh_runcmd('user@host', ['sudo', 'ls'], tty=True)``
    which is more intuitive.

    The target is given as-is to ssh, and may use any syntax ssh
    accepts.

    Environment variables may or may not be passed to the remote
    machine: this is dependent on the ssh and sshd configurations.
    Invoke env(1) explicitly to pass in the variables you need to
    exist on the other end.

    Pipelines are not supported.

    '''

    tty = kwargs.get('tty', None)
    if tty:
        ssh_cmd = ['ssh', '-tt', target, '--']
    elif tty is False:
        ssh_cmd = ['ssh', '-T', target, '--']
    else:
        ssh_cmd = ['ssh', target, '--']
    if 'tty' in kwargs:
        del kwargs['tty']

    local_argv = ssh_cmd + map(shell_quote, argv)
    return runcmd(local_argv, **kwargs)

