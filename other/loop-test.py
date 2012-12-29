#!/usr/bin/env python
import pyinotify
wm = pyinotify.WatchManager()
notifier = pyinotify.Notifier(wm)
wm.add_watch('.', pyinotify.ALL_EVENTS, rec=True, auto_add=True)
notifier.loop()
