from epm.option import OptionParser
from epm import *

USAGE="epm install [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    opts, args = parser.parse_args(argv)
    if len(args) < 1:
        raise Error, "package names needed"
    opts.args = args
    return opts

def main(opts):
    pass

# vim:ts=4:sw=4:et
