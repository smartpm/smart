from epm.transaction import Transaction, PolicyInstall
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
    print trans
    print "Running transaction"
    from epm.backends.rpm.pm import RPMPackageManager
    pm = RPMPackageManager()
    from epm.progress import RPMStyleProgress
    prog = RPMStyleProgress()
    #pm.commit(trans, prog)
    ctrl.standardFinalize()

# vim:ts=4:sw=4:et
