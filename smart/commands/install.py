#
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
from smart.transaction import Transaction, PolicyInstall, sortUpgrades
from smart.transaction import INSTALL, REINSTALL
from smart.matcher import MasterMatcher
from smart.option import OptionParser
from smart import *
import string
import re
import os

USAGE="smart install [options] package ..."

DESCRIPTION="""
This command will install one or more packages in the
system. If a new version of an already installed package
is available, it will be selected for installation.
"""

EXAMPLES="""
smart install pkgname
smart install '*kgna*'
smart install pkgname-1.0
smart install pkgname-1.0-1
smart install pkgname1 pkgname2
smart install ./somepackage.file
smart install http://some.url/some/path/somepackage.file
"""

def parse_options(argv):
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION,
                          examples=EXAMPLES)
    parser.add_option("--stepped", action="store_true",
                      help="split operation in steps")
    parser.add_option("--urls", action="store_true",
                      help="dump needed urls and don't commit operation")
    parser.add_option("--download", action="store_true",
                      help="download packages and don't commit operation")
    parser.add_option("--force", action="store_true",
                      help="do not ask for confirmation")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(ctrl, opts):

    urls = []
    for arg in opts.args[:]:
        if '/' in arg:
            if os.path.isfile(arg):
                ctrl.addFileChannel(arg)
                opts.args.remove(arg)
            elif ":/" in arg:
                urls.append(arg)
    if urls:
        succ, fail = ctrl.downloadURLs(urls, "packages", targetdir=os.getcwd())
        if fail:
            raise Error, "Failed to download packages:\n" + \
                         "\n".join(["    %s: %s" % (url, fail[url])
                                    for url in fail])
        for url, file in succ.items():
            ctrl.addFileChannel(file)
            opts.args.remove(url)
    ctrl.updateCache()
    cache = ctrl.getCache()
    trans = Transaction(cache, PolicyInstall)
    for channel in ctrl.getFileChannels():
        for pkg in channel.getInfo("loader").getPackages():
            if pkg.installed:
                raise Error, "%s is already installed" % pkg
            trans.enqueue(pkg, INSTALL)
    for arg in opts.args:
        matcher = MasterMatcher(arg)
        pkgs = matcher.filter(cache.getPackages())
        if not pkgs:
            raise Error, "'%s' matches no packages" % arg
        if len(pkgs) > 1:
            sortUpgrades(pkgs)
        names = {}
        found = False
        for pkg in pkgs:
            names.setdefault(pkg.name, []).append(pkg)
        for name in names:
            pkg = names[name][0]
            if pkg.installed:
                iface.warning("%s is already installed" % pkg)
            else:
                found = True
                trans.enqueue(pkg, INSTALL)
        if not found:
            raise Error, "No uninstalled packages matched '%s'" % arg
    iface.showStatus("Computing transaction...")
    trans.run()
    iface.hideStatus()
    if trans:
        confirm = not opts.force
        if opts.urls:
            ctrl.dumpTransactionURLs(trans)
        elif opts.download:
            ctrl.downloadTransaction(trans, confirm=confirm)
        elif opts.stepped:
            ctrl.commitTransactionStepped(trans, confirm=confirm)
        else:
            ctrl.commitTransaction(trans, confirm=confirm)

# vim:ts=4:sw=4:et
