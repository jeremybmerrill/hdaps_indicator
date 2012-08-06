#!/usr/bin/env python
# -*- coding: <encoding-name> -*-
#
# Copyright 2009-2012 Canonical Ltd.
#
# Authors: Neil Jagdish Patel <neil.patel@canonical.com>
#          Jono Bacon <jono@ubuntu.com>
#          David Planella <david.planella@ubuntu.com>
#          Jeremy B. Merrill <jeremy@jeremybmerrill.com>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the
# Free Software Foundation; and/or
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR
# PURPOSE. See the applicable version of the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public
# License version 3 and version 2.1 along with this program.  If not, see
# <http://www.gnu.org/licenses/>
#

import os
import platform
import sys

import gtk

import pygtk
pygtk.require("2.0")

import pynotify

import gobject
import appindicator


try:
    from pyinotify import WatchManager, ThreadedNotifier, IN_MODIFY
    pyinotify = True
except ImportError:
    pyinotify = None


def _(s): #TODO: implement. :)
  return s

hdaps_short_description = _("%s protected from shocks")
no_hdaps_short_description = _("%s not protected from shocks")

sysfs_dir = "/sys/block"

def compare_linux_version(wanted_version):
    version = map(int, platform.release().split("-")[0].split("."))
    major_version_greater = version[0] > wanted_version[0] 
    minor_version_greater = version[0] >= wanted_version[0] and version[1] > wanted_version[1]
    bugfix_version_greater = version[0] >= wanted_version[0] and version[1] >= wanted_version[1] and version[2] >= wanted_version[2]
    return major_version_greater or minor_version_greater or bugfix_version_greater

version_at_least_2_6_27 = compare_linux_version([2, 6, 27])

if version_at_least_2_6_27:
    protect_file = "device/unload_heads"
else:
    method_file = "queue/protect_method"
    protect_file = "queue/protect"

POLLING_FREQUENCY = 500 #milliseconds

class ThinkHDAPSApplet:
    """Applet that shows the status of HDAPS.

       This class partly copyright (C) 2008 - 2010  onox <denkpadje@gmail.com>, from AWN-extras
    """

    __hdaps_device = None
    __was_paused = False
    __error_occurred = False
    __show_notifications = True

    def check_status_cb(self):
        """Check the status the hard disk monitored by HDAPS and change
        the applet's icon if necessary,

        """
        try:
            paused = bool(int(open(self.__status_file).readline()))

            # Change icon if status has changed
            if paused != self.__was_paused or self.__error_occurred:
              if paused:
                self.ind.set_status(appindicator.STATUS_ATTENTION)
                print "trying: paused"
                if __show_notifications:
                    pynotify.init("hard-drive-paused")
                    imageURI = 'file://' + os.path.abspath(os.path.curdir) + '/hard-drive-paused.svg'
                    if (self.__n != None):
                        self.__n.close()
                    self.__n = pynotify.Notification("HDAPS", "Hard-disk drive was paused.", imageURI)
                    self.__n.set_urgency(pynotify.URGENCY_CRITICAL);
                    self.__n.show()
                    self.__n.set_timeout(1)

              else:
                self.ind.set_status(appindicator.STATUS_ACTIVE)
                print "trying: notpaused"
                if __show_notifications:
                    pynotify.init("hard-drive-normal")
                    imageURI = 'file://' + os.path.abspath(os.path.curdir) + '/hard-drive-normal.svg'
                    if (self.__n != None):
                        self.__n.close()
                    self.__n = pynotify.Notification("HDAPS", "Hard-disk drive was resumed.", imageURI)
                    self.__n.set_urgency(pynotify.URGENCY_CRITICAL);
                    self.__n.show()
                    self.__n.set_timeout(1)

            if self.__error_occurred:
                self.__error_occurred = False
                #TODO: self.applet.tooltip.set(hdaps_short_description % self.__hdaps_device)
                #Create a dummy element in the menu for status

            self.__was_paused = paused
            return True
        except IOError:
            if not self.__error_occurred:
                self.__error_occurred = True

                self.ind.set_status(appindicator.STATUS_ATTENTION)
                #TODO: self.applet.tooltip.set(no_hdaps_short_description % self.__hdaps_device)

    def toggleNotifications(self, widget):
        if widget.active:
            self.__show_notifications == True
        else:
            self.__show_notifications == False

    def __init__(self):
        self.ind = appindicator.Indicator("new-hdaps-indicator",
                                           "hard-drive-normal",
                                           appindicator.CATEGORY_HARDWARE)
        self.ind.set_status(appindicator.STATUS_ACTIVE)
        self.ind.set_icon("hard-drive-normal")
        self.ind.set_attention_icon("hard-drive-paused") #TODO

        self.menu_setup()
        self.ind.set_menu(self.menu)
        #######

        if version_at_least_2_6_27:
            def can_unload(disk):
                file = os.path.join(sysfs_dir, disk, protect_file)
                if not os.path.isfile(file):
                    return False
                try:
                    open(file).read()
                    return True
                except IOError:
                    return False
        else:
            def can_unload(disk):
                file = os.path.join(sysfs_dir, disk, method_file)
                return os.path.isfile(file) and "[unload]" in open(file).read()
        disks = [disk for disk in os.listdir(sysfs_dir) if can_unload(disk)]

        if len(disks) > 0:
          self.__hdaps_device = disks[0]

        if self.__hdaps_device is not None:
            self.ind.set_status(appindicator.STATUS_ACTIVE)

            self.__status_file = os.path.join(sysfs_dir, self.__hdaps_device, protect_file)

            """TODO:
            applet.tooltip.set(hdaps_short_description % self.__hdaps_device)

            if not self.setup_inotify():
                applet.timing.register(self.check_status_cb, check_status_interval)
            """
        else:
            self.set_error_icon()
            """TODO: 
            applet.tooltip.set(_("No hard disk found"))
            """

    def menu_setup(self):
        self.menu = gtk.Menu()
        self.notificationsItem = gtk.CheckMenuItem("Show Notifications")
        self.notificationsItem.set_active(True)
        self.notificationsItem.connect("activate", self.toggleNotifications)
        self.menu.append(self.notificationsItem)
        self.quit_item = gtk.MenuItem("Quit")
        self.quit_item.connect("activate", self.quit) 
        self.quit_item.show()
        self.menu.append(self.quit_item)

    def quit(self, widget):
        sys.exit(0)

    def main(self):
        self.check_status_cb()
        gtk.timeout_add(POLLING_FREQUENCY, self.check_status_cb)
        gtk.main()

    def setup_inotify(self):
        if pyinotify is None:
            return False

        watch_manager = WatchManager()
        result = watch_manager.add_watch(self.__status_file, IN_MODIFY)[self.__status_file] > 0

        if result:
            global notifier
            def notify_cb(event):
                glib.idle_add(self.check_status_cb)
            notifier = ThreadedNotifier(watch_manager, notify_cb)
            notifier.start()
        return result

    def set_error_icon(self):
        #TODO: inotify, maybe?
        raise Exception


if __name__ == "__main__":
  indicator = ThinkHDAPSApplet()
  indicator.main()

