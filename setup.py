#!/usr/bin/python
from distutils.command.install_scripts import install_scripts
from distutils.core import setup, Extension
import distutils.file_util
import distutils.dir_util
import sys
import re

verpat = re.compile("VERSION *= *\"(.*)\"")
data = open("cpm.py").read()
m = verpat.search(data)
if not m:
    sys.exit("error: can't find VERSION")
VERSION = m.group(1)

# Python really rocks, isn't it. ;-)
copy_file_orig = distutils.file_util.copy_file
copy_tree_orig = distutils.dir_util.copy_tree
def copy_file(src, dst, *args, **kwargs):
    if dst.endswith("bin/cpm.py"):
        dst = dst[:-3]
    copy_file_orig(src, dst, *args, **kwargs)
def copy_tree(*args, **kwargs):
    outputs = copy_tree_orig(*args, **kwargs)
    for i in range(len(outputs)):
        if outputs[i].endswith("bin/cpm.py"):
            outputs[i] = outputs[i][:-3]
    return outputs
distutils.file_util.copy_file = copy_file
distutils.dir_util.copy_tree = copy_tree

setup(name="cpm",
      version = VERSION,
      description = "CPM is an advanced packaging tool",
      author = "Gustavo Niemeyer",
      author_email = "niemeyer@conectiva.com",
      license = "GPL",
      long_description =
"""\
CPM Package Manager is an advanced packaging system.
""",
      packages = ["cpm"],
      scripts = ["cpm.py"],
      ext_modules = [
                     Extension("cpm.ccache",
      			       ["cpm/ccache.c"]),
                     Extension("cpm.backends.rpm.crpmver",
                               ["cpm/backends/rpm/crpmver.c"]),
                    ],
      )

