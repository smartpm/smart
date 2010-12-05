#
# Copyright (c) 2007 Red Hat
#
# Written by Mauricio Teixeira <mteixeira@webset.net>
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
import ConfigParser
import re

# be compatible with 2.3
import sys
if sys.version_info < (2, 4):
    from sets import Set as set

from smart.channel import *
from smart import *

YUM_REPOS_DIR = "/etc/yum.repos.d/"

def _getbasearch():
    """
    Get system "base" architecture.
    """
    try:
        import rpmUtils.arch # from yum
        return rpmUtils.arch.getBaseArch()
    except ImportError:
        return None

def _getreleasever():
    """
    Get system release and version.
    """
    try:
        import rpm
        import rpmUtils.transaction
    except ImportError:
        return None

    rpmroot = sysconf.get("rpm-root", "/")
    ts = rpmUtils.transaction.initReadOnlyTransaction(root=rpmroot)
    ts.pushVSFlags(~(rpm._RPMVSF_NOSIGNATURES|rpm._RPMVSF_NODIGESTS))
    releasever = None
    # HACK: we're hard-coding the most used distros, will add more if needed
    idx = ts.dbMatch('provides', 'fedora-release')
    if idx.count() == 0:
        idx = ts.dbMatch('provides', 'redhat-release')
    if idx.count() != 0:
        hdr = idx.next()
        releasever = str(hdr['version'])
        del hdr
    del idx
    del ts
    return releasever

BASEARCH = _getbasearch()
RELEASEVER = _getreleasever()

def _replaceStrings(txt):
    """
    Replace some predefined strings that may appear in the repo file.
    """
    retxt = re.sub("\$basearch", "%s" % BASEARCH, txt)
    retxt = re.sub("\$releasever", "%s" % RELEASEVER, retxt)
    return retxt

def _findBaseUrl(mirrorlist, repo):
    """
    Fetches the first suggested mirror from the mirrorlist and use as baseurl.
    """
    import urllib
    list = urllib.urlopen(mirrorlist)
    baseurl = None
    while 1:
        line = list.readline()
        if line.startswith("#"):
            continue
        elif (line.startswith("http:") or line.startswith("https:") or
            line.startswith("ftp:") or line.startswith("file:")):
            baseurl = line
            break
        elif not line:
            break
    return baseurl

def _searchComments(repofile, repo):
    """
    Hack to find the commented out baseurl line if mirrorlist is feeling sad.
    """
    section = None
    baseurl = None
    file = open(repofile)
    while 1:
        line = file.readline()
        if not line:
            break
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[]")
            continue
        elif section == repo and line.startswith("#baseurl="):
            baseurl = _replaceStrings(line[9:])
            break
    file.close()
    return baseurl

def _loadRepoFile(filename):
    """
    Loads each repository file information.
    """

    file = open(filename)
 
    # The computed aliases we have seen in the given file
    seen = set()

    repofile = ConfigParser.ConfigParser()
    repofile.read(filename)

    for repo in repofile.sections():
        # Iterate through each repo found in file
        alias = "yumsync-%s" % repo
        name = _replaceStrings(repofile.get(repo, 'name'))
        baseurl = None
        mirrorlist = None

        # Some repos have baseurl, some have mirrorlist
        if repofile.has_option(repo, 'baseurl'):
            baseurl = _replaceStrings(repofile.get(repo, 'baseurl'))
            if baseurl.find("\n") >= 0: baseurl = baseurl.splitlines()[1]
            if baseurl == "file:///media/cdrom/":  baseurl = "localmedia://"
            if baseurl == "file:///media/cdrecorder/": baseurl = "localmedia://"
        else:
            # baseurl is required for rpm-md channels
            baseurl = _searchComments(filename, repo)
        if repofile.has_option(repo, 'mirrorlist'):
            mirrorlist = _replaceStrings(repofile.get(repo, 'mirrorlist'))
            if not baseurl:
                baseurl = _findBaseUrl(mirrorlist, repo)
        if baseurl is None and mirrorlist is None:
            iface.warning(_("Yum channel %s does not contain baseurl or " \
                            "mirrorlist addresses. Not syncing.") % repo)
            return seen

        if repofile.has_option(repo, 'enabled'):
            enabled = not repofile.getboolean(repo, 'enabled')
        else:
            enabled = False

        data = {"type": "rpm-md",
                "name": name,
                "baseurl": baseurl,
                "disabled": enabled}
        if mirrorlist:
            data["mirrorlist"] = mirrorlist
        seen.add(alias)
 
        try:
            createChannel(alias, data)
        except Error, e:
            iface.error(_("While using %s: %s") % (filename, e))
        else:
            # Store it persistently.
            sysconf.set(("channels", alias), data)

    return seen


def syncYumRepos(reposdir, force=None):
    """
    Sync Smart channels based on Yum repositories.
    """

    seen = set()

    if os.path.isdir(reposdir):
        for entry in os.listdir(reposdir):
            if entry.endswith(".repo"):
                filepath = os.path.join(reposdir, entry)
                if os.path.isfile(filepath):
                    seen.update(_loadRepoFile(filepath))

    # Delete the entries which were not seen in current files.
    channels = sysconf.get("channels")
    for alias in sysconf.keys("channels"):
        if alias.startswith("yumsync-") and alias not in seen:
            sysconf.remove(("channels", alias))


if not sysconf.getReadOnly():
    if sysconf.get("sync-yum-repos",False):
        syncYumRepos(sysconf.get("yum-repos-dir", YUM_REPOS_DIR))

# vim:ts=4:sw=4:et
