#!/bin/sh
#
# Copyright (C) 2010  Dinko Korunic, InfoMAR
# $Id: BlackMesa-DR.init.sh,v de859cceb463 2010/10/28 09:10:17 dinko $

# Basic support for RHEL chkconfig
# chkconfig: 2345 99 01
# description: BlackMesa Disaster Recovery Synchronisation Service

# Source function library.
. /etc/init.d/functions

DAEMON="monitor.py summer.py syncer.py"
PATH=/opt/ActivePython-2.7/bin:$PATH
BlackMesaDRPATH=/opt/BlackMesa-DR

start () {
	for i in $DAEMON; do
		echo -n $"Starting $i: "
		daemon $BlackMesaDRPATH/$i
	    echo ""
	done
}

stop () {
	for i in $DAEMON; do
		echo -n $"Shutting down $i: "
		if pkill -f ".*python.*$i\$" >/dev/null 2>&1; then
            success $"$i shutdown"
        else
            failure $"$i shutdown"
        fi
	    echo ""
	done
}

restart() {
	stop
	start
}

status() {
    pids=$(pgrep -f ".*python.*$BlackMesaDRPATH.*py" | xargs echo -n)
    if [ ! -z "$pids" ]; then
        echo $"BlackMesa-DR is running with pids $pids"
        return 0
    else
        echo $"BlackMesa-DR is stopped"
        return 3
    fi
}

case $1 in
	start)
		start
        RETVAL=$?
	;;
	stop)
		stop
        RETVAL=$?
	;;
	restart)
		restart
        RETVAL=$?
	;;
	status)
		status
        RETVAL=$?
	;;
	*)
	    echo $"Usage: $prog {start|stop|restart|status}"
    	exit 1
    ;;
esac

exit $RETVAL
