#!/usr/bin/python
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
import sys
if sys.version_info < (2, 3):
    sys.exit("error: python 2.3 or later required")

from smart.const import VERSION, DEBUG, DATADIR
from smart.option import OptionParser
from smart import init
from smart import *
import pwd
import os

USAGE="smart command [options] [arguments]"

DESCRIPTION="""
Action commands:
    update
    install
    reinstall
    upgrade
    remove
    fix
    download

Query commands:
    search
    query

Setup commands:
    channel
    priority
    mirror
    flag

Run "smart command --help" for more information.
"""

EXAMPLES = """
smart install --help
smart install pkgname
smart --gui
smart --gui install pkgname
smart --shell
"""

def parse_options(argv):
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION,
                          examples=EXAMPLES,
                          version="smart %s" % VERSION)
    parser.disable_interspersed_args()
    parser.add_option("--config-file", metavar="FILE",
                      help="configuration file (default is <data-dir>/config)")
    parser.add_option("--data-dir", metavar="DIR",
                      help="data directory (default is %s)" % DATADIR)
    parser.add_option("--log-level", metavar="LEVEL",
                      help="set the log level to LEVEL (debug, info, "
                           "warning, error)")
    parser.add_option("--gui", action="store_true",
                      help="use the default graphic interface")
    parser.add_option("--shell", action="store_true",
                      help="use the default shell interface")
    parser.add_option("--interface", metavar="NAME",
                      help="use the given interface")
    parser.add_option("-o", "--option", action="append", default=[],
                      metavar="OPT",
                      help="set the option given by a name=value pair")
    opts, args = parser.parse_args()
    if args:
        opts.command = args[0]
        opts.argv = args[1:]
    else:
        opts.command = None
        opts.argv = []
    if not (opts.command or opts.gui or opts.shell):
        parser.print_help()
        sys.exit(1)
    return opts

def set_config_options(options):
    import re, copy

    globals = {}
    globals["__builtins__"] = {}
    globals["True"] = True
    globals["true"] = True
    globals["yes"] = True
    globals["False"] = False
    globals["false"] = False
    globals["no"] = False

    p = re.compile(r"^([-a-zA-Z0-9]+)(\+?=)(.*)$")

    for opt in options:
        m = p.match(opt)
        if not m:
            raise Error, "Invalid option: %s" % opt
        name, assign, value = m.groups()
        if assign == "+=":
            lst = sysconf.get(name)
            if lst is None:
                lst = []
            elif type(lst) != list:
                raise Error, "Current value of '%s' is not a list" % name
            else:
                lst = copy.copy(lst)
        else:
            lst = None

        try:
            value = int(value)
        except ValueError:
            try:
                value = eval(value, globals)
            except:
                pass
        if lst:
            lst.append(value)
            value = lst
        sysconf.set(name, value, soft=True)

def main(argv):
    # Get the right $HOME, even when using sudo.
    if os.getuid() == 0:
        os.environ["HOME"] = pwd.getpwuid(0)[5]
    opts = None
    try:
        opts = parse_options(argv)
        ctrl = init(opts)
        if opts.option:
            set_config_options(opts.option)
        iface.run(opts.command, opts.argv)
        ctrl.saveSysConf()
        ctrl.restoreMediaState()
    except Error, e:
        if opts and opts.log_level == "debug":
            import traceback
            traceback.print_exc()
        if iface.object:
            iface.error(str(e))
        else:
            sys.stderr.write("error: %s\n" % e)
        sys.exit(1)
    except KeyboardInterrupt:
        if opts and opts.log_level == "debug":
            import traceback
            traceback.print_exc()
            sys.exit(1)
        sys.stderr.write("\nInterrupted\n")
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])

# vim:ts=4:sw=4:et
