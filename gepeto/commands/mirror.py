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
from gepeto.option import OptionParser, append_all
from gepeto.channel import *
from gepeto import *
import textwrap
import sys, os

USAGE="gpt mirror [options]"

DESCRIPTION="""
This command allows one to manipulate mirrors. Mirrors are URLs
that supposedly provide the same contents as are available in
other URLs, named origins in this help text. There is no internal
restriction on the kind of information which is mirrored. Once
an origin URL is provided, and one or more mirror URLs are
provided, these mirrors will be considered for any file which
is going to be fetched from an URL starting with the origin URL.
Whether the mirror will be chosen or not will depend on the
history of downloads from this mirror and from other mirrors for
the same URL, since mirrors are automatically balanced so that
the fastest mirror and with less errors is chosen. When errors
occur, the next mirror is tried.

For instance, if a mirror "http://mirror.url/path/" is provided
for the origin "ftp://origin.url/other/path/", and a file in
"ftp://origin.url/other/path/subpath/somefile" is going to be
fetched, the mirror will be considered for being used, and the
URL "http://mirror.url/path/subpath/somefile" will be used if
the mirror is chosen. Notice that strings are compared and
replaced without any pre-processing, so that it's possible to
use URLs ending in prefixes of directory entries.
"""

EXAMPLES="""
gpt mirror --show
gpt mirror --add ftp://origin.url/some/path/ http://mirror.url/path/
gpt mirror --remove ftp://origin.url/some/path/ http://mirror.url/path/
gpt mirror --clear-history ftp://origin.url/some/path/
gpt mirror --clear-history ftp://mirror.url/path/
gpt mirror --clear-history
"""

def parse_options(argv):
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION,
                          examples=EXAMPLES)
    parser.defaults["add"] = []
    parser.defaults["remove"] = []
    parser.defaults["clear_history"] = None
    parser.add_option("--show", action="store_true",
                      help="show current mirrors")
    parser.add_option("--add", action="callback", callback=append_all,
                      help="add to the given origin URL the given mirror URL, "
                           "provided either in pairs, or in a given file "
                           "in the format used by --show")
    parser.add_option("--remove", action="callback", callback=append_all,
                      help="remove from the given origin URL the given "
                           "mirror URL, provided either in pairs, or in a "
                           "given file in the format used by --show")
    parser.add_option("--clear-history", action="callback", callback=append_all,
                      help="clear history for the given origins/mirrors, or "
                           "for all mirrors")
    parser.add_option("--show-penalities", action="store_true",
                      help="show current penalities for origins/mirrors, "
                           "based on the history information")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def read_mirrors(filename):
    if not os.path.isfile(filename):
        raise Error, "File not found: %s" % filename
    result = []
    origin = None
    mirror = None
    for line in open(filename):
        url = line.strip()
        if not url:
            continue
        if line[0].isspace():
            mirror = url
        else:
            origin = url
            continue
        if not origin:
            raise Error, "Invalid mirrors file"
        result.append(origin)
        result.append(mirror)
    return result

def main(opts, ctrl):

    mirrors = sysconf.get("mirrors", setdefault={})
    history = sysconf.get("mirrors-history", setdefault=[])

    if opts.add:

        if len(opts.add) == 1:
            opts.add = read_mirrors(opts.add[0])

        if len(opts.add) % 2 != 0:
            raise Error, "Invalid arguments for --add"

        for i in range(0,len(opts.add),2):
            origin, mirror = opts.add[i:i+2]
            if origin in mirrors:
                if mirror not in mirrors[origin]:
                    mirrors[origin].append(mirror)
            else:
                mirrors[origin] = [mirror]

    if opts.remove:

        if len(opts.remove) == 1:
            opts.remove = read_mirrors(opts.remove[0])

        if len(opts.remove) % 2 != 0:
            raise Error, "Invalid arguments for --remove"

        for i in range(0,len(opts.remove),2):
            origin, mirror = opts.remove[i:i+2]
            if origin in mirrors:
                if mirror in mirrors[origin]:
                    mirrors[origin].remove(mirror)
                    if not mirrors[origin]:
                        del mirrors[origin]
                else:
                    if not mirrors[origin]:
                        del mirrors[origin]
                    raise Error, "Mirror not found"
            else:
                raise Error, "Origin not found"

    if opts.clear_history is not None:
        
        if opts.clear_history:
            history[:] = [x for x in history if x[0] not in opts.clear_history]
        else:
            del history[:]

    if opts.show:

        for origin in mirrors:
            print origin
            for mirror in mirrors[origin]:
                print "   ", mirror
            print

    if opts.show_penalities:

        from gepeto.mirror import MirrorSystem
        mirrorsystem = MirrorSystem()
        penalities = mirrorsystem.getPenalities()
        for url in penalities:
            print "%s %.5f" % (url, penalities[url])

# vim:ts=4:sw=4:et
