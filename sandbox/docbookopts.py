#!/usr/bin/env python

from smart.option import OptionParser
from smart.const import VERSION

import optparse
import textwrap
import os

# This is a quick hack, to extract the help info as DocBook
# Written by Anders F Bjorklund <afb@users.sourceforge.net>

sortorder = \
[
#Action commands:
    "update",
    "install",
    "reinstall",
    "upgrade",
    "remove",
    "check",
    "fix",
    "download",
    "clean",

#Query commands:
    "search",
    "query",
    "newer",
    "info",
    "stats",

#Setup commands:
    "config",
    "channel",
    "priority",
    "mirror",
    "flag",

    "nothing"
]

def compare(x, y):
     return sortorder.index(x)-sortorder.index(y)

class DocBookFormatter(optparse.HelpFormatter):

    def __init__(self):
        optparse.HelpFormatter.__init__(self, 4, 24, 79, 1)

    def format_usage(self, usage):
        usage = usage.replace(" ...", "...")
        args = usage.split()
        command = args.pop(0)
        result = "<cmdsynopsis><command>%s</command>\n" % command
        action = args.pop(0)
        result += "  <arg choice='plain'>%s</arg>\n" % action
        for arg in args:
            opt = ""
            if arg.endswith("..."):
                arg = arg.rstrip('.')
                opt += " rep='repeat'"
            if arg.startswith("["):
                arg = arg.strip('[]')
                opt += " choice='opt'"
            else:
                opt += " choice='req'"
            result += "  <arg%s>%s</arg>\n" % (opt, arg)
        result += "</cmdsynopsis>\n"
        return result

    def format_heading(self, heading):
        return "\n%*s<para>%s:</para>\n" % (self.current_indent, "", heading.capitalize())

    def format_description(self, description):
        description = description.replace("&", "&amp;")
        description = description.replace("<", "&lt;")
        description = description.replace(">", "&gt;")
        return "<para>%s</para>\n" % description

    def format_option(self, option):
        help = option.help
        if help:
            option.help = help.capitalize()
        result = []
        if option == parser.option_list[0]:
            result += "<variablelist>\n"
        opts = self.option_strings[option]
        opt_width = self.help_position - self.current_indent - 2
        if len(opts) > opt_width:
            opts = "%*s%s\n" % (self.current_indent, "", opts)
            indent_first = self.help_position
        else:                       # start help on same line as opts
            opts = "%*s%-*s  " % (self.current_indent, "", opt_width, opts)
            indent_first = 0
        result.append("<varlistentry>\n")
        result.append("  <term>")
        for opt in opts.split(","):
             result.append("<option>%s</option> " % opt.strip())
        result.append("</term>\n")
        result.append("  <listitem><para>")
        if option.help:
            help_text = self.expand_default(option)
            help_lines = textwrap.wrap(help_text, self.help_width)
            result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
            result.extend(["%*s%s\n" % (self.help_position, "", line)
                           for line in help_lines[1:]])
        result[-1] = result[-1].rstrip()
        result.append("</para></listitem>\n")
        result.append("</varlistentry>\n")
        if option == parser.option_list[-1]:
            result += "</variablelist>\n"
        option.help = help
        return "".join(result)

commands = []
for entry in os.listdir("smart/commands"):
    if entry != "__init__.py" and entry.endswith(".py"):
        command = entry[:-3]
        commands.append(command)
    else:
        continue

commands.sort(compare)
for command in commands:
    mod = __import__("smart.commands."+command, globals(), locals(),
                     ['USAGE', 'DESCRIPTION', 'EXAMPLES', 'option_parser'], -1)

    formatter = DocBookFormatter()
    
    formatter._short_opt_fmt = "%s <replaceable>%s</replaceable>"
    formatter._long_opt_fmt = "%s=<replaceable>%s</replaceable>"

    if hasattr(mod, 'option_parser'):
        #print command
        print ('<sect3 id="smart-text-%s" xreflabel="%s"><title>%s</title>\n' %
              (command, command.capitalize(), command.capitalize()))

        parser = mod.option_parser()
        parser.remove_option("--help")
        if parser._examples:
            parser._examples = "<synopsis>" + parser._examples + "</synopsis>\n"
        parser.formatter = formatter
        print parser.format_help(formatter)
        
        print "</sect3>\n"

