from epm.transaction import Transaction, upgradePackages
from epm.transaction import PolicyInstall, PolicyGlobalUpgrade
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
    if opts.args:
        trans.setPolicy(PolicyInstall())
        for arg in opts.args:
            matcher = MasterMatcher(arg)
            pkgs = matcher.filter(pkgs)
    else:
        trans.setPolicy(PolicyGlobalUpgrade())
    pkgs = [x for x in pkgs if x.installed]
    if not pkgs:
        raise Error, "'%s' matches no uninstalled packages" % arg
    upgradePackages(trans, pkgs)
    ctrl.standardFinalize()

# vim:ts=4:sw=4:et
