#!/bin/sh
# crude BlackMesa Disaster Recovery cleaner
# $Id: clean.sh,v 3a965d4bb696 2010/10/22 23:37:59 dinko $

rm -f BlackMesa-DR.hash \
    BlackMesa-DR.status \
    BlackMesa-DR.sync \
    BlackMesa-DR-syncer.log \
    BlackMesa-DR.hash.lock \
    BlackMesa-DR-summer.log \
    BlackMesa-DR-summer.pid \
    BlackMesa-DR-syncer.pid \
    BlackMesa-DR.sync.lock \
    common.pyc \
    BlackMesa-DR-monitor.log \
    BlackMesa-DR-monitor.pid \
    BlackMesa-DR.status.lock
