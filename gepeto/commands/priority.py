from gepeto.option import OptionParser
from gepeto import *
import string
import re

USAGE="gpt priority [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    parser.add_option("--set", action="store_true",
                      help="set priority")
    parser.add_option("--remove", action="store_true",
                      help="unset priority")
    parser.add_option("--show", action="store_true",
                      help="show priorities")
    parser.add_option("--force", action="store_true",
                      help="ignore problems")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):
    priorities = sysconf.get("package-priorities", setdefault={})

    if opts.set:

        if len(opts.args) == 2:
            name, priority = opts.args
            alias = None
        elif len(opts.args) == 3:
            name, alias, priority = opts.args
        else:
            raise Error, "Invalid arguments"

        try:
            priority = int(priority)
        except ValueError:
            raise Error, "Invalid priority"

        priorities.setdefault(name, {})[alias] = priority

    elif opts.remove:

        if len(opts.args) == 1:
            name = opts.args[0]
            alias = None
        elif len(opts.args) == 2:
            name, alias = opts.args
        else:
            raise Error, "Invalid arguments"

        pkgpriorities = priorities.get(name)
        if pkgpriorities and alias in pkgpriorities:
            del pkgpriorities[alias]
            if not pkgpriorities:
                del priorities[name]
        elif not opts.force:
            raise Error, "Priority not found"

    elif opts.show:

        header = ("Package", "Channel", "Priority")
        print "%-30s %-20s %s" % header
        print "-"*(52+len(header[-1]))

        showpriorities = opts.args or priorities.keys()
        showpriorities.sort()

        for name in showpriorities:
            pkgpriorities = priorities.get(name)
            aliases = pkgpriorities.keys()
            aliases.sort()
            for alias in aliases:
                priority = pkgpriorities[alias]
                print "%-30s %-20s %d" % (name, alias or "*", priority)

        print

# vim:ts=4:sw=4:et
