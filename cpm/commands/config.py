from cpm.option import OptionParser
from cpm.cmdline import initCmdLine
from cpm import *
import pprint
import string
import re

USAGE="cpm config [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    parser.add_option("--set", action="append", default=[],
                      help="set given option")
    parser.add_option("--show", action="append", default=[],
                      help="show given option")
    parser.add_option("--remove", action="append", default=[],
                      help="remove given option")
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
            raise Error, "option '%s' exists and is not a dictionary" \
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
                raise Error, "option '%s' not found" % subnamestr
    return subnames[-1], d

def main(opts):
    ctrl = initCmdLine(opts)

    for opt in opts.set:

        m = SETRE.match(opt)
        if not m:
            raise Error, "invalid --set argument: %s" % opt

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
                raise Error, "invalid sequence access in '%s'" % g["name"]
            if g["assign"] == "+=":
                elem = lst[pos]
                if type(elem) is not list:
                    if opts.force:
                        continue
                    raise Error, "current value of '%s' is not a list" % \
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
                    raise Error, "current value of '%s' is not a list" % \
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
                value = eval(value)
            except:
                pass
        set(value)

    for opt in opts.remove:

        m = DELRE.match(opt)
        if not m:
            raise Error, "invalid --del argument: %s" % opt

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
                raise Error, "invalid sequence access in '%s[%d]'" % \
                             (g["name"], pos)
            del lst[pos]
        else:
            if subname in d:
                del d[subname]
            else:
                if opts.force:
                    continue
                raise Error, "option '%s' not found" % g["name"]
            
    for opt in opts.show:

        m = GETRE.match(opt)
        if not m:
            raise Error, "invalid --show argument: %s" % opt

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
            raise Error, "option '%s' not found" % g["name"]

        if g["pos"]:
            pos = int(g["pos"])
            if type(value) not in (list, tuple):
                if opts.force:
                    continue
                raise Error, "option '%s' is not a sequence" % g["name"]
            value = value[pos]

        pprint.pprint(value)

    ctrl.saveSysConf()

    if opts.dump:
        pprint.pprint(sysconf.getMap())

# vim:ts=4:sw=4:et
