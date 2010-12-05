#
# Copyright (c) 2005 Canonical
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#            Mauricio Teixeira <mteixeira@webset.net>
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
from smart.option import OptionParser
from smart import *
import os

USAGE=_("smart clean [options]")

DESCRIPTION=_("""
This command cleans the package cache. You can use it to
delete old unused files that were left behind because of
an incomplete transaction.
""")

def option_parser():
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION)
    parser.add_option("--auto", action="store_true",
                      help=_("remove packages not in other channels"))
    return parser

def parse_options(argv):
    parser = option_parser()
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(ctrl, opts):

    packagesdir = os.path.join(sysconf.get("data-dir"), "packages/")

    if not os.path.isdir(packagesdir):
        raise Error, _("Directory not found: %s") % packagesdir

    iface.info(_("Removing cached package files..."))
   
    if opts.auto:
        available = {}
        ctrl.reloadChannels()
        cache = ctrl.getCache()
        for pkg in cache.getPackages():
            for loader in pkg.loaders:
                if loader.getInstalled():
                    continue
                info = loader.getInfo(pkg)
                for url in info.getURLs():
                    available[os.path.basename(url)] = pkg

    for root, dirs, files in os.walk(packagesdir):
        for cached_pkg in files:
            if opts.auto:
                if cached_pkg in available:
                    continue
            try:
                os.unlink(os.path.join(root, cached_pkg))
                iface.debug(_("Removed %s") % cached_pkg)
            except os.error, e:
                iface.error(_("Can't remove cached package %s: %s") \
                            % (cached_pkg, str(e)))

# vim:ts=4:sw=4:et
