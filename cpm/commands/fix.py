from cpm.transaction import Transaction, PolicyInstall, FIX
from cpm.matcher import MasterMatcher
from cpm.option import OptionParser
from cpm import *
import string
import re

USAGE="cpm fix [options] packages"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    parser.add_option("--stepped", action="store_true",
                      help="split operation in steps")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):
    ctrl.fetchRepositories()
    ctrl.loadCache()
    cache = ctrl.getCache()
    trans = Transaction(cache, PolicyInstall)
    pkgs = cache.getPackages()
    if opts.args:
        newpkgs = []
        for arg in opts.args:
            matcher = MasterMatcher(arg)
            fpkgs = matcher.filter(pkgs)
            if not fpkgs:
                raise Error, "'%s' matches no packages" % arg
            newpkgs.extend(fpkgs)
        pkgs = dict.fromkeys(newpkgs).keys()
    for pkg in pkgs:
        trans.enqueue(pkg, FIX)
    iface.showStatus("Computing transaction...")
    trans.run()
    if not trans:
        iface.showStatus("No problems to resolve!")
    else:
        iface.hideStatus()
        if opts.stepped:
            ctrl.commitTransactionStepped(trans)
        else:
            ctrl.commitTransaction(trans)

# vim:ts=4:sw=4:et
