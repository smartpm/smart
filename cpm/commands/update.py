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
    ctrl.reloadSysConfRepositories()
    repositories = ctrl.getRepositories()
    if opts.args:
        repositories = [x for x in repositories if x.getName() in opts.args]
    ctrl.fetchRepositories(repositories, caching=NEVER)

# vim:ts=4:sw=4:et
