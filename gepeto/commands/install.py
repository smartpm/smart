from gepeto.transaction import Transaction, PolicyInstall, sortUpgrades, INSTALL
from gepeto.matcher import MasterMatcher
from gepeto.option import OptionParser
from gepeto import *
import string
import re

USAGE="gpt install [options] packages"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    parser.add_option("--stepped", action="store_true",
                      help="split operation in steps")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):
    ctrl.updateCache()
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
            iface.warning("'%s' matches multiple packages, selecting: %s" % \
                          (arg, pkgs[0]))
        pkg = pkgs[0]
        trans.enqueue(pkg, INSTALL)
    iface.showStatus("Computing transaction...")
    trans.run()
    iface.hideStatus()
    if trans:
        if opts.stepped:
            ctrl.commitTransactionStepped(trans)
        else:
            ctrl.commitTransaction(trans)

# vim:ts=4:sw=4:et
