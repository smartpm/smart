#
# Written by Pascal Bleser <guru@unixtech.be>
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
from smart.util.strtools import isGlob, sizeToStr
from smart.transaction import Transaction, PolicyUpgrade, UPGRADE
from smart.option import OptionParser
from smart.cache import Provides, PreRequires, Package
from smart.const import *
from smart import *
import tempfile
import fnmatch
import string
import sys
import os
import re

USAGE=_("smart newer")

DESCRIPTION=_("""
This command shows packages that have available upgrades.
""")

EXAMPLES=_("""
smart newer
""")

def option_parser(help=None):
    if help:
        parser = OptionParser(help=help)
    else:
        parser = OptionParser(usage=USAGE,
                              description=DESCRIPTION,
                              examples=EXAMPLES)
    return parser

def parse_options(argv, help=None):
    parser = option_parser(help)
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(ctrl, opts, reloadchannels=True):

    if reloadchannels:
        ctrl.reloadChannels()

    cache = ctrl.getCache()
    trans = Transaction(cache, PolicyUpgrade)
    checkstate = None

    for pkg in cache.getPackages():
        if pkg.installed:
            trans.enqueue(pkg, UPGRADE)
            pass
        pass

    trans.run()
    changeset = trans.getChangeSet()
    state = changeset.getPersistentState()
    if not state:
        iface.showStatus(_("No interesting upgrades available."))
        return 2
    elif checkstate:
        for entry in state:
            if checkstate.get(entry) != state[entry]:
                break
            pass
        else:
            iface.showStatus(_("There are pending upgrades!"))
            return 1
        iface.showStatus(_("There are new upgrades available!"))
    elif not trans:
        iface.showStatus(_("No interesting upgrades available."))
        pass
    else:
        iface.hideStatus()
        upgrades = [pkg for (pkg, op) in changeset.items() if op == INSTALL]
        upgrades.sort()
        report = []
        for pkg in upgrades:
            upgraded = []
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    for prvpkg in prv.packages:
                        if prvpkg.installed:
                            upgraded.append(prvpkg)
                            pass
                        pass
                    pass
                pass

            for loader in pkg.loaders:
                if not loader.getInstalled():
                    break
                else:
                    continue
            info = loader.getInfo(pkg)
            for url in info.getURLs():
                size = info.getSize(url)
            ch = loader.getChannel()

            if len(upgraded) > 0:
                if str.find(upgraded[0].version, '@') != -1 :
                    (uversion, uarch) = upgraded[0].version.split('@')
                else:
                    (uversion, uarch) = (upgraded[0].version, "")
            else:
                uversion = _('(not installed)')
                uarch = ''
                pass
            if str.find(pkg.version, '@') != -1 :
                (iversion, iarch) = pkg.version.split('@')
            else:
                (iversion, iarch) = (pkg.version, "")
            entry = [pkg.name, uversion, uarch, iversion, iarch, ch.getAlias(), size]
            report.append(entry)
            pass

        # TODO: make this use an interface method
        
        report.insert(0, [_('Package Name'), _('Installed'), '', _('Upgrade'), '', _('Channel'), _('Size')])

        maxwidth = [0, 0, 0, 0, 0, 0, 0]
        for entry in report:
            for i in range(len(entry)):
                if entry[i] != None and len(str(entry[i])) > maxwidth[i]:
                    maxwidth[i] = len(str(entry[i]))
                    pass
                pass
            pass

        line = []
        mask = []
        mask.append('%-'+str(maxwidth[0])+'s')
        mask.append('%-'+str(maxwidth[1])+'s %'+str(maxwidth[2])+'s')
        mask.append('%-'+str(maxwidth[3])+'s %'+str(maxwidth[4])+'s')
        mask.append('%-'+str(maxwidth[5])+'s')
        mask.append('%-'+str(maxwidth[6])+'s')
        
        for mw in maxwidth:
            line.append(''.join(['-' for x in range(mw)]))
            pass

        maskline = ' | '.join(mask)

        print maskline % tuple(report[0])
        print '-+-'.join(mask) % tuple(line)
        for entry in report[1:]:
            print maskline % tuple(entry)

# vim:ts=4:sw=4:et
