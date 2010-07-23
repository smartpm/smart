#
# Copyright (c) 2005 Canonical
#
# Written by Gustavo Niemeyer <gustavo@niemeyer.net>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from smart import *
import os

def detectRPMSystem():
    dir = os.path.join(sysconf.get("rpm-root", "/"),
                       sysconf.get("rpm-dbpath", "var/lib/rpm"))
    file = os.path.join(dir, "Packages")
    if os.path.exists(file):
        for alias in sysconf.keys("channels"):
            if sysconf.get(("channels", alias, "type")) == "rpm-sys":
                break
        else:
            sysconf.set("channels.rpm-sys", {
                            "type": "rpm-sys",
                            "name": "RPM System"
                        })

def detectDEBSystem():
    dir = os.path.join(sysconf.get("deb-root", "/"),
                       sysconf.get("deb-admindir", "var/lib/dpkg"))
    file = os.path.join(dir, "status")
    if os.path.exists(file):
        for alias in sysconf.keys("channels"):
            if sysconf.get(("channels", alias, "type")) == "deb-sys":
                break
        else:
            sysconf.set("channels.deb-sys", {
                            "type": "deb-sys",
                            "name": "DEB System"
                        })

def detectSLACKSystem():
    dir = os.path.join(sysconf.get("slack-root", "/"),
                       sysconf.get("slack-packages-dir",
                                   "var/log/packages"))
    if os.path.isdir(dir):
        for alias in sysconf.keys("channels"):
            if sysconf.get(("channels", alias, "type")) == "slack-sys":
                break
        else:
            sysconf.set("channels.slack-sys", {
                            "type": "slack-sys",
                            "name": "Slackware System"
                        })

def detectARCHSystem():
    dir = os.path.join(sysconf.get("arch-root", "/"),
                       sysconf.get("arch-packages-dir",
                                   "var/lib/pacman"))
    if os.path.isdir(dir):
        for alias in sysconf.keys("channels"):
            if sysconf.get(("channels", alias, "type")) == "arch-sys":
                break
        else:
            sysconf.set("channels.arch-sys", {
                            "type": "arch-sys",
                            "name": "Archlinux System"
                        })

if not sysconf.getReadOnly():
    detect_sys_channels = sysconf.get("detect-sys-channels", True)
    if detect_sys_channels:
        if detect_sys_channels == True or "rpm" in str(detect_sys_channels):
            detectRPMSystem()
        if detect_sys_channels == True or "deb" in str(detect_sys_channels):
            detectDEBSystem()
        if detect_sys_channels == True or "slack" in str(detect_sys_channels):
            detectSLACKSystem()
        if detect_sys_channels == True or "arch" in str(detect_sys_channels):
            detectARCHSystem()
