from cpm.transaction import Transaction, PolicyRemove
from cpm.matcher import MasterMatcher
from cpm.option import OptionParser
from cpm.control import Control
from cpm.cache import Provides
from cpm import *
import string
import re

USAGE="cpm install [options] packages"

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
        raise Error, "no installed packages matched given arguments"
    trans.minimize()
    print trans
    print "Running transaction"
    from cpm.backends.rpm.pm import RPMPackageManager
    pm = RPMPackageManager()
    from cpm.progress import RPMStyleProgress
    prog = RPMStyleProgress()
    #pm.commit(trans, prog)
    ctrl.standardFinalize()

# vim:ts=4:sw=4:et
