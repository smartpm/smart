from epm.option import OptionParser
from epm.control import Control
from epm.cache import Provides
from epm import *
import string
import re

USAGE="epm test [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts):
    ctrl = Control(opts)
    ctrl.standardInit()
    import __main__
    __main__.ctrl = ctrl
    __main__.cache = ctrl.getCache()
    #try:
    #    import user
    #except ImportError:
    #    pass

# vim:ts=4:sw=4:et
