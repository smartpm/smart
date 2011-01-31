# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Per Øyvind Karlsen
#
# Written by Per Øyvind Karlsen <peroyvind@mandriva.org>
# and Anders F Bjorklund <afb@users.sourceforge.net>
# Parts of code based on urpmi2smart by Michael Scherer <misc@mandriva.org> 
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
import posixpath
import os
import re

# be compatible with 2.3
import sys
if sys.version_info < (2, 4):
    from sets import Set as set

from smart.channel import *
from smart import *
from smart.fetcher import Fetcher

URPMI_CONFIG_DIR = "/etc/urpmi/"
URPMI_CONFIG = URPMI_CONFIG_DIR + "urpmi.cfg"
URPMI_MEDIA_DIR = "/var/lib/urpmi/"
URPMI_MIRRORS_CACHE = "/var/cache/urpmi/mirrors.cache"

# http://wiki.mandriva.com/en/Product_id
PRODUCT_ID = "/etc/product.id"
RELEASE = "/etc/release"

def getProductID():
    fp = open(sysconf.get("product-id", PRODUCT_ID))
    items = fp.readline().strip().split(",")
    fp.close()
    productid = {}
    for item in items:
        key,entry = item.split("=")
        productid[key] = entry.lower()
    return productid

def getReleaseArch():
    fp = open(sysconf.get("release", RELEASE))
    line = fp.readline().strip()
    fp.close()
    match = re.match(r".*release (\d+\.\d+).*for (\w+)", line)
    if match:
        release = match.group(1)
        arch = match.group(2)
        if line.lower().find("cooker") != -1:
            release = "cooker"
        return (release, arch)
    return ("release", "arch")

def fetch_urpmi_cfg(filename):
    fetcher = Fetcher()
    if os.path.isfile(URPMI_MIRRORS_CACHE):
        mirrorsfile = open(URPMI_MIRRORS_CACHE)
        mirrorscache = eval(mirrorsfile.read().replace('=>', ':').replace(';',''))
        mirrorsfile.close()
    else:
        mirrorscache = None

    config=[]
    in_block = False
    skip = False
    urpmi_cfg_f=open(filename)
    for line in urpmi_cfg_f.readlines():
        line = line.strip()
        if len(line) <= 0:
            continue
        if line[-1] == "}":
            in_block = False
            skip = False
        if skip:
            continue
        if line[-1] == "{":
            in_block = True
            s = line.split(" ")
            if len(s) == 1:
                skip = True
                continue
            config.append(dict())
            config[-1]["name"] = " ".join(s[0:-2]).replace("\\", "")
            if s[-2]:
                config[-1]["url"] = s[-2]
            continue
        if not in_block:
            continue
        if line.find(": ") > 0:
            (key,value) = line.strip().split(": ")
            config[-1][key.strip()] = value
            if key == "mirrorlist":
                if mirrorscache:
                    if mirrorscache.has_key(value):
                        value = mirrorscache[value]
                        # Make sure to find a mirror using a protocol that we
                        # actually handle...
                        scheme = value["chosen"].split(":")[0]
                        if fetcher.getHandler(scheme, None):
                            config[-1]["url"] = value["chosen"]
                        else:
                            config[-1]["url"] = None

                        for mirror in value["list"]:
                            scheme = mirror["url"].split(":")[0]
                            if fetcher.getHandler(scheme, None):
                                if not config[-1]["url"]:
                                    config[-1]["url"] = mirror["url"]
                                else:
                                    sysconf.add(("mirrors", config[-1]["url"]), mirror["url"], unique=True)
        else:
            config[-1][line.strip()] = True
    urpmi_cfg_f.close()
    return config

def find_urpmi_password(url):
    machine = url[url.rfind("@")+1:].split("/")[0]
    login = url[:url.rfind("@")].split("://")
    if len(login) >= 2:
        login = login[1]
        try:
            fp = open(URPMI_CONFIG_DIR + "netrc")
            line = fp.readline()
            while line:
                netrc = {}
                splitted = line.strip("\n").split(" ")
                for i in xrange(0, len(splitted), 2):
                    netrc[splitted[i]] = splitted[i+1]
                if netrc["machine"] == machine and netrc["login"] == login:
                    url = "%s:%s@%s" % (url[:url.rfind("@")], netrc["password"], url[url.rfind("@")+1:])
                    break
                line = fp.readline()

            fp.close()
        except IOError, e:
            pass

    return url

def _loadMediaList(filename):

    # The computed aliases we have seen in the given file.
    seen = set()

    urpmi_cfg = fetch_urpmi_cfg(filename)

    for media in urpmi_cfg:
        name = media["name"]
        alias = "urpmisync-%s" % name
        priority = 0
        baseurl = None
        mirrorurl = None
        
        if not media.has_key("url"): 
            continue

        def getMirrorListURL(mirrorurl):
            if mirrorurl == "$MIRRORLIST":
                productid = getProductID()
                mirrorurl = "http://api.mandriva.com/mirrors/%s.%s.%s.list" \
                          % (productid["type"], productid["version"], productid["arch"])
            elif mirrorurl.find("$RELEASE") != -1 or mirrorurl.find("$ARCH") != -1:
                (release, arch) = getReleaseArch()
                mirrorurl = mirrorurl.replace("$RELEASE", release).replace("$ARCH", arch)
            return mirrorurl

        removable = media["url"].startswith("cdrom://")
        if removable:
            baseurl = media["url"].replace("cdrom://", "localmedia://")
        else:
            baseurl = find_urpmi_password(media["url"].replace("ssh://", "scp://"))

        hdlurl = None
        directory = None
        
        if media.has_key("with_hdlist"):
            hdlurl = media["with_hdlist"]
        elif media.has_key("media_info_dir"):
            hdlurl = media["media_info_dir"] + "/synthesis.hdlist.cz"
        else:
            if media.has_key("with-dir"):
                directory = media["with-dir"]
            hdlurl = "media_info/synthesis.hdlist.cz"

        if media.has_key("mirrorlist"):
            mirrorurl = getMirrorListURL(media["mirrorlist"])

        data = {"type": "urpmi",
                "name": name,
                "baseurl": baseurl,
                "hdlurl": hdlurl,
                "disabled": media.has_key("ignore"),
                "removable": removable,
                "priority": priority}
        if directory:
            data["directory"] = directory
        if mirrorurl:
            data["mirrorurl"] = mirrorurl

        seen.add(alias)

        # See if creating a channel works.
        try:
            createChannel(alias, data)
        except Error, e:
            iface.error(_("While using %s: %s") % (file.name, e))
        else:
            # Store it persistently, without destroying existing setttings.
            channel = sysconf.get(("channels", alias))
            if channel is not None:
                channel.update(data)
            else:
                channel = data

            sysconf.set(("channels", alias), channel)

    return seen


def syncURPMIChannels(urpmicfg, mediadir=URPMI_MEDIA_DIR, force=None):
    seen = set()

    # First, the urpmi.cfg file.
    if os.path.isfile(urpmicfg):
        seen.update(_loadMediaList(urpmicfg))

    # Delete the entries which were not seen in current files.
    channels = sysconf.get("channels")
    for alias in sysconf.keys("channels"):
        if alias.startswith("urpmisync-") and alias not in seen:
            sysconf.remove(("channels", alias))


if not sysconf.getReadOnly():
    if sysconf.get("sync-urpmi-medialist",False):
        # Sync is not enabled by default
        syncURPMIChannels(sysconf.get("urpmi-config", URPMI_CONFIG))

# vim:ts=4:sw=4:et
