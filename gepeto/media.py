#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Gepeto.
#
# Gepeto is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gepeto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gepeto; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from gepeto.util.filetools import compareFiles
from gepeto import *
import commands
import os

class MediaSet(object):

    def __init__(self):
        self._medias = []
        self.discover()

    def discover(self):
        self.restoreState()
        del self._medias[:]
        mountpoints = {}
        for lst in hooks.call("Media.discover"):
            for media in lst:
                mountpoint = media.getMountPoint()
                if mountpoint not in mountpoints:
                    mountpoints[mountpoint] = media
                    self._medias.append(media)

    def resetState(self):
        for media in self._medias:
            media.resetState()

    def restoreState(self):
        for media in self._medias:
            media.restoreState()

    def mountAll(self):
        for media in self._medias:
            media.mount()

    def umountAll(self):
        for media in self._medias:
            media.umount()

    def findMountPoint(self, path, subpath=False):
        path = os.path.normpath(path)
        for media in self._medias:
            mountpoint = media.getMountPoint()
            if (mountpoint == path or
                subpath and path.startswith(mountpoint+"/")):
                return media
        return None

    def findFile(self, path, comparepath=None):
        if path.startswith("localmedia:"):
            path = path[11:]
        while path[:2] == "//":
            path = path[1:]
        for media in self._medias:
            if media.isMounted():
                filepath = media.joinPath(path)
                if (os.path.isfile(filepath) and
                    not comparepath or compareFiles(filepath, comparepath)):
                    return media
        return None

    def getDefault(self):
        default = sysconf.get("default-localmedia")
        if default:
            return self.findMountPoint(default, subpath=True)
        return None

    def __iter__(self):
        return iter(self._medias)

class Media(object):

    def __init__(self, mountpoint, device=None):
        self._mountpoint = os.path.normpath(mountpoint)
        self._device = device
        self.resetState()

    def resetState(self):
        self._wasmounted = self.isMounted()

    def restoreState(self):
        if self._wasmounted:
            self.mount()
        else:
            self.umount()

    def getMountPoint(self):
        return self._mountpoint

    def getDevice(self):
        return self._device

    def isMounted(self):
        if not os.path.isfile("/proc/mounts"):
            raise Error, "/proc/mounts not found"
        for line in open("/proc/mounts"):
            device, mountpoint, type = line.split()[:3]
            if mountpoint == self._mountpoint:
                return True
        return False

    def mount(self):
        return True

    def umount(self):
        return True

    def eject(self):
        if self._device:
            status, output = commands.getstatusoutput("eject %s" %
                                                      self._device)
            if status == 0:
                return True
        return False

    def joinPath(self, path):
        if path.startswith("localmedia:/"):
            path = path[12:]
        while path[0] == "/":
            path = path[1:]
        return os.path.join(self._mountpoint, path)

    def joinURL(self, path):
        if path.startswith("localmedia:/"):
            path = path[12:]
        while path[0] == "/":
            path = path[1:]
        return os.path.join("file://"+self._mountpoint, path)

    def hasFile(self, path, comparepath=None):
        if media.isMounted():
            filepath = self.joinPath(path)
            if (os.path.isfile(filepath) and
                not comparepath or compareFiles(path, comparepath)):
                return True
        return False

class MountMedia(Media):

    def mount(self):
        if self.isMounted():
            return True
        status, output = commands.getstatusoutput("mount %s" %
                                                  self._mountpoint)
        if status != 0:
            iface.debug(output)
            return False
        return True

class UmountMedia(Media):

    def umount(self):
        if not self.isMounted():
            return True
        status, output = commands.getstatusoutput("umount %s" % 
                                                  self._mountpoint)
        if status != 0:
            iface.debug(output)
            return False
        return True

class BasicMedia(MountMedia, UmountMedia):
    pass

class AutoMountMedia(UmountMedia):

    def mount(self):
        try:
            os.listdir(self._mountpoint)
        except OSError:
            return False
        else:
            return True

def discoverFstabMedias():
    result = []
    if os.path.isfile("/etc/fstab"):
        for line in open("/etc/fstab"):

            line = line.strip()
            if not line or line[0] == "#":
                continue

            device, mountpoint, type = line.split()[:3]
            if device == "none":
                device = None

            if type == "supermount":
                result.append(MountMedia(mountpoint))
            elif (type in ("iso9660", "udf") or
                device in ("/dev/cdrom", "/dev/dvd") or
                mountpoint.endswith("/cdrom") or mountpoint.endswith("/dvd")):
                result.append(BasicMedia(mountpoint, device))
    return result

hooks.register("Media.discover", discoverFstabMedias)

def discoverAutoMountMedias():
    result = []
    if os.path.isfile("/etc/auto.master"):
        for line in open("/etc/auto.master"):
            line = line.strip()
            if not line or line[0] == "#":
                continue
            prefix, mapfile = line.split()[:2]
            if os.path.isfile(mapfile):
                for line in open(mapfile):
                    line = line.strip()
                    if not line or line[0] == "#":
                        continue
                    key, type, location = line.split()
                    if ("-fstype=iso9660" in type or
                        location in (":/dev/cdrom", ":/dev/dvd")):
                        mountpoint = os.path.join(prefix, key)
                        device = location[1:]
                        result.append(AutoMountMedia(mountpoint, device))
    return result

hooks.register("Media.discover", discoverAutoMountMedias,
               priority=400)

