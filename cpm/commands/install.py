from cpm.transaction import Transaction, PolicyInstall
from cpm.matcher import MasterMatcher
from cpm.cmdline import initCmdLine
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
    policy = PolicyInstall()
    trans = Transaction(cache, policy)
    for arg in opts.args:
        matcher = MasterMatcher(arg)
        pkgs = matcher.filter(cache.getPackages())
        pkgs = [x for x in pkgs if not x.installed]
        if not pkgs:
            raise Error, "'%s' matches no uninstalled packages" % arg
        if len(pkgs) > 1:
            raise Error, "'%s' matches multiple packages: %s" % \
                         (arg, ", ".join([str(x) for x in pkgs]))
        else:
            pkg = pkgs[0]
            trans.install(pkg)
            policy.setLocked(pkg, True)
    trans.minimize()
    ctrl.commitTransaction(trans)

# vim:ts=4:sw=4:et
