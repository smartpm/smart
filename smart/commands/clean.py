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
from smart.option import OptionParser
from smart import *
import re, os

USAGE=_("smart clean [options]")

DESCRIPTION=_("""
This command cleans the package cache. You can use it to
delete old unused files that were left behind because of
an incomplete transaction.
""")

def parse_options(argv):
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION)
    parser.add_option("-y", "--yes", action="store_true",
                      help=_("do not ask for confirmation"))
    parser.add_option("-v", "--verbose", action="store_true",
                      help=_("show cleaned packages"))
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(ctrl, opts):

    localdir = os.path.join(sysconf.get("data-dir"), "packages/")

    if not os.path.isdir(localdir):
        raise Error, _("Cache directory %s not found.") % localdir

    iface.info(_("Cleaning package cache..."))
   
    os.chdir(localdir)
    for root, dirs, files in os.walk(localdir):
        for cached_pkg in files:
            if opts.yes or iface.askYesNo(_("Clean %s?") % cached_pkg):
                try:
                    os.unlink(cached_pkg)
                    if opts.verbose:
                        iface.info(_("Cleaned %s..." % cached_pkg))
                except os.error, msg:
                    raise Error, _("Can't remove cached package %s: %s") % (cached_pkg, str(msg))

# vim:ts=4:sw=4:et
