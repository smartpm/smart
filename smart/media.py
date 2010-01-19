#
# Copyright (c) 2005 Canonical
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
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
from smart.util.filetools import compareFiles
from smart import *
import commands
import stat
import os

try:
    import dbus
except ImportError:
    dbus = None

class MediaSet(object):

    def __init__(self):
        self._medias = []
        self._processcache = {}
        self.discover()

    def discover(self):
        self.restoreState()
        del self._medias[:]
        self._processcache.clear()
        mountpoints = {}
        for lst in hooks.call("discover-medias"):
            for media in lst:
                mountpoint = media.getMountPoint()
                if mountpoint not in mountpoints:
                    mountpoints[mountpoint] = media
                    self._medias.append(media)
        self._medias.sort()

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

    def findDevice(self, path, subpath=False):
        path = os.path.normpath(path)
        for media in self._medias:
            device = media.getDevice()
            if device and \
               (device == path or subpath and path.startswith(device+"/")):
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

    def processFilePath(self, filepath):
        dirname = os.path.dirname(filepath)
        if dirname in self._processcache:
            media = self._processcache.get(dirname)
            if media:
                filepath = media.convertDevicePath(filepath)
        else:
            media = self.findMountPoint(filepath, subpath=True)
            if not media:
                media = self.findDevice(filepath, subpath=True)
            if media:
                media.mount()
                filepath = media.convertDevicePath(filepath)
                self._processcache[dirname] = media
            else:
                isfile = os.path.isfile
                paths = []
                path = dirname
                while path != "/":
                    paths.append(path)
                    if isfile(path):
                        for media in hooks.call("discover-device-media", path):
                            if media:
                                media.mount()
                                self._medias.append(media)
                                filepath = media.convertDevicePath(filepath)
                                self._processcache.update(
                                        dict.fromkeys(paths, media))
                                break
                        if media:
                            break
                    path = os.path.dirname(path)
                else:
                    self._processcache.update(dict.fromkeys(paths, None))
        return filepath, media

    def getDefault(self):
        default = sysconf.get("default-localmedia")
        if default:
            return self.findMountPoint(default, subpath=True)
        return None

    def __iter__(self):
        return iter(self._medias)

class Media(object):

    order = 1000

    def __init__(self, mountpoint, device=None,
                 type=None, options=None, removable=False):
        self._mountpoint = os.path.normpath(mountpoint)
        self._device = device
        self._type = type
        self._options = options
        self._removable = removable
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

    def getType(self):
        return self._type

    def getOptions(self):
        return self._options

    def isRemovable(self):
        return self._removable

    def wasMounted(self):
        return self._wasmounted

    def isMounted(self):
        if not os.path.isfile("/proc/mounts"):
            if self._mountpoint:
                return os.path.ismount(self._mountpoint)
            raise Error, _("/proc/mounts not found")
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
        while path and path[0] == "/":
            path = path[1:]
        return os.path.join(self._mountpoint, path)

    def joinURL(self, path):
        if path.startswith("localmedia:/"):
            path = path[12:]
        while path and path[0] == "/":
            path = path[1:]
        return os.path.join("file://"+self._mountpoint, path)

    def convertDevicePath(self, path):
        if path.startswith(self._device):
            path = path[len(self._device):]
            while path and path[0] == "/":
                path = path[1:]
            path = os.path.join(self._mountpoint, path)
        return path

    def hasFile(self, path, comparepath=None):
        if self.isMounted():
            filepath = self.joinPath(path)
            if (os.path.isfile(filepath) and
                not comparepath or compareFiles(path, comparepath)):
                return True
        return False

    def __lt__(self, other):
        return self.order < other.order

class MountMedia(Media):

    def mount(self):
        if self.isMounted():
            return True
        if self._device:
            cmd = "mount %s %s" % (self._device, self._mountpoint)
            if self._type:
                cmd += " -t %s" % self._type
        else:
            cmd = "mount %s" % self._mountpoint
        if self._options:
            cmd += " -o %s" % self._options
        status, output = commands.getstatusoutput(cmd)
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

    order = 500

    def mount(self):
        try:
            os.listdir(self._mountpoint)
        except OSError:
            return False
        else:
            return True

class DeviceMedia(BasicMedia):

    order = 100

    def mount(self):
        if not os.path.isdir(self._mountpoint):
            os.mkdir(self._mountpoint)
        BasicMedia.mount(self)

    def umount(self):
        BasicMedia.umount(self)
        try:
            os.rmdir(self._mountpoint)
        except OSError:
            pass

def discoverFstabMedias(filename="/etc/fstab"):
    result = []
    if os.path.isfile(filename):
        for line in open(filename):

            line = line.strip()
            if not line or line[0] == "#":
                continue

            tokens = line.split()
            if len(tokens) < 3:
                continue

            device, mountpoint, type = tokens[:3]
            if device == "none":
                device = None

            if type == "supermount":
                result.append(MountMedia(mountpoint))
            elif (type in ("iso9660", "udf", "udf,iso9660") or
                device in ("/dev/cdrom", "/dev/dvd") or
                mountpoint.endswith("/cdrom") or mountpoint.endswith("/dvd")):
                result.append(BasicMedia(mountpoint, device, removable=True))
    return result

hooks.register("discover-medias", discoverFstabMedias)

def discoverAutoMountMedias(filename="/etc/auto.master"):
    result = []
    if os.access(filename, os.R_OK):
        for line in open(filename):
            line = line.strip()
            if not line or line[0] == "#":
                continue
            tokens = line.split()
            if len(tokens) < 2:
                continue # +auto.master syntax, not yet supported
            prefix, mapfile = tokens[:2]
            if os.access(mapfile, os.R_OK):
                firstline = False
                for line in open(mapfile):
                    if firstline and line.startswith("#!"):
                        firstline = False
                        break
                    line = line.strip()
                    if not line or line[0] == "#":
                        continue
                    tokens = line.split()
                    if len(tokens) == 2:
                        key, location = tokens
                        type = None
                    elif len(tokens) == 3:
                        key, type, location = tokens
                    else:
                        continue
                    if (type and "-fstype=iso9660" in type or
                        location in (":/dev/cdrom", ":/dev/dvd")):
                        mountpoint = os.path.join(prefix, key)
                        device = location[1:]
                        result.append(AutoMountMedia(mountpoint, device,
                                                     removable=True))
    return result

hooks.register("discover-medias", discoverAutoMountMedias)

def discoverHalVolumeMedias():
    result = []
    if dbus:
        import sys
        import StringIO
        olderr = sys.stderr
        sys.stderr = StringIO.StringIO()
        try:
            bus = dbus.SystemBus()
            hal_object = bus.get_object('org.freedesktop.Hal',
                                        '/org/freedesktop/Hal/Manager')
            hal_manager = dbus.Interface(hal_object, 'org.freedesktop.Hal.Manager')
            
            volume_udi_list = hal_manager.FindDeviceByCapability('volume')
            for udi in volume_udi_list:
                dev_object = bus.get_object('org.freedesktop.Hal', udi)
                volume = dbus.Interface(dev_object, 'org.freedesktop.Hal.Device')
                device = volume.GetProperty('block.device')
                fstype = volume.GetProperty('volume.fstype')
                mount_point = volume.GetProperty('volume.mount_point')
                storage_udi = volume.GetProperty('block.storage_device')
                dev_object = bus.get_object('org.freedesktop.Hal', storage_udi)
                storage = dbus.Interface(dev_object, 'org.freedesktop.Hal.Device')
                drive_type = storage.GetProperty('storage.drive_type')
                if mount_point and (fstype == "iso9660" or drive_type == "cdrom"):
                    result.append(AutoMountMedia(mount_point, device,
                                                              removable=True))
        except:
            pass
        err = sys.stderr.getvalue()
        sys.stderr = olderr
    return result

hooks.register("discover-medias", discoverHalVolumeMedias)

def discoverDeviceKitDisksMedias():
    result = []
    if dbus:
        import sys
        import StringIO
        olderr = sys.stderr
        sys.stderr = StringIO.StringIO()
        try:
            bus = dbus.SystemBus()
            dk_object = bus.get_object('org.freedesktop.DeviceKit.Disks',
                                       '/org/freedesktop/DeviceKit/Disks')
            dk_interface = dbus.Interface(dk_object, 'org.freedesktop.DeviceKit.Disks')
            for path in dk_interface.EnumerateDevices():
                dev_object = bus.get_object('org.freedesktop.DeviceKit.Disks', path)
                interface = 'org.freedesktop.DeviceKit.Disks.Device'
                volume = dbus.Interface(dev_object, 'org.freedesktop.DBus.Properties')
                device = str(volume.Get(interface, 'DeviceFile'))
                fstype = str(volume.Get(interface, 'IdType'))
                mount_paths = volume.Get(interface, 'DeviceMountPaths')
                optical_disc = bool(volume.Get(interface, 'DeviceIsOpticalDisc'))
                is_removable = bool(volume.Get(interface, 'DeviceIsRemovable'))
                if mount_paths and (fstype == "iso9660" or optical_disc):
                    mount_point = unicode(mount_paths.pop())
                    result.append(AutoMountMedia(mount_point, device,
                                                              removable=is_removable))
        except:
            pass
        err = sys.stderr.getvalue()
        sys.stderr = olderr
    return result

hooks.register("discover-medias", discoverDeviceKitDisksMedias)

def discoverDeviceMedia(path):
    mntdir = os.path.join(sysconf.get("data-dir"), "mnt")
    if not os.path.isdir(mntdir):
        try:
            os.makedirs(mntdir)
        except OSError:
            return None
    elif not os.access(mntdir, os.W_OK):
        return None
    dirname, basename = os.path.split(path)
    suffix = 0
    mountpoint = os.path.join(mntdir, basename)
    while os.path.ismount(mountpoint):
        suffix += 1
        mountpoint = os.path.join(mntdir, basename+(".%d" % suffix))
    if suffix:
        basename += ".%d" % suffix
    st = os.stat(path)
    if stat.S_ISBLK(st.st_mode):
        options = None
    else:
        options = "loop"
    return DeviceMedia(mountpoint, path, options=options)

hooks.register("discover-device-media", discoverDeviceMedia)
