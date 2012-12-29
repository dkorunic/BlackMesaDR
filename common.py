#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""Common functions for BlackMesa Disaster Recovery project
"""

__copyright__ = """Copyright (C) 2010  Dinko Korunic, InfoMAR

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
"""

__version__ = '$Id: common.py,v de859cceb463 2010/10/28 09:10:17 dinko $'


import os
import fcntl
import cPickle
import hashlib
import signal
import subprocess
import sys
import logging
import logging.handlers
import getopt
import atexit


def sha1sum(path):
    """Calculate SHA1 sum of given file. Returns SHA1 hex digest as
    string.
    """
    sha1 = hashlib.sha1()
    sha1file = open(path, 'rb')
    # read chunks of 128k
    for chunk in iter(lambda: sha1file.read(131072), ''):
        sha1.update(chunk)
    sha1file.close()
    return sha1.hexdigest()

def write_atomic(path, myobject):
    """Serialize and write atomically an object into file with locking.
    Does not return anything.
    """
    lockfile = open(path + '.lock', 'a')
    fcntl.flock(lockfile, fcntl.LOCK_EX)
    picklefile = None
    try:
        try:
            picklefile = open(path + '.tmp', 'wb')
            cPickle.dump(myobject, picklefile, -1)
        finally:
            if picklefile:
                picklefile.close()
        os.rename(path + '.tmp', path)
    finally:
        fcntl.flock(lockfile, fcntl.LOCK_UN)
        lockfile.close()

def read_atomic(path):
    """Read from file and serialize with locking. Returns unserialized
    unpickled object.
    """
    lockfile = open(path + '.lock', 'a')
    fcntl.flock(lockfile, fcntl.LOCK_EX)
    picklefile = None
    try:
        picklefile = open(path, 'rb')
        myobject = cPickle.load(picklefile)
    finally:
        if picklefile:
            picklefile.close()
        fcntl.flock(lockfile, fcntl.LOCK_UN)
        lockfile.close()
    return myobject

def run_with_timeout(args, cwd=None, shell=False, kill_tree=True,
        timeout=-1):
    """Run a command with a timeout after which it will be forcibly
    killed. (c) Alex Martelli
    """
    class Alarm(Exception):
        pass
    def alarm_handler(signum, frame):
        raise Alarm
    p = subprocess.Popen(args, shell=shell, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if timeout != -1:
        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(timeout)
    try:
        stdout, stderr = p.communicate()
        if timeout != -1:
            signal.alarm(0)
    except Alarm:
        pids = [p.pid]
        if kill_tree:
            pids.extend(get_process_children(p.pid))
        for pid in pids:
            os.kill(pid, signal.SIGKILL)
        return -9, '', ''
    return p.returncode, stdout, stderr

def get_process_children(pid):
    """Get all children from a given PID. (c) Alex Martelli
    """
    p = subprocess.Popen('ps --no-headers -o pid --ppid %d' % pid,
            shell = True, stdout = subprocess.PIPE,
            stderr = subprocess.PIPE)
    stdout, stderr = p.communicate()
    return [int(p) for p in stdout.split()]

def setup_logging(progname, console_loglevel, file_loglevel, logfmt,
        logfile, datefmt):
    """Setup common logging for all programs. Returns typical logger
    object.
    """
    # system-wide defaults
    logger = logging.getLogger(progname)
    logger.setLevel(logging.DEBUG)

    # logging to file
    fh = logging.handlers.RotatingFileHandler(logfile, maxBytes=30720,
            backupCount=5)
    fh.setLevel(file_loglevel)
    formatter = logging.Formatter(logfmt, datefmt)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # logging to console (makes sense only if running in foreground)
    if console_loglevel:
        ch = logging.StreamHandler()
        ch.setLevel(console_loglevel)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger

def print_usage():
    """Print common program usage. Does not return anything.
    """
    usage = """Usage: program [OPTION]...
Possible and optional arguments:
-v, --version       print program name and version,
-f, --foreground    keep running in foreground, as opposite to default,
-d, --debug         elevate all logs to debug level,
-c, --consoledebug  enable console debugging (implies --foreground).
"""
    print >> sys.stderr, usage

def parse_argv(argv, globaldict):
    """Parse given arguments. Does not return anything.
    """
    try:
        opts, args = getopt.getopt(argv[1:], 'hvfdc', ['help', 'version',
            'foreground', 'debug', 'consoledebug'])
    except getopt.GetoptError, err:
        print str(err)
        print_usage()
        sys.exit(2)

    for o, a in opts:
        if o in ('-h', '--help'):
            print_usage()
            sys.exit(0)
        if o in ('-v', '--version'):
            print argv[0], ':', globaldict['__version__']
            sys.exit(0)
        elif o in ('-f', '--foreground'):
            globaldict['foreground'] = True
        elif o in ('-d', '--debug'):
            globaldict['FILE_LOG_LEVEL'] = logging.DEBUG
        elif o in ('-c', '--consoledebug'):
            globaldict['FILE_LOG_LEVEL'] = logging.DEBUG
            globaldict['CONSOLE_LOG_LEVEL'] = logging.DEBUG
            globaldict['foreground'] = True
        else:
            assert False, 'unhandled option'

def checkpid(pidfile):
    """Check if process with given pidfile is running. Does not return
    anything.
    """
    pid = None
    if pidfile:
        pf = None
        try:
            pf = open(pidfile, 'r')
            pid = int(pf.read().strip())
        except IOError:
            pid = None
        finally:
            if pf:
                pf.close()
    if pid:
        try:
            os.kill(pid, signal.SIGCHLD)
            print >> sys.stderr, 'Daemon already running with PID %s. ' \
                'Bailing out.' % pid
            sys.exit(1)
        except OSError:
            pass

def writepid(pidfile):
    """Write PID of running process into given pidfile. Does not return
    anything.
    """
    pid = str(os.getpid())
    pf = None
    try:
        pf = open(pidfile, 'w+')
        pf.write('%s\n' % pid)
    finally:
        if pf:
            pf.close()

def delpid(pidfile):
    """Remove PID file. Typically used as atexit handler. Does not return
    anything.
    """
    if os.path.exists(pidfile):
        os.remove(pidfile)

def daemonize(pidfile=None, foreground=False):
    """Do the usual Unix style daemonization magic. Does not return
    anything.
    """
    # check if already running
    checkpid(pidfile)

    if not foreground:
        # first fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as (errno, strerr):
            print >> sys.stderr, 'Fork failed: %s (%s)' % (errno, strerr)
            sys.exit(1)

        # chdir, setsid and umask
        os.chdir('/')
        os.setsid()
        os.umask(0)

        # second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as (errno, strerr):
            print >> sys.stderr, 'Fork failed: %s (%s)' % (errno, strerr)
            sys.exit(1)

        # closing fds
        os.close(sys.stdin.fileno())
        os.close(sys.stdout.fileno())
        os.close(sys.stderr.fileno())

    # pidfile and exit handlers
    if pidfile:
        atexit.register(delpid, pidfile)
        writepid(pidfile)
