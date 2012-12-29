#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""Checksumming part of BlackMesa Disaster Recovery project
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

__version__ = '$Id: summer.py,v de859cceb463 2010/10/28 09:10:17 dinko $'


import time
import os
import stat
import sys
import random
import collections

from common import write_atomic, read_atomic, sha1sum, setup_logging, \
    parse_argv, daemonize
from settings import *


FilesActionMap = {}
FilesHashMap = {}
FilesSyncQueue = collections.deque()
logger = None
foreground = False


def check_updated(monitor_action, monitor_timestamp, myfile):
    """Check if action map has been updated in the meantime. Returns True
if yes, False otherwise.
    """
    global FilesActionMap
    global logger

    # reread status and check if there are newer changes
    FilesActionMap = read_atomic(FILES_STATUS_FILE)

    _, monitor_timestampnew = FilesActionMap[myfile]
    if monitor_timestampnew == monitor_timestamp:
        # remove from action map if there are no changes
        del FilesActionMap[myfile]
        write_atomic(FILES_STATUS_FILE, FilesActionMap)
    else:
        return True
    return False

def decisionlogic():
    """Main decision/summing loop. Returns False if no more actions
to perform.
    """
    global FilesActionMap
    global FilesHashMap
    global FilesSyncQueue
    global logger

    # reread fresh status on every run
    FilesActionMap = read_atomic(FILES_STATUS_FILE)

    # ignore if no actions pending
    if len(FilesActionMap.keys()) == 0:
        return False

    # random choice to avoid checksumming the same file over and over if
    # it changes often
    myfile = random.choice(FilesActionMap.keys())
    monitor_action, monitor_timestamp = FilesActionMap[myfile]

    # by default don't resync nor remote remove files
    sync_action = None
    myperm = None

    # file is freshly created or changed
    if monitor_action == 'changed' or monitor_action == 'created' or \
            monitor_action == 'attrib':
        # calculate checksum
        try:
            mysha1sum = sha1sum(myfile)
        except (IOError, OSError):
            logger.info('Could not checksum file %s. Ignoring.' % myfile)
            check_updated(None, monitor_timestamp, myfile)
            return True

        # get permissions
        try:
            myperm = oct(stat.S_IMODE(os.stat(myfile)[stat.ST_MODE]))
        except (IOError, OSError):
            logger.info('Could not get permissions for file %s. Ignoring.'
                    % myfile)
            check_updated(None, monitor_timestamp, myfile)
            return True

        # already known file
        if myfile in FilesHashMap:
            mysha1sumold, mypermold = FilesHashMap[myfile]
            # if checksum is different, resync is mandatory
            if mysha1sumold != mysha1sum:
                sync_action = 'sync'
            # else if just mode changed, change remote mode
            elif myperm != mypermold:
                sync_action = 'change_perm'
        # first time seen file (no checksum and no mode)
        else:
            sync_action = 'sync'
        FilesHashMap[myfile] = mysha1sum, myperm

    # deleted file
    elif monitor_action == 'deleted':
        if myfile in FilesHashMap:
            del FilesHashMap[myfile]
        sync_action = 'remove'

    # created directory
    elif monitor_action == 'created_dir':
        try:
            myperm = oct(stat.S_IMODE(os.stat(myfile)[stat.ST_MODE]))
        except (IOError, OSError):
            logger.info('Could not get permissions for directory %s. '
                    'Ignoring.' % myfile)
            check_updated(None, monitor_timestamp, myfile)
            return True
        sync_action = 'make_dir'

    # deleted directory 
    elif monitor_action == 'deleted_dir':
        sync_action = 'remove_dir'

    # permissions change for directory
    elif monitor_action == 'attrib_dir':
        # get permissions
        try:
            myperm = oct(stat.S_IMODE(os.stat(myfile)[stat.ST_MODE]))
        except (IOError, OSError):
            logger.info('Could not get permissions for directory %s. '
                    'Ignoring.' % myfile)
            check_updated(None, monitor_timestamp, myfile)
            return True
        sync_action = 'change_perm'

    # write hash file..
    write_atomic(FILES_HASH_FILE, FilesHashMap)
    logger.debug('Hash file status: %s.' % FilesHashMap)

    # check if file/directory has been updated in the meantime
    check_updated(sync_action, monitor_timestamp, myfile)

    # resync or remove remote files
    logger.debug('Pending action %s for file %s.' % (sync_action, myfile))
    if sync_action:
        FilesSyncQueue = read_atomic(FILES_SYNC_FILE)
        FilesSyncQueue.append((myfile, sync_action, myperm))
        write_atomic(FILES_SYNC_FILE, FilesSyncQueue)
        logger.debug('Pending sync queue: %s.' % FilesSyncQueue)

    return True

def main(argv):
    global FilesActionMap
    global FilesHashMap
    global FilesSyncQueue
    global logger
    global foreground

    # parse argv
    parse_argv(argv, globals())

    # daemonize
    daemonize(SUMMER_PID, foreground)

    # initialize logging
    logger = setup_logging(argv[0], CONSOLE_LOG_LEVEL, FILE_LOG_LEVEL,
            LOG_FORMAT, SUMMER_LOG, DATE_FORMAT)

    # sanity check
    if not os.path.isdir(WATCH_DIR):
        logger.critical('Watched directory %s does not exist. '
                'Bailing out.' % WATCH_DIR)
        sys.exit(1)

    # if FilesActionMap is nonexistant or damaged, truncate it
    try:
        FilesActionMap = read_atomic(FILES_STATUS_FILE)
    except (IOError, AttributeError, EOFError):
        logger.warn('Unusable action map status file %s. Recreating.' %
                FILES_STATUS_FILE)
        pass
    write_atomic(FILES_STATUS_FILE, FilesActionMap)

    # if FilesHashMap is nonexistant or damaged, truncate it
    try:
        FilesHashMap = read_atomic(FILES_HASH_FILE)
    except (IOError, AttributeError, EOFError):
        logger.warn('Unusable hash map file %s. Recreating.' %
                FILES_HASH_FILE)
        pass
    write_atomic(FILES_HASH_FILE, FilesHashMap)

    # if FilesSyncQueue is nonexistant or damaged, truncate it
    try:
        FilesSyncQueue = read_atomic(FILES_SYNC_FILE)
    except (IOError, AttributeError, EOFError):
        logger.warn('Unusable sync queue file %s. Recreating.' %
                FILES_SYNC_FILE)
        pass
    write_atomic(FILES_SYNC_FILE, FilesSyncQueue)

    # clear non-existant files from checksum map, most probably due to
    # changes when monitor was inactive
    for path in FilesHashMap.keys():
        if not os.path.exists(path):
            logger.warn('File %s is in hash map, but not on disk. '
                    'Deleting from map and trying to delete remotely.' %
                    path)
            # remove from hash file
            FilesHashMap = read_atomic(FILES_HASH_FILE)
            del FilesHashMap[path]
            write_atomic(FILES_HASH_FILE, FilesHashMap)
            # enqueue to remove remotely
            FilesSyncQueue = read_atomic(FILES_SYNC_FILE)
            FilesSyncQueue.append((path, 'remove', 0))
            write_atomic(FILES_SYNC_FILE, FilesSyncQueue)

    # start main loop
    logger.debug('Checksumming service starting... Entering wait loop.')
    while True:
        while decisionlogic():
            pass
        time.sleep(SLEEP_TIME)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
