#
# Copyright (c) 2005 Canonical
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
from smart.option import OptionParser, append_all
from smart.util.filetools import getFileDigest
from smart.const import NEVER
from smart.channel import *
from smart import *
import tempfile
import textwrap
import sys, os

USAGE=_("smart channel [options]")

DESCRIPTION=_("""
This command allows one to manipulate channels. Channels are
used as sources of information about installed and available
packages. Depending on the channel type, a different backend
is used to handle interactions with the operating system and
extraction of information from the given channel.

The following channel types are available:

%(types)s

Use --help-type <type> for more information.
""")

EXAMPLES=_("""
smart channel --help-type apt-rpm
smart channel --add mydb type=rpm-sys name="RPM Database"
smart channel --add mychannel type=apt-rpm name="Some repository" \\
                  baseurl=http://somewhere.com/pub/repos components=extra
smart channel --set mychannel priority=-100
smart channel --disable mychannel
smart channel --remove mychannel
smart channel --show
smart channel --show mychannel > mychannel.txt
smart channel --add ./mychannel.txt
smart channel --add http://some.url/mychannel.txt
smart channel --add /mnt/cdrom
""")

def build_types():
    result = ""
    typeinfo = getAllChannelInfos().items()
    typeinfo.sort()
    for type, info in typeinfo:
        result += "  %-10s - %s\n" % (type, info.name)
    return result.rstrip()

def format_fields(fields):
    result = []
    maxkey = max([len(x[0])+(x[3] is None and 4 or 0) for x in fields])
    for key, label, ftype, default, descr in fields:
        if not descr:
            descr = label
        indent = " "*(5+maxkey)
        lines = textwrap.wrap(text=descr, width=70,
                              initial_indent=indent,
                              subsequent_indent=indent)
        label = lines.pop(0).strip()
        if default is None:
            key += " (*)"
        result.append("  %s%s - %s" % (key, " "*(maxkey-len(key)), label))
        for line in lines:
            result.append(line)
    return "\n".join(result)

def option_parser():
    description = DESCRIPTION % {"types": build_types()}
    parser = OptionParser(usage=USAGE,
                          description=description,
                          examples=EXAMPLES)
    parser.defaults["add"] = None
    parser.defaults["set"] = None
    parser.defaults["remove"] = None
    parser.defaults["enable"] = None
    parser.defaults["disable"] = None
    parser.defaults["list"] = None
    parser.defaults["show"] = None
    parser.defaults["yaml"] = None
    parser.add_option("--add", action="callback", callback=append_all,
                      help=_("argument is an alias and one or more "
                             "key=value pairs defining a channel, or a "
                             "filename/url pointing to a channel description "
                             "in the same format used by --show, or a "
                             "directory path where autodetection will be "
                             "tried"))
    parser.add_option("--set", action="callback", callback=append_all,
                      help=_("argument is an alias, and one or more key=value "
                             "pairs modifying a channel"))
    parser.add_option("--remove", action="callback", callback=append_all,
                      help=_("arguments are channel aliases to be removed"))
    parser.add_option("--remove-all", action="store_true",
                      help=_("remove all existent channels"))
    parser.add_option("--list", action="callback", callback=append_all,
                      help=_("list all known channel aliases"))
    parser.add_option("--show", action="callback", callback=append_all,
                      help=_("show channels with given aliases, or all "
                           "channels if no arguments were given"))
    parser.add_option("--yaml", action="callback", callback=append_all,
                      help=_("show given channels in YAML format"))
    parser.add_option("--edit", action="store_true",
                      help=_("edit channels in editor set by $EDITOR"))
    parser.add_option("--enable", action="callback", callback=append_all,
                      help=_("enable channels with given aliases"))
    parser.add_option("--disable", action="callback", callback=append_all,
                      help=_("disable channels with given aliases"))
    parser.add_option("-y", "--yes", action="store_true",
                      help=_("execute without asking"))
    parser.add_option("--help-type", action="store", metavar="TYPE",
                      help=_("show further information about given type"))
    return parser

def parse_options(argv):
    parser = option_parser()
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(ctrl, opts):

    if opts.help_type:
        info = getChannelInfo(opts.help_type)
        print _("Type:"), opts.help_type, "-", info.name
        print
        print info.description.strip()
        print
        print _("Fields:")
        print format_fields(info.fields)
        print
        print _("(*) These fields are necessary for this type.")
        print
        sys.exit(0)

    if (sysconf.getReadOnly() is True and opts.list is None and
                              opts.show is None and opts.yaml is None):
        iface.warning(_("Can't edit channels information."))
        raise Error, _("Configuration is in readonly mode.")

    # Argument check
    opts.check_args_of_option("set", -1)
    opts.check_args_of_option("remove", -1)
    opts.check_args_of_option("edit", 0)
    opts.check_args_of_option("enable", -1)
    opts.check_args_of_option("disable", -1)
    opts.ensure_action("channel", ["add", "set", "remove", "remove-all",
                       "list", "show", "yaml", "enable", "disable"])
    opts.check_remaining_args()

    if opts.add is not None:
        if not opts.add and opts.args == ["-"]:
            newchannels = []
            data = sys.stdin.read()
            descriptions = parseChannelsDescription(data)
            for alias in descriptions:
                channel = descriptions[alias]
                channel["alias"] = alias
                newchannels.append(channel)
        elif len(opts.add) == 1:
            arg = opts.add[0]
            if os.path.isdir(arg):
                sysconf.set("default-localmedia", arg, soft=True)
                newchannels = detectLocalChannels(arg)
            elif os.path.isfile(arg):
                newchannels = []
                data = open(arg).read()
                descriptions = parseChannelsDescription(data)
                for alias in descriptions:
                    channel = descriptions[alias]
                    channel["alias"] = alias
                    newchannels.append(channel)
            elif ":/" in arg:
                succ, fail = ctrl.downloadURLs([arg], "channel description")
                if fail:
                    raise Error, _("Unable to fetch channel description: %s")\
                                 % fail[arg]
                data = open(succ[arg]).read()
                if succ[arg].startswith(sysconf.get("data-dir")):
                    os.unlink(succ[arg])
                newchannels = []
                descriptions = parseChannelsDescription(data)
                for alias in descriptions:
                    channel = descriptions[alias]
                    channel["alias"] = alias
                    newchannels.append(channel)
            else:
                raise Error, _("File not found: %s") % arg
        elif opts.add:
            alias = opts.add.pop(0).strip()
            if not alias:
                raise Error, _("Channel has no alias")
            channel = {}
            for arg in opts.add:
                if "=" not in arg:
                    raise Error, _("Argument '%s' has no '='") % arg
                key, value = arg.split("=", 1)
                channel[key.strip()] = value.strip()
            channel = parseChannelData(channel)
            channel["alias"] = alias
            newchannels = [channel]
        else:
            raise Error, _("Channel information needed")

        newaliases = []
        for channel in newchannels:
            type = channel.get("type")
            if not opts.yes:
                info = getChannelInfo(type)
                print
                for key, label, ftype, default, descr in info.fields:
                    if key in channel:
                        print "%s: %s" % (label, channel[key])
                print
            if opts.yes or iface.askYesNo(_("Include this channel?")):
                try:
                    createChannel("alias", channel)
                except Error, e:
                    raise
                else:
                    try:
                        alias = channel.get("alias")
                        while not alias or sysconf.has(("channels", alias)):
                            if alias:
                                print _("Channel alias '%s' is already in "
                                        "use.") % alias
                            alias = raw_input(_("Channel alias: ")).strip()
                        del channel["alias"]
                        sysconf.set(("channels", alias), channel)
                        newaliases.append(alias)
                    except KeyboardInterrupt:
                        print

        removable = [alias for alias in newaliases
                     if sysconf.get(("channels", alias, "removable"))]
        if removable:
            print
            print _("Updating removable channels...")
            print
            import update
            updateopts = update.parse_options(removable)
            update.main(ctrl, updateopts)

    if opts.set:
        if not opts.set:
            raise Error, _("Invalid arguments")

        alias = opts.set.pop(0)
        if "=" in alias:
            raise Error, _("First argument must be the channel alias")

        channel = sysconf.get(("channels", alias))
        if not channel:
            raise Error, _("Channel with alias '%s' not found") % alias

        for arg in opts.set:
            if "=" not in arg:
                raise Error, _("Argument '%s' has no '='") % arg
            key, value = arg.split("=", 1)
            key = key.strip()
            if key == "type":
                raise Error, _("Can't change the channel type")
            if key == "alias":
                raise Error, _("Can't change the channel alias")
            channel[key] = value.strip()

        for key in channel.keys():
            if not channel[key]:
                del channel[key]

        createChannel(alias, channel)

        sysconf.set(("channels", alias), channel)

    if opts.remove:
        for alias in opts.remove:
            if (not sysconf.has(("channels", alias)) or opts.yes or
                iface.askYesNo(_("Remove channel '%s'?") % alias)):
                if not sysconf.remove(("channels", alias)):
                    iface.warning(_("Channel '%s' not found.") % alias)

    if opts.remove_all:
        if (not sysconf.get("channels") or opts.yes or
            iface.askYesNo(_("Remove ALL channels?"))):
            sysconf.remove("channels")

    if opts.enable:
        for alias in opts.enable:
            if not sysconf.has(("channels", alias)):
                iface.warning(_("Channel '%s' not found.") % alias)
            else:
                sysconf.remove(("channels", alias, "disabled"))

    if opts.disable:
        for alias in opts.disable:
            if not sysconf.has(("channels", alias)):
                iface.warning(_("Channel '%s' not found.") % alias)
            else:
                sysconf.set(("channels", alias, "disabled"), "yes")

    if opts.list is not None:
        for alias in (opts.list or sysconf.get("channels", ())):
            channel = sysconf.get(("channels", alias))
            if not channel:
                iface.warning(_("Channel '%s' not found.") % alias)
            else:
                print alias

    if opts.show is not None:
        for alias in (opts.show or sysconf.get("channels", ())):
            channel = sysconf.get(("channels", alias))
            if not channel:
                iface.warning(_("Channel '%s' not found.") % alias)
            else:
                desc = createChannelDescription(alias,
                                                parseChannelData(channel))
                if desc:
                    print desc
                    print

    if opts.yaml is not None:
        try:
            import yaml
        except ImportError:
            raise Error, _("Please install PyYAML in order to use this function")
        yamlchannels = {}
        for alias in (opts.yaml or sysconf.get("channels", ())):
            channel = sysconf.get(("channels", alias))
            if not channel:
                iface.warning(_("Channel '%s' not found.") % alias)
            else:
                data = parseChannelData(channel)
                yamlchannels[alias] = data    
        print yaml.dump(yamlchannels)

    if opts.edit:
        sysconf.assertWritable()
        
        fd, name = tempfile.mkstemp(".ini")
        file = os.fdopen(fd, "w")
        aliases = sysconf.keys("channels")
        aliases.sort()
        for alias in aliases:
            channel = sysconf.get(("channels", alias))
            desc = createChannelDescription(alias, parseChannelData(channel))
            print >>file, desc
            print >>file
        file.close()
        editor = os.environ.get("EDITOR", "vi")
        olddigest = getFileDigest(name)
        while True:
            os.system("%s %s" % (editor, name))
            newdigest = getFileDigest(name)
            if newdigest == olddigest:
                break
            file = open(name)
            data = file.read()
            file.close()
            try:
                newchannels = parseChannelsDescription(data)
            except Error, e:
                iface.error(unicode(e))
                if not iface.askYesNo(_("Continue?"), True):
                    break
                else:continue
            failed = False
            for alias in newchannels:
                channel = newchannels[alias]
                try:
                    createChannel(alias, channel)
                except Error, e:
                    failed = True
                    iface.error(_("Error in '%s' channel: %s") %
                                (alias, unicode(e)))
            if failed:
                if not iface.askYesNo(_("Continue?"), True):
                    break
            else:
                sysconf.set("channels", newchannels)
                break
        os.unlink(name)

# vim:ts=4:sw=4:et
