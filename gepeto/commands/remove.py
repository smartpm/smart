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
from gepeto.transaction import Transaction, PolicyRemove, REMOVE
from gepeto.matcher import MasterMatcher
from gepeto.option import OptionParser
from gepeto import *
import string
import re

USAGE="gpt remove [options] package ..."

DESCRIPTION="""
This command will remove one or more packages which
are currently installed in the system.
"""

EXAMPLES="""
gpt remove pkgname
gpt remove '*kgnam*'
gpt remove pkgname-1.0
gpt remove pkgname-1.0-1
gpt remove pkgname1 pkgname2
"""

def parse_options(argv):
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION,
                          examples=EXAMPLES)
    parser.add_option("--stepped", action="store_true",
                      help="split operation in steps")
    parser.add_option("--dump-urls", action="store_true",
                      help="dump needed urls and don't commit operation")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):
    ctrl.updateCache()
    cache = ctrl.getCache()
    trans = Transaction(cache, PolicyRemove)
    found = False
    for arg in opts.args:
        matcher = MasterMatcher(arg)
        for pkg in matcher.filter(cache.getPackages()):
            if pkg.installed:
                found = True
                trans.enqueue(pkg, REMOVE)
    if not found:
        raise Error, "No installed packages matched given arguments"
    iface.showStatus("Computing transaction...")
    trans.run()
    iface.hideStatus()
    if trans:
        if opts.dump_urls:
            ctrl.dumpURLs(trans)
        elif opts.stepped:
            ctrl.commitTransactionStepped(trans)
        else:
            ctrl.commitTransaction(trans)

# vim:ts=4:sw=4:et
