from cpm.option import OptionParser
from cpm.const import NEVER
from cpm import *
import string
import re

USAGE="cpm update [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):
    ctrl.reloadSysConfChannels()
    channels = ctrl.getChannels()
    if opts.args:
        channels = [x for x in channels if x.getName() in opts.args]
    ctrl.fetchChannels(channels, caching=NEVER)

# vim:ts=4:sw=4:et
