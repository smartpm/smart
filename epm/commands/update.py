from epm.option import OptionParser
from epm.control import Control
from epm.cmdline import initCmdLine
from epm import *
import string
import re

USAGE="epm update [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts):
    ctrl = Control(opts)
    initCmdLine(ctrl)
    ctrl.standardInit()
    initCmdLine(ctrl)
    fetcher = ctrl.getFetcher()
    fetcher.setUseCache(False)
    ctrl.acquireRepositories()
    ctrl.standardFinalize()

# vim:ts=4:sw=4:et
