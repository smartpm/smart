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
import pprint
import string
import re

USAGE="gpt config [options]"

DESCRIPTION="""
This command allows changing the internal configuration
representation arbitrarily. This is supposed to be used
by advanced users only, and is generally not needed.
"""

EXAMPLES="""
gpt config --set someoption.suboption=10
gpt config --remove someoption
gpt config --show someoption
gpt config --dump
"""

def parse_options(argv):
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION,
                          examples=EXAMPLES)
    parser.defaults["set"] = []
    parser.defaults["show"] = []
    parser.defaults["remove"] = []
    parser.add_option("--set", action="callback", callback=append_all,
                      help="set given key=value options")
    parser.add_option("--show", action="callback", callback=append_all,
                      help="show given options")
    parser.add_option("--remove", action="callback", callback=append_all,
                      help="remove given options")
    parser.add_option("--dump", action="store_true",
                      help="show all options")
    parser.add_option("--force", action="store_true",
                      help="ignore problems")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

SETRE = re.compile(r"^(?P<name>\S+?)"
                   r"(?:\[(?P<pos>\d+)\])?"
                   r"(?P<assign>\+?=)"
                   r"(?P<value>.*)$")
GETRE = re.compile(r"^(?P<name>\S+?)"
                   r"(?:\[(?P<pos>\d+)\])?$")
DELRE = GETRE

def getSubName(name, d, create=False):
    subnames = name.split(".")
    subnamestr = ""
    while len(subnames) > 1:
        if type(d) is not dict:
            raise Error, "Option '%s' exists and is not a dictionary" \
                         % subnamestr
        subname = subnames.pop(0)
        if subnamestr:
            subnamestr += "."
            subnamestr += subname
        else:
            subnamestr = subname
        if create:
            d = d.setdefault(subname, {})
        else:
            d = d.get(subname)
            if d is None:
                raise Error, "Option '%s' not found" % subnamestr
    return subnames[-1], d

def main(opts, ctrl):
    globals = {}
    globals["__builtins__"] = {}
    globals["True"] = True
    globals["true"] = True
    globals["yes"] = True
    globals["False"] = False
    globals["false"] = False
    globals["no"] = False

    for opt in opts.set:

        m = SETRE.match(opt)
        if not m:
            raise Error, "Invalid --set argument: %s" % opt

        g = m.groupdict()

        try:
            subname, d = getSubName(g["name"], sysconf.getMap(), True)
        except Error:
            if opts.force:
                continue
            raise

        if g["pos"]:
            pos = int(g["pos"])
            lst = d.get(subname)
            if not lst or pos >= len(lst):
                if opts.force:
                    continue
                raise Error, "Invalid sequence access in '%s'" % g["name"]
            if g["assign"] == "+=":
                elem = lst[pos]
                if type(elem) is not list:
                    if opts.force:
                        continue
                    raise Error, "Current value of '%s' is not a list" % \
                                 g["name"]
                def set(value, elem=elem):
                    elem.append(value)
            else:
                def set(value, lst=lst, pos=pos):
                    lst[pos] = value
        else:
            if g["assign"] == "+=":
                elem = d.setdefault(subname, [])
                if type(elem) is not list:
                    if opts.force:
                        continue
                    raise Error, "Current value of '%s' is not a list" % \
                                 g["name"]
                def set(value, elem=elem):
                    elem.append(value)
            else:
                def set(value, d=d, subname=subname):
                    d[subname] = value

        value = g["value"]
        try:
            value = int(value)
        except ValueError:
            try:
                value = eval(value, globals)
            except:
                pass
        set(value)

    for opt in opts.remove:

        m = DELRE.match(opt)
        if not m:
            raise Error, "Invalid --del argument: %s" % opt

        g = m.groupdict()

        try:
            subname, d = getSubName(g["name"], sysconf.getMap(), True)
        except Error:
            if opts.force:
                continue
            raise

        if g["pos"]:
            pos = int(g["pos"])
            lst = d.get(subname)
            if not lst or pos >= len(lst):
                if opts.force:
                    continue
                raise Error, "Invalid sequence access in '%s[%d]'" % \
                             (g["name"], pos)
            del lst[pos]
        else:
            if subname in d:
                del d[subname]
            else:
                if opts.force:
                    continue
                raise Error, "Option '%s' not found" % g["name"]
            
    for opt in opts.show:

        m = GETRE.match(opt)
        if not m:
            raise Error, "Invalid --show argument: %s" % opt

        g = m.groupdict()

        try:
            subname, d = getSubName(g["name"], sysconf.getMap())
        except Error:
            if opts.force:
                continue
            raise

        value = d.get(subname)
        if value is None:
            if opts.force:
                continue
            raise Error, "Option '%s' not found" % g["name"]

        if g["pos"]:
            pos = int(g["pos"])
            if type(value) not in (list, tuple):
                if opts.force:
                    continue
                raise Error, "Option '%s' is not a sequence" % g["name"]
            value = value[pos]

        pprint.pprint(value)

    if opts.dump:
        pprint.pprint(sysconf.getMap())

# vim:ts=4:sw=4:et
