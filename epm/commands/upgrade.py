from epm.transaction import Transaction, globalUpgrade
from epm.transaction import PolicyInstall, PolicyGlobalUpgrade
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
    if opts.args:
        trans.setPolicy(PolicyInstall())
        for arg in opts.args:
            matcher = MasterMatcher(arg)
            pkgs = matcher.filter(cache.getPackages())
            pkgs = [x for x in pkgs if not x.installed]
            if not pkgs:
                raise Error, "'%s' matches no uninstalled packages" % arg
            pkgs.sort()
            trans.install(pkgs[-1])
    else:
        trans.setPolicy(PolicyGlobalUpgrade())
        trans.globalUpgrade()
    trans.run()
    ctrl.standardFinalize()

# vim:ts=4:sw=4:et
