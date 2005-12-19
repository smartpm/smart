#!/usr/bin/env python
#
# Copyright (c) 2005 Canonical
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
from smart.option import OptionParser
from smart import init
from smart import *
import tempfile
import unittest
import doctest
import shutil
import tests
import sys
import os

USAGE=_("test.py [options] [<test filename>, ...]")

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts


def main():

    datadir = tempfile.mkdtemp()

    __builtins__.__dict__.update(tests.__dict__)

    try:

        ctrl = init(datadir=datadir)
        opts = parse_options(sys.argv[1:])

        runner = unittest.TextTestRunner()
        loader = unittest.TestLoader()
        testdir = os.path.dirname(tests.__file__)
        filenames = os.listdir(testdir)
        doctest_flags = doctest.ELLIPSIS
        unittests = []
        doctests = []
        for filename in filenames:
            if (filename == "__init__.py" or filename.endswith(".pyc") or
                opts.args and filename not in opts.args):
                pass
            elif filename.endswith(".py"):
                unittests.append(filename)
            elif filename.endswith(".txt"):
                doctests.append(filename)

        class Summary:
            def __init__(self):
                self.total_failures = 0
                self.total_tests = 0
            def __call__(self, failures, tests):
                self.total_failures += failures
                self.total_tests += tests
                print "(failures=%d, tests=%d)" % (failures, tests)

        summary = Summary()

        if unittests:
            print "Running unittests..."
            for filename in unittests:
                print "[%s]" % filename
                module = __import__("tests." + filename[:-3],
                                    None, None, [filename])
                test = loader.loadTestsFromModule(module)
                result = runner.run(test)
                summary(len(result.failures), test.countTestCases())
                print

                shutil.rmtree(datadir)
                os.mkdir(datadir)

        if doctests:
            print "Running doctests..."
            for filename in doctests:
                print "[%s]" % filename
                summary(*doctest.testfile(filename, package=tests,
                                          optionflags=doctest_flags))
                print

                shutil.rmtree(datadir)
                os.mkdir(datadir)

    finally:
        shutil.rmtree(datadir)

    print "Total failures: %d" % summary.total_failures
    print "Total tests: %d" % summary.total_tests

    return bool(summary.total_failures)

if __name__ == "__main__":
    status = main()
    sys.exit(status)

# vim:ts=4:sw=4:et
