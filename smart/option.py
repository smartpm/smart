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
import re

# NOTICE: The standard optparse module haven't been touched, but since
#         this code subclasses it and trusts on a specific interface,
#         an internal copy is being used to avoid future breakage.

__all__ = ["OptionParser", "OptionValueError", "Values", "Option", "append_all"]

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

class Values(optparse.Values):

    # Check if the given option has the specified number of arguments
    # Raise an error if the option has an invalid number of arguments
    # A negative number for 'nargs' means "at least |nargs| arguments are needed"
    def check_args_of_option(self, opt, nargs, err=None):
        given_opts = getattr(self, "_given_opts", [])
        if not opt in given_opts:
            return
        values = getattr(self, opt, [])
        if type(values) != type([]):
            return
        if nargs < 0:
            nargs = -nargs
            if len(values) >= nargs:
                return
            if not err:
                if nargs == 1:
                    err = _("Option '%s' requires at least one argument") % opt
                else:
                    err = _("Option '%s' requires at least %d arguments") % (opt, nargs)
            raise Error, err
        elif nargs == 0:
            if len( values ) == 0:
                return
            raise Error, err
        else:
            if len(values) == nargs:
                return
            if not err:
                if nargs == 1:
                    err = _("Option '%s' requires one argument") % opt
                else:
                    err = _("Option '%s' requires %d arguments") % (opt, nargs)
            raise Error, err

    # Check that at least one of the options in 'actlist' was given as an argument
    # to the command 'cmdname'
    def ensure_action(self, cmdname, actlist):
        given_opts = getattr(self, "_given_opts", [])
        for action in actlist:
            if action in given_opts:
                return
        raise Error, _("No action specified for command '%s'") % cmdname

    # Check if there are any other arguments left after parsing the command line and
    # raise an error if such arguments are found
    def check_remaining_args(self):
        if self.args:
            raise Error, _("Invalid argument(s) '%s'" % str(self.args))

class Option(optparse.Option):

    def take_action(self, action, dest, opt, value, values, parser):
        # Keep all the options in the command line in the '_given_opts' array
        # This will be used later to validate the command line
        given_opts = getattr(parser.values, "_given_opts", [])
        user_opt = re.sub(r"^\-*", "", opt).replace("-", "_")
        given_opts.append(user_opt)
        setattr(parser.values, "_given_opts", given_opts)
        optparse.Option.take_action(self, action, dest, opt, value, values, parser)

class OptionParser(optparse.OptionParser):

    def __init__(self, usage=None, help=None, examples=None, skipunknown=False,
                 **kwargs):
        if not "formatter" in kwargs:
            kwargs["formatter"] = HelpFormatter()
        kwargs["option_class"] = Option
        optparse.OptionParser.__init__(self, usage, **kwargs)
        self._override_help = help
        self._examples = examples
        self._skipunknown = skipunknown

    def get_default_values(self):
        if not self.process_default_values:
            # Old, pre-Optik 1.5 behaviour.
            return Values(self.defaults)

        defaults = self.defaults.copy()
        for option in self._get_all_options():
            default = defaults.get(option.dest)
            if isinstance(default, basestring):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)

        return Values(defaults)

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
