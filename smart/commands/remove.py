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
from smart.transaction import Transaction, PolicyRemove, REMOVE
from smart.matcher import MasterMatcher
from smart.option import OptionParser
from smart import *
import string
import re

USAGE="smart remove [options] package ..."

DESCRIPTION="""
This command will remove one or more packages which
are currently installed in the system.
"""

EXAMPLES="""
smart remove pkgname
smart remove '*kgnam*'
smart remove pkgname-1.0
smart remove pkgname-1.0-1
smart remove pkgname1 pkgname2
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

    ctrl.reloadChannels()
    cache = ctrl.getCache()
    trans = Transaction(cache, PolicyRemove)
    policy = trans.getPolicy()
    for arg in opts.args:
        found = False
        matcher = MasterMatcher(arg)
        for pkg in matcher.filter(cache.getPackages()):
            if pkg.installed:
                found = True
                trans.enqueue(pkg, REMOVE)
            else:
                policy.setLocked(pkg, True)
        if not found:
            raise Error, "'%s' matches no installed packages" % arg
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
