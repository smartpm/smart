from epm.transaction import Transaction
from epm.transaction import PolicyUpgrade
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
    trans = Transaction(cache)
    pkgs = cache.getPackages()
    trans.setPolicy(PolicyUpgrade())
    if opts.args:
        newpkgs = []
        for arg in opts.args:
            matcher = MasterMatcher(arg)
            fpkgs = matcher.filter(pkgs)
            if not fpkgs:
                raise Error, "'%s' matches no uninstalled packages" % arg
            newpkgs.extend(fpkgs)
        pkgs = dict.fromkeys(newpkgs).keys()
    pkgs = [x for x in pkgs if x.installed]
    trans.upgrade(pkgs)
    print trans
    print "Running transaction"
    from epm.backends.rpm.pm import RPMPackageManager
    pm = RPMPackageManager()
    pm.commit(trans)
    ctrl.standardFinalize()

# vim:ts=4:sw=4:et
