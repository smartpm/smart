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

def parse_options(argv):
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION)
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(ctrl, opts):

    packagesdir = os.path.join(sysconf.get("data-dir"), "packages/")

    if not os.path.isdir(packagesdir):
        raise Error, _("Directory not found: %s") % packagesdir

    iface.info(_("Removing cached package files..."))
   
    for root, dirs, files in os.walk(packagesdir):
        for cached_pkg in files:
            try:
                os.unlink(os.path.join(root, cached_pkg))
                iface.debug(_("Removed %s") % cached_pkg)
            except os.error, e:
                iface.error(_("Can't remove cached package %s: %s") \
                            % (cached_pkg, str(e)))

# vim:ts=4:sw=4:et
