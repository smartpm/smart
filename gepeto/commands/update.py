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
from gepeto.option import OptionParser
from gepeto.const import NEVER
from gepeto import *
import string
import re

USAGE="gepeto update [options] [channelalias] ..."

DESCRIPTION="""
This command will update the known information about the
given channels. If no channels are given, all channels
which are not disabled or setup for manual updates will
be updated.
"""

EXAMPLES="""
gpt update
gpt update mychannel
gpt update mychannel1 mychannel2
"""

def parse_options(argv):
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION,
                          examples=EXAMPLES)
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):
    ctrl.reloadSysConfChannels()
    if opts.args:
        channels = [x for x in ctrl.getChannels() if x.getAlias() in opts.args]
        if not channels:
            return
    else:
        channels = None
    # First, load current cache to keep track of new packages.
    ctrl.updateCache()
    ctrl.updateCache(channels, caching=NEVER)
    cache = ctrl.getCache()
    newpackages = sysconf.filterByFlag("new", cache.getPackages())
    if not newpackages:
        iface.showStatus("Channels have no new packages.")
    else:
        if len(newpackages) <= 10:
            info = ":\n"
            for pkg in newpackages:
                info += "    %s\n" % pkg
        else:
            info = "."
        iface.showStatus("Channels have %d new packages%s"
                         % (len(newpackages), info))

# vim:ts=4:sw=4:et
