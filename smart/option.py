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
from smart.util import optparse
from smart import Error, _
import textwrap
import sys, os

# NOTICE: The standard optparse module haven't been touched, but since
#         this code subclasses it and trusts on a specific interface,
#         an internal copy is being used to avoid future breakage.

__all__ = ["OptionParser", "OptionValueError", "append_all"]

try:
    optparse.STD_HELP_OPTION.help = \
            _("show this help message and exit")
    optparse.STD_VERSION_OPTION.help = \
            _("show program's version number and exit")
except AttributeError:
    optparse._ = _

OptionValueError = optparse.OptionValueError

class HelpFormatter(optparse.HelpFormatter):

    def __init__(self):
        optparse.HelpFormatter.__init__(self, 2, 24, 79, 1)

    def format_usage(self, usage):
        return _("Usage: %s\n") % usage

    def format_heading(self, heading):
        heading = _(heading)
        return "\n%*s%s:\n" % (self.current_indent, "", heading.capitalize())
        _("options")

    def format_description(self, description):
        return description.strip()

    def format_option(self, option):
        help = option.help
        if help:
            option.help = help.capitalize()
        result = optparse.HelpFormatter.format_option(self, option)
        option.help = help
        return result

class OptionParser(optparse.OptionParser):

    def __init__(self, usage=None, help=None, examples=None, skipunknown=False,
                 **kwargs):
        if not "formatter" in kwargs:
            kwargs["formatter"] = HelpFormatter()
        optparse.OptionParser.__init__(self, usage, **kwargs)
        self._override_help = help
        self._examples = examples
        self._skipunknown = skipunknown

    def format_help(self, formatter=None):
        if formatter is None:
            formatter = self.formatter
        if self._override_help:
            result = self._override_help.strip()
            result += "\n"
        else:
            result = optparse.OptionParser.format_help(self, formatter)
            result = result.strip()
            result += "\n"
            if self._examples:
                result += formatter.format_heading(_("examples"))
                formatter.indent()
                for line in self._examples.strip().splitlines():
                    result += " "*formatter.current_indent
                    result += line+"\n"
                formatter.dedent()
        result += "\n"
        return result

    def error(self, msg):
        raise Error, msg

    def _process_args(self, largs, rargs, values):
        """_process_args(largs : [string],
                         rargs : [string],
                         values : Values)

        Process command-line arguments and populate 'values', consuming
        options and arguments from 'rargs'.  If 'allow_interspersed_args' is
        false, stop at the first non-option argument.  If true, accumulate any
        interspersed non-option arguments in 'largs'.
        """
        while rargs:
            arg = rargs[0]
            # We handle bare "--" explicitly, and bare "-" is handled by the
            # standard arg handler since the short arg case ensures that the
            # len of the opt string is greater than 1.
            if arg == "--":
                del rargs[0]
                return
            elif arg[0:2] == "--":
                # process a single long option (possibly with value(s))
                try:
                    self._process_long_opt(rargs, values)
                except optparse.BadOptionError:
                    # That's the reason to change this function. We want
                    # to be able to skip unknown options.
                    if not self._skipunknown:
                        raise
                    largs.append(arg)
                    if "=" in arg:
                        rargs.pop(0)
            elif arg[:1] == "-" and len(arg) > 1:
                # process a cluster of short options (possibly with
                # value(s) for the last one only)
                try:
                    self._process_short_opts(rargs, values)
                except optparse.BadOptionError:
                    # That's the reason to change this function. We want
                    # to be able to skip unknown options.
                    if not self._skipunknown:
                        raise
                    largs.append(arg)
            elif self.allow_interspersed_args:
                largs.append(arg)
                del rargs[0]
            else:
                return                  # stop now, leave this arg in rargs

    def _process_short_opts(self, rargs, values):
        arg = rargs.pop(0)
        stop = False
        i = 1
        for ch in arg[1:]:
            opt = "-" + ch
            option = self._short_opt.get(opt)
            i += 1                      # we have consumed a character

            if not option:
                # That's the reason to change this function. We must
                # raise an error so that the argument is post-processed
                # when using skipunknown.
                raise optparse.BadOptionError, _("no such option: %s") % opt
            if option.takes_value():
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    rargs.insert(0, arg[i:])
                    stop = True

                nargs = option.nargs
                if len(rargs) < nargs:
                    if nargs == 1:
                        self.error(_("%s option requires an argument") % opt)
                    else:
                        self.error(_("%s option requires %d arguments")
                                   % (opt, nargs))
                elif nargs == 1:
                    value = rargs.pop(0)
                else:
                    value = tuple(rargs[0:nargs])
                    del rargs[0:nargs]

            else:                       # option doesn't take a value
                value = None

            option.process(opt, value, values, self)

            if stop:
                break

def append_all(option, opt, value, parser):
    if option.dest is None:
        option.dest = opt
        while option.dest[0] == "-":
            option.dest = option.dest[1:]
    dest = option.dest.replace("-", "_")
    lst = getattr(parser.values, dest)
    if type(lst) is not list:
        lst = []
        setattr(parser.values, dest, lst)
    rargs = parser.rargs
    while rargs and rargs[0] and rargs[0][0] != "-":
        lst.append(parser.rargs.pop(0))


# vim:et:ts=4:sw=4
