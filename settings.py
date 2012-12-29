#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""System-wide settings for BlackMesa Disaster Recovery project
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

__version__ = '$Id: settings.py,v de859cceb463 2010/10/28 09:10:17 dinko $'


import pyinotify
import logging


# directory to replicate
WATCH_DIR = '/dare/VMwareDataRecovery'

# remote directory (aka replica directory)
REMOTE_DIR = '/dare/VMwareDataRecovery'

# internal status files -- file modification logs, sha1 sums and
# permissions and finally remote sync queue
FILES_STATUS_FILE = '/opt/BlackMesa-DR/BlackMesa-DR.status'
FILES_HASH_FILE = '/opt/BlackMesa-DR/BlackMesa-DR.hash'
FILES_SYNC_FILE = '/opt/BlackMesa-DR/BlackMesa-DR.sync'

# logfiles for all three components
MONITOR_LOG = '/opt/BlackMesa-DR/BlackMesa-DR-monitor.log'
SUMMER_LOG = '/opt/BlackMesa-DR/BlackMesa-DR-summer.log'
SYNCER_LOG = '/opt/BlackMesa-DR/BlackMesa-DR-syncer.log'

# pid files for all three components
MONITOR_PID = '/opt/BlackMesa-DR/BlackMesa-DR-monitor.pid'
SUMMER_PID = '/opt/BlackMesa-DR/BlackMesa-DR-summer.pid'
SYNCER_PID = '/opt/BlackMesa-DR/BlackMesa-DR-syncer.pid'

# console log level for all three services (by default disabled)
CONSOLE_LOG_LEVEL = None

# file log level for all three services
FILE_LOG_LEVEL = logging.WARNING

# default log format
LOG_FORMAT = '[%(asctime)s] [%(levelname)s] %(message)s'

# default date format (check strftime() documentation)
DATE_FORMAT = '%a %b %d %H:%M:%S %Z %Y'

# polling time for summer and syncer
SLEEP_TIME = 5

# remote server timeout sleep time
TIMEOUT_SLEEP_TIME = 300

# remote/local commands syntax (usually not required to change)
SYNC_COMMAND = 'rsync --timeout=600 --delete-after --password-file=/opt/BlackMesa-DR/password-file -a %s dare@10.4.224.41::dare' + REMOTE_DIR + '/%s'
REMOVE_COMMAND = 'ssh root@10.4.224.41 rm -f ' + REMOTE_DIR + '/%s'
REMOVE_DIR_COMMAND = 'ssh root@10.4.224.41 rm -rf ' + REMOTE_DIR + '/%s'
MAKE_DIR_COMMAND = 'ssh root@10.4.224.41 mkdir -m %s -p ' + REMOTE_DIR + '/%s'
PRE_COMMAND = 'ssh root@10.4.224.41 mkdir -p ' + REMOTE_DIR + '/%s'
CHMOD_COMMAND = 'ssh root@10.4.224.41 chmod %s ' + REMOTE_DIR + '/%s'
