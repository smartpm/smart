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
import optparse
import sys, os

__all__ = ["OptionParser", "OptionValueError", "append_all"]

OptionValueError = optparse.OptionValueError

class CapitalizeHelpFormatter(optparse.IndentedHelpFormatter):

    def format_usage(self, usage):
        return optparse.IndentedHelpFormatter \
                .format_usage(self, usage).capitalize()

    def format_heading(self, heading):
        return optparse.IndentedHelpFormatter \
                .format_heading(self, heading).capitalize()

class OptionParser(optparse.OptionParser):

    def __init__(self, usage=None, help=None, **kwargs):
        if not "formatter" in kwargs:
            kwargs["formatter"] = CapitalizeHelpFormatter()
        optparse.OptionParser.__init__(self, usage, **kwargs)
        self._override_help = help

    def format_help(self, formatter=None):
        if self._override_help:
            return self._override_help
        else:
            return optparse.OptionParser.format_help(self, formatter)

def append_all(option, opt, value, parser):
    if option.dest is None:
        option.dest = opt
        while option.dest[0] == "-":
            option.dest = option.dest[1:]
    lst = getattr(parser.values, option.dest)
    if type(lst) is not list:
        lst = []
        setattr(parser.values, option.dest, lst)
    rargs = parser.rargs
    while rargs and rargs[0] and rargs[0][0] != "-":
        lst.append(parser.rargs.pop(0))


# vim:et:ts=4:sw=4
