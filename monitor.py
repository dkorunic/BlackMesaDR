#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""File Monitor part of BlackMesa Disaster Recovery project
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

__version__ = '$Id: monitor.py,v de859cceb463 2010/10/28 09:10:17 dinko $'


import time
import os
import sys
import pyinotify

from common import write_atomic, read_atomic, setup_logging, parse_argv, \
    daemonize
from settings import *


InotifyMask = {pyinotify.IN_CREATE: 'created',
        pyinotify.IN_DELETE: 'deleted',
        pyinotify.IN_MODIFY: 'changed',
        pyinotify.IN_CLOSE_WRITE: 'changed',
        pyinotify.IN_ATTRIB: 'attrib',
        pyinotify.IN_MOVED_TO: 'created',
        pyinotify.IN_MOVED_FROM: 'deleted',
        pyinotify.IN_CREATE|pyinotify.IN_ISDIR: 'created_dir',
        pyinotify.IN_DELETE|pyinotify.IN_ISDIR: 'deleted_dir',
        pyinotify.IN_ATTRIB|pyinotify.IN_ISDIR: 'attrib_dir',
        pyinotify.IN_MOVED_TO|pyinotify.IN_ISDIR: 'created_dir',
        pyinotify.IN_MOVED_FROM|pyinotify.IN_ISDIR: 'deleted_dir'}
FilesActionMap = {}
logger = None
foreground = False


class ProcessEventHandler(pyinotify.ProcessEvent):
    """Main inotify process event handler for Pyinotify.
    """
    def process_IN_IGNORED(self, event):
        pass

    def process_IN_UNMOUNT(self, event):
        logger.critical('Detected filesystem umount. Bailing out.')
        sys.exit(1)

    def process_IN_Q_OVERFLOW(self, event):
        logger.critical('Detected inotify queue overflow. Bailing out.')
        sys.exit(1)

    def process_default(self, event):
        global FilesActionMap
        global logger

        # sanity check
        if event.mask not in InotifyMask:
            logger.warn('Got unexpected/unhandled event %d. Ignoring.' %
                    event.mask)
            return

        # map and process individual actions
        FilesActionMap = read_atomic(FILES_STATUS_FILE)
        action = InotifyMask[event.mask]
        FilesActionMap[event.pathname] = (action, time.time())
        write_atomic(FILES_STATUS_FILE, FilesActionMap)
        logger.debug('Pending monitor actions %s.' % FilesActionMap)

def main(argv):
    global FilesActionMap
    global logger
    global foreground

    # parse argv
    parse_argv(argv, globals())

    # daemonize
    daemonize(MONITOR_PID, foreground)

    # initialize logging
    logger = setup_logging(argv[0], CONSOLE_LOG_LEVEL, FILE_LOG_LEVEL,
            LOG_FORMAT, MONITOR_LOG, DATE_FORMAT)

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

    # initial recursive walk (initial events)
    for root, dirs, files in os.walk(WATCH_DIR):
        for name in files:
            path = os.path.join(root, name)
            FilesActionMap[path] = ('created', time.time())
        for name in dirs:
            path = os.path.join(root, name)
            FilesActionMap[path] = ('created_dir', time.time())
    write_atomic(FILES_STATUS_FILE, FilesActionMap)
    logger.debug('Initial events %s. Commiting.' % FilesActionMap)

    # start inotify monitor
    watch_manager = pyinotify.WatchManager()
    handler = ProcessEventHandler()
    notifier = pyinotify.Notifier(watch_manager, default_proc_fun=handler,
            read_freq=SLEEP_TIME)

    # try coalescing events if possible
    try:
        notifier.coalesce_events()
        logger.debug('Successfuly enabled events coalescing. Good.')
    except AttributeError:
        pass

    # catch only create/delete/modify/attrib events; don't monitor
    # IN_MODIFY, instead use IN_CLOSE_WRITE when file has been written to
    # and finally closed; and monitor IN_MOVED_TO when using temporary
    # files for atomicity as well as IN_MOVED_FROM when file is moved from
    # watched path
    event_mask = pyinotify.IN_CREATE|pyinotify.IN_DELETE|\
            pyinotify.IN_CLOSE_WRITE|pyinotify.IN_ATTRIB|\
            pyinotify.IN_MOVED_TO|pyinotify.IN_MOVED_FROM|\
            pyinotify.IN_ISDIR|pyinotify.IN_UNMOUNT|\
            pyinotify.IN_Q_OVERFLOW
    watch_manager.add_watch(WATCH_DIR, event_mask, rec=True,
            auto_add=True)

    # enter loop
    logger.debug('Inotify handler starting... Entering notify loop.')
    notifier.loop()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
