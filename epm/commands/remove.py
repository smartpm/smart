from epm.transaction import Transaction, PolicyRemove
from epm.matcher import MasterMatcher
from epm.option import OptionParser
from epm.control import Control
from epm.cache import Provides
from epm import *
import string
import re

USAGE="epm install [options] packages"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts):
    ctrl = Control(opts)
    ctrl.standardInit()
    cache = ctrl.getCache()
    policy = PolicyRemove()
    trans = Transaction(cache, policy)
    found = False
    for arg in opts.args:
        matcher = MasterMatcher(arg)
        for pkg in matcher.filter(cache.getPackages()):
            if pkg.installed:
                found = True
                trans.remove(pkg)
                policy.setLocked(pkg, True)
    if not found:
        raise Error, "no packages matched given arguments"
    print trans
    ctrl.standardFinalize()

# vim:ts=4:sw=4:et
