from gepeto.option import OptionParser
from gepeto import *
import string
import re

USAGE="gpt test [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):
    ctrl.updateCache()
    import __main__
    __main__.ctrl = ctrl
    __main__.cache = ctrl.getCache()
    try:
        import user
    except ImportError:
        pass

# vim:ts=4:sw=4:et
