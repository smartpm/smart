#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from smart.transaction import Transaction, PolicyInstall, sortUpgrades
from smart.transaction import INSTALL, REINSTALL
from smart.matcher import MasterMatcher
from smart.option import OptionParser, append_all
from smart.channel import FileChannel
from smart import *
import string
import re
import os

USAGE="smart download [options] package ..."

DESCRIPTION="""
This command allows downloading one or more given packages.
"""

EXAMPLES="""
smart download pkgname
smart download '*kgna*'
smart download pkgname-1.0
smart download pkgname-1.0-1
smart download pkgname1 pkgname2
smart download pkgname --urls 2> pkgname-url.txt
smart download --from-urls pkgname-url.txt
smart download --from-urls http://some.url/some/path/somefile
"""

def parse_options(argv):
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION,
                          examples=EXAMPLES)
    parser.defaults["from_urls"] = []
    parser.defaults["target"] = os.getcwd()
    parser.add_option("--target", action="store", metavar="DIR",
                      help="packages will be saved in given directory")
    parser.add_option("--urls", action="store_true",
                      help="dump needed urls and don't download packages")
    parser.add_option("--from-urls", action="callback", callback=append_all,
                      help="download files from the given urls and/or from "
                           "the given files with lists of urls")
    opts, args = parser.parse_args(argv)
    opts.args = args
    if not os.path.isdir(opts.target):
        raise Error, "Directory not found:", opts.target
    return opts

def main(ctrl, opts):

    packages = []
    if opts.args:
        ctrl.updateCache()
        cache = ctrl.getCache()
        for arg in opts.args:
            matcher = MasterMatcher(arg)
            pkgs = matcher.filter(cache.getPackages())
            if not pkgs:
                raise Error, "'%s' matches no packages" % arg
            if len(pkgs) > 1:
                sortUpgrades(pkgs)
                iface.warning("'%s' matches multiple packages, selecting: %s"
                              % (arg, pkgs[0]))
            packages.append(pkgs[0])
        if opts.urls:
            ctrl.dumpURLs(packages)
        else:
            ctrl.downloadPackages(packages, targetdir=opts.target)
    elif opts.from_urls:
        urls = []
        for arg in opts.from_urls:
            if ":/" in arg:
                urls.append(arg)
            elif os.path.isfile(arg):
                urls.extend([x.strip() for x in open(arg)])
            else:
                raise Error, "Argument is not a file nor url: %s" % arg
        ctrl.downloadURLs(urls, "URLs", targetdir=opts.target)

# vim:ts=4:sw=4:et
