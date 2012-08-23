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

    if 'ignore_fail' in kwargs:
        ignore_fail = kwargs['ignore_fail']
        del kwargs['ignore_fail']
    else:
        ignore_fail = False

    exit, out, err = runcmd_unchecked(argv, *args, **kwargs)
    if exit != 0:
        msg = 'Command failed: %s\n%s' % (' '.join(argv), err)
        if ignore_fail:
            logging.info(msg)
        else:
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
        elif i == len(argv) - 1:
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
            r, w, x = select.select(rlist, wlist, [])
        else:
            r = w = [] # pragma: no cover

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

    return procs[-1].returncode, ''.join(out), ''.join(err)

