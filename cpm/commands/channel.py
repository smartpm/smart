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
    
    if opts.add:

        if len(opts.args) == 1:
            arg = opts.args[0]
            if os.path.isfile(arg):
                data = open(arg).read()
                channels = parseChannelDescription(data)
            elif ":/" in arg:
                succ, fail = ctrl.fetchFiles([arg], "channel description")
                if fail:
                    raise Error, "Unable to fetch channel description: %s" \
                                 % fail[arg]
                data = open(succ[arg]).read()
                channels = parseChannelDescription(data)
                os.unlink(succ[arg])
            else:
                raise Error, "Don't know what to do with: %s" % arg
        else:
            channels = []
            channel = {}
            for arg in opts.args:
                if "=" not in arg:
                    raise Error, "Argument '%s' has no '='" % arg
                key, value = arg.split("=")
                channel[key.strip()] = value.strip()
            if "type" not in channel:
                raise Error, "Channel has no type"
            if "alias" not in channel:
                raise Error, "Channel has no alias"

            channels.append(channel)

        curchannels = sysconf.get("channels")
        if curchannels is None:
            curchannels = []
            sysconf.set("channels", curchannels)
        for channel in channels:
            desc = createChannelDescription(channel)
            if not desc:
                continue
            if not opts.force:
                print
                print desc
                print
                res = raw_input("Include this channel (y/N)? ").strip()
            if opts.force or res and res[0].lower() == "y":
                try:
                    createChannel(channel.get("type"), channel)
                except Error, e:
                    print "error: invalid description: %s" % e
                else:
                    alias = channel.get("alias")
                    while [x for x in curchannels if x.get("alias") == alias]:
                        print "Channel alias '%s' is already in use." % alias
                        res = raw_input("Choose another one: ").strip()
                        if res:
                            alias = res
                    channel["alias"] = alias
                    curchannels.append(channel)

    elif opts.remove:

        channels = sysconf.get("channels", [])

        for arg in opts.args:

            if [x for x in channels if x.get("alias") == arg]:
                if not opts.force:
                    res = raw_input("Remove channel '%s' (y/N)? "
                                    % arg).strip()
                if opts.force or res and res[0].lower() == "y":
                    channels = [x for x in channels if x.get("alias") != arg]

        sysconf.set("channels", channels)

    elif opts.enable or opts.disable:

        channels = sysconf.get("channels", [])

        for channel in channels:
            if channel.get("alias") in opts.args:
                if opts.enable:
                    if "disabled" in channel:
                        del channel["disabled"]
                else:
                    channel["disabled"] = "yes"

    elif opts.show:

        channels = sysconf.get("channels", [])
        if opts.args:
            channels = [x for x in channels if x.get("alias") in opts.args]

        for channel in channels:
            desc = createChannelDescription(channel)
            if desc:
                print desc
            print

# vim:ts=4:sw=4:et
