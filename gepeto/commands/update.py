from gepeto.option import OptionParser
from gepeto.const import NEVER
from gepeto import *
import string
import re

USAGE="gepeto update [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):
    ctrl.reloadSysConfChannels()
    channels = ctrl.getChannels()
    if opts.args:
        channels = [x for x in channels if x.getAlias() in opts.args]
    if channels:
        ctrl.updateCache()
        ctrl.updateCache(channels, caching=NEVER)
        cache = ctrl.getCache()
        newpackages = sysconf.filterByFlag("new", cache.getPackages())
        if not newpackages:
            iface.showStatus("There are no new packages.")
        else:
            iface.showStatus("There are %d new packages." % len(newpackages))

# vim:ts=4:sw=4:et
