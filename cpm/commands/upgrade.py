from cpm.transaction import Transaction
from cpm.transaction import PolicyUpgrade
from cpm.matcher import MasterMatcher
from cpm.cmdline import initCmdLine
from cpm.option import OptionParser
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
    ctrl = initCmdLine(opts)
    ctrl.fetchRepositories()
    ctrl.loadCache()
    cache = ctrl.getCache()
    trans = Transaction(cache)
    pkgs = cache.getPackages()
    trans.setPolicy(PolicyUpgrade(cache))
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
    print "Computing upgrade..."
    trans.upgrade(pkgs)
    if not trans:
        print "No upgrades available!"
    else:
        trans.minimize()
        print trans
        #ctrl.commitTransaction(trans)

# vim:ts=4:sw=4:et
