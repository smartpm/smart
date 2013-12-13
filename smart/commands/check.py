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
from smart.transaction import checkPackages
from smart.option import OptionParser
from smart.cache import Package
from smart import *
import string
import re

USAGE=_("smart check [options] [package] ...")

DESCRIPTION=_("""
This command will check relations between packages. If no
packages are explicitly given, all packages in the selected
channels will be checked. Relations of the checked packages
will only match packages inside the selected channels.

Use the 'fix' command to fix broken relations of
installed packages.
""")

EXAMPLES=_("""
smart check
smart check pkgname
smart check '*kgna*'
smart check pkgname-1.0
smart check pkgname-1.0-1
smart check pkgname1 pkgname2
""")

def option_parser():
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION,
                          examples=EXAMPLES)
    parser.add_option("--all", action="store_true",
                      help=_("check packages in all channels"))
    parser.add_option("--installed", action="store_true",
                      help=_("check packages which are in at least "
                             "one installed channel (default)"))
    parser.add_option("--available", action="store_true",
                      help=_("check packages which are in at least "
                             "one non-installed channel"))
    parser.add_option("--channels", action="store", metavar="ALIASES",
                      help=_("check packages which are inside the "
                             "given channels (comma separated aliases)"))
    return parser

def parse_options(argv):
    parser = option_parser()
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(ctrl, opts, reloadchannels=True):

    # Argument check
    opts.check_args_of_option("channels", 1)

    if sysconf.get("auto-update"):
        from smart.commands import update
        updateopts = update.parse_options([])
        update.main(ctrl, updateopts)
    else:
        if reloadchannels:
            ctrl.reloadChannels()

    cache = ctrl.getCache()

    if opts.all:
        relateset = dict.fromkeys(cache.getPackages(), True)
    else:
        relateset = {}
        if opts.available:
            for pkg in cache.getPackages():
                if not pkg.installed:
                    relateset[pkg] = True
                else:
                    for loader in pkg.loaders:
                        if not loader.getInstalled():
                            relateset[pkg] = True
                            break

        if opts.channels:
            aliases = opts.channels.split(",")
            notfound = []
            disabled = []
            channels = sysconf.get("channels", ())
            for alias in aliases:
                if alias not in channels:
                    notfound.append(alias)
                elif channels[alias].get("disabled"):
                    disabled.append(alias)
            if notfound:
                raise Error, _("Channels not found: %s") % ", ".join(notfound)
            elif disabled:
                iface.warning(_("Channels are disabled: %s") % \
                              ", ".join(disabled))
            for pkg in cache.getPackages():
                for loader in pkg.loaders:
                    if loader.getChannel().getAlias() in opts.channels:
                        relateset[pkg] = True
                        break

        if opts.installed or not opts.channels and not opts.available:
            for pkg in cache.getPackages():
                if pkg.installed:
                    relateset[pkg] = True

    if opts.args:
        checkset = {}
        for arg in opts.args:
            ratio, results, suggestions = ctrl.search(arg)

            if not results:
                if suggestions:
                    dct = {}
                    for r, obj in suggestions:
                        if isinstance(obj, Package):
                            dct[obj] = True
                        else:
                            dct.update(dict.fromkeys(obj.packages, True))
                    raise Error, _("'%s' matches no packages. "
                                   "Suggestions:\n%s") % \
                                 (arg, "\n".join(["    "+str(x) for x in dct]))
                else:
                    raise Error, _("'%s' matches no packages") % arg

            dct = {}
            for obj in results:
                if isinstance(obj, Package):
                    dct[obj] = True
                else:
                    dct.update(dict.fromkeys(obj.packages, True))
            checkset.update(dct)
    else:
        checkset = relateset

    return not checkPackages(cache, checkset, relateset, report=True)

# vim:ts=4:sw=4:et
