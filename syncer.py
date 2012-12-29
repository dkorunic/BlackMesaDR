#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""File-syncing and remote deletion part of BlackMesa Disaster Recovery project
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

__version__ = '$Id: syncer.py,v de859cceb463 2010/10/28 09:10:17 dinko $'


import time
import os
import sys
import collections

from common import write_atomic, read_atomic, run_with_timeout, \
    setup_logging, parse_argv, daemonize
from settings import *


FilesSyncQueue = collections.deque()
logger = None
foreground = False


def check_updated(poporig):
    """Check if sync queue has been updated in meantime. Returns True if
yes, False otherwise.
    """
    global FilesSyncQueue
    global logger

    FilesSyncQueue = read_atomic(FILES_SYNC_FILE)
    popnew = FilesSyncQueue.popleft()
    if poporig == popnew:
        write_atomic(FILES_SYNC_FILE, FilesSyncQueue)
    else:
        logger.warn('Oops, left side of file sync queue %s has changed. '
                'This should never happen.' % FilesSyncQueue)
        return True
    return False

def decisionlogic():
    """Main decision/syncing loop. Returns False if no more actions to
perform.
    """
    global FilesSyncQueue
    global logger

    # reread fresh status on every run
    FilesSyncQueue = read_atomic(FILES_SYNC_FILE)

    # ignore if no actions pending
    if len(FilesSyncQueue) == 0:
        return False

    # pop the necessary values from sync queue
    poporig = FilesSyncQueue.popleft()
    myfile, action, myperm = poporig

    # check if file exists at all when resyncing and forget action if not
    if action == 'sync' and not os.path.exists(myfile):
        logger.info('Tried to sync nonexisting file %s. Ignoring.' %
                myfile)
        check_updated(poporig)
        return

    # get relative path of file and relative path of directories above
    _, relpath = myfile.split('%s/' % WATCH_DIR)

    # return values
    retval = None

    # execute pre-command on remote directory (usually mkdir)
    if action == 'sync':
        # only if synced file in remote subdirectory
        if relpath.find('/') != -1:
            relpathdir, _ = relpath.rsplit('/', 1)
            logger.debug('Executing pre_command: %s.' % PRE_COMMAND %
                    relpathdir)
            retval = run_with_timeout(PRE_COMMAND % relpathdir, shell=True,
                    timeout=600)

        logger.debug('Executing sync_command: %s.' % SYNC_COMMAND %
                (myfile, relpath))
        retval = run_with_timeout(SYNC_COMMAND % (myfile, relpath),
                shell=True, timeout=3600)

        # most fatal error, log stdout and stderr too
        if retval[0] != 0 and retval[0] != -9:
            logger.critical('Fatal error %d when syncing remote file %s. '
                    'STDOUT: %s. STDERR: %s.' % (retval[0], myfile,
                        retval[1], retval[2]))
            #sys.exit(1)

    # remove remote file
    elif action == 'remove':
        logger.debug('Executing remove_command: %s.' % REMOVE_COMMAND %
                relpath)
        retval = run_with_timeout(REMOVE_COMMAND % relpath, shell=True,
                timeout=600)

    # make remote directory with given permissions
    elif action == 'make_dir':
        logger.debug('Executing make_dir_command: %s.' % MAKE_DIR_COMMAND
                % (myperm, relpath))
        retval = run_with_timeout(MAKE_DIR_COMMAND % (myperm, relpath),
                shell=True, timeout=600)

    # remove remote directory
    elif action == 'remove_dir':
        logger.debug('Executing remove_dir_command: %s.' %
                REMOVE_DIR_COMMAND % relpath)
        retval = run_with_timeout(REMOVE_DIR_COMMAND % relpath,
                shell=True, timeout=600)

    # change permissions of a remote file or directory
    elif action == 'change_perm':
        logger.debug('Executing change_perm: %s.' % CHMOD_COMMAND %
                (myperm, relpath))
        retval = run_with_timeout(CHMOD_COMMAND % (myperm, relpath),
                shell=True, timeout=600)

    if retval and retval[0] != 0:
        # remote command timeouted, print reasons in 1/stdout and 2/stderr
        # and sleep for extended time
        logger.warn('Remote action %s on file %s failed. Sleeping.' %
                (action, relpath))
        time.sleep(TIMEOUT_SLEEP_TIME)
        return

    # final pop and delete after all is done
    check_updated(poporig)

    return True

def main(argv):
    global FilesSyncQueue
    global logger
    global foreground

    # parse argv
    parse_argv(argv, globals())

    # daemonize
    daemonize(SYNCER_PID, foreground)

    # initialize logging
    logger = setup_logging(argv[0], CONSOLE_LOG_LEVEL, FILE_LOG_LEVEL,
            LOG_FORMAT, SYNCER_LOG, DATE_FORMAT)

    # sanity check
    if not os.path.isdir(WATCH_DIR):
        logger.critical('Watched directory %s does not exist. '
                'Bailing out.' % WATCH_DIR)
        sys.exit(1)

    # if FilesSyncQueue is nonexistant or damaged, truncate it
    try:
        FilesSyncQueue = read_atomic(FILES_SYNC_FILE)
    except (IOError, AttributeError, EOFError):
        logger.warn('Unusable file sync queue file %s. Recreating.' %
                FILES_SYNC_FILE)
        pass
    write_atomic(FILES_SYNC_FILE, FilesSyncQueue)

    # start main loop
    logger.debug('File sync service starting... Entering wait loop.')
    while True:
        while decisionlogic():
            pass
        time.sleep(SLEEP_TIME)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
