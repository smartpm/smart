from cpm.transaction import Transaction, PolicyInstall, sortUpgrades, INSTALL
from cpm.cmdline import initCmdLine, confirmChanges
from cpm.matcher import MasterMatcher
from cpm.option import OptionParser
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
    trans = Transaction(cache, PolicyInstall)
    for arg in opts.args:
        matcher = MasterMatcher(arg)
        pkgs = matcher.filter(cache.getPackages())
        pkgs = [x for x in pkgs if not x.installed]
        if not pkgs:
            raise Error, "'%s' matches no uninstalled packages" % arg
        if len(pkgs) > 1:
            sortUpgrades(pkgs)
            print "'%s' matches multiple packages, selecting: %s" % \
                  (arg, pkgs[0])
        pkg = pkgs[0]
        trans.enqueue(pkg, INSTALL)
    trans.run()
    if trans and confirmChanges(trans):
        ctrl.commitTransaction(trans)

# vim:ts=4:sw=4:et
