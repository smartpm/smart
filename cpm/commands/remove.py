from cpm.transaction import Transaction, PolicyRemove, REMOVE
from cpm.cmdline import initCmdLine
from cpm.matcher import MasterMatcher
from cpm.option import OptionParser
from cpm import *
import string
import re

USAGE="cpm remove [options] packages"

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
    trans = Transaction(cache, PolicyRemove)
    found = False
    for arg in opts.args:
        matcher = MasterMatcher(arg)
        for pkg in matcher.filter(cache.getPackages()):
            if pkg.installed:
                found = True
                trans.enqueue(pkg, REMOVE)
    if not found:
        raise Error, "no installed packages matched given arguments"
    trans.run()
    if trans:
        ctrl.commitTransaction(trans)

    ctrl.saveSysConf()

# vim:ts=4:sw=4:et
