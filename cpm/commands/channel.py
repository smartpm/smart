from cpm.option import OptionParser
from cpm.channel import *
from cpm import *
import os

USAGE="cpm channel [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    parser.add_option("--add", action="store_true",
                      help="arguments are key=value pairs defining a "
                           "channel, or a filename/url pointing to "
                           "a channel description")
    parser.add_option("--set", action="store_true",
                      help="arguments are key=value pairs defining a "
                           "channel, or a filename/url pointing to "
                           "a channel description")
    parser.add_option("--remove", action="store_true",
                      help="arguments are channel aliases to be removed")
    parser.add_option("--show", action="store_true",
                      help="show channels with aliases given as arguments "
                           "or all channels, if no argument was given")
    parser.add_option("--enable", action="store_true",
                      help="arguments are channel aliases to be enabled")
    parser.add_option("--disable", action="store_true",
                      help="arguments are channel aliases to be disabled")
    parser.add_option("--force", action="store_true",
                      help="execute without asking")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):

    channels = sysconf.get("channels", setdefault={})
    
    if opts.add:

        if len(opts.args) == 1:
            arg = opts.args[0]
            if os.path.isfile(arg):
                data = open(arg).read()
                newchannels = parseChannelDescription(data)
            elif ":/" in arg:
                succ, fail = ctrl.fetchFiles([arg], "channel description")
                if fail:
                    raise Error, "Unable to fetch channel description: %s" \
                                 % fail[arg]
                data = open(succ[arg]).read()
                newchannels = parseChannelDescription(data)
                os.unlink(succ[arg])
            else:
                raise Error, "Don't know what to do with: %s" % arg
        else:
            newchannels = {}
            channel = {}
            alias = None
            for arg in opts.args:
                if "=" not in arg:
                    raise Error, "Argument '%s' has no '='" % arg
                key, value = arg.split("=")
                key = key.strip()
                value = value.strip()
                if key == "alias":
                    alias = value
                else:
                    channel[key] = value
            if not alias:
                raise Error, "Channel has no alias"
            if "type" not in channel:
                raise Error, "Channel has no type"

            newchannels[alias] = channel

        for alias in newchannels:
            channel = newchannels[alias]
            type = channel.get("type")
            desc = createChannelDescription(type, alias, channel)
            if not desc:
                continue
            if not opts.force:
                print
                print desc
                print
                res = raw_input("Include this channel (y/N)? ").strip()
            if opts.force or res and res[0].lower() == "y":
                try:
                    createChannel(type, alias, channel)
                except Error, e:
                    iface.error("Invalid channel: %s" % e)
                else:
                    while alias in channels:
                        iface.info("Channel alias '%s' is already in use."
                                   % alias)
                        res = raw_input("Choose another one: ").strip()
                        if res:
                            alias = res
                    channels[alias] = channel

    elif opts.set:

        if not opts.args:
            raise Error, "Invalid arguments"

        alias = opts.args.pop(0)
        if "=" in alias:
            raise Error, "First argument must be the channel alias"
        if alias not in channels:
            raise Error, "Channel with alias '%s' not found" % alias
        oldchannel = channels[alias]

        channel = {}
        for arg in opts.args:
            if "=" not in arg:
                raise Error, "Argument '%s' has no '='" % arg
            key, value = arg.split("=")
            key = key.strip()
            if key == "type":
                raise Error, "Can't change the channel type"
            if key == "alias":
                raise Error, "Can't change the channel alias"
            channel[key] = value.strip()

        newchannel = oldchannel.copy()
        newchannel.update(channel)
        for key in newchannel.keys():
            if not newchannel[key]:
                del newchannel[key]
        try:
            createChannel(newchannel.get("type"), alias, newchannel)
        except Error, e:
            raise Error, "Invalid channel: %s" % e

        oldchannel.update(channel)
        for key in oldchannel.keys():
            if not oldchannel[key]:
                del oldchannel[key]

    elif opts.remove:

        for alias in opts.args:
            if alias not in channels:
                continue
            if opts.force or iface.askYesNo("Remove channel '%s'" % alias):
                del channels[alias]

    elif opts.enable or opts.disable:

        for alias in opts.args:
            if alias not in channels:
                continue
            channel = channels[alias]
            if opts.enable:
                if "disabled" in channel:
                    del channel["disabled"]
            else:
                channel["disabled"] = "yes"

    elif opts.show:

        for alias in opts.args or channels:
            if alias not in channels:
                continue
            channel = channels[alias]
            desc = createChannelDescription(channel.get("type"),
                                            alias, channel)
            if desc:
                print desc
                print

# vim:ts=4:sw=4:et
