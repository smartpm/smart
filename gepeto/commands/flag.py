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
from gepeto import *
import string
import re

USAGE="gpt flag [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    parser.defaults["set"] = []
    parser.defaults["remove"] = []
    parser.defaults["show"] = None
    parser.add_option("--set", action="callback", callback=append_all,
                      help="set flags given in pairs of flag name/target, "
                           "where targets may use just the package "
                           "name, or the package name, relation, and "
                           "version, such as: lock 'python > 1.0'")
    parser.add_option("--remove", action="callback", callback=append_all,
                      help="remove flags given in pairs of flag name/target, "
                           "where targets may use just the package "
                           "name, or the package name, relation, and "
                           "version, such as: lock 'python > 1.0'")
    parser.add_option("--show", action="callback", callback=append_all,
                      help="show packages with the flags given as arguments "
                           "or all flags if no argument was given")
    parser.add_option("--force", action="store_true",
                      help="ignore problems")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

TARGETRE = re.compile(r"^\s*(?P<name>\S+?)\s*"
                      r"((?P<rel>[<>=]+)\s*"
                      r"(?P<version>\S+))?\s*$")

def main(opts, ctrl):
    flags = sysconf.get("package-flags", setdefault={})

    for args in (opts.set, opts.remove):

        if len(args) % 2 != 0:
            raise Error, "Invalid arguments"

        for i in range(0, len(args), 2):
            flag, target = args[i:i+2]

            m = TARGETRE.match(target)
            if not m:
                raise Error, "Invalid target: %s" % arg

            g = m.groupdict()

            names = flags.setdefault(flag, {})
            lst = names.setdefault(g["name"], [])

            tup = (g["rel"], g["version"])

            if args is opts.set:
                if tup not in lst:
                    lst.append(tup)
            else:
                if tup in lst:
                    lst.remove(tup)
                    if not lst:
                        del names[g["name"]]

                if flags.get(flag) == {}:
                    del flags[flag]

    if opts.show is not None:

        showflags = opts.show or flags.keys()
        showflags.sort()

        for flag in showflags:
            flag = flag.strip()

            print flag

            names = flags.get(flag, {})
            nameslst = names.keys()
            nameslst.sort()
            for name in nameslst:
                for relation, version in names[name]:
                    if relation and version:
                        print "   ", name, relation, version
                    else:
                        print "   ", name
            print

# vim:ts=4:sw=4:et
