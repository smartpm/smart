#!/usr/bin/python
from distutils.command.install_scripts import install_scripts
from distutils.core import setup, Extension
import distutils.file_util
import distutils.dir_util
import sys
import re

verpat = re.compile("VERSION *= *\"(.*)\"")
data = open("epm.py").read()
m = verpat.search(data)
if not m:
    sys.exit("error: can't find VERSION")
VERSION = m.group(1)

# Python really rocks, isn't it. ;-)
copy_file_orig = distutils.file_util.copy_file
copy_tree_orig = distutils.dir_util.copy_tree
def copy_file(src, dst, *args, **kwargs):
    if dst.endswith("bin/epm.py"):
        dst = dst[:-3]
    copy_file_orig(src, dst, *args, **kwargs)
def copy_tree(*args, **kwargs):
    outputs = copy_tree_orig(*args, **kwargs)
    for i in range(len(outputs)):
        if outputs[i].endswith("bin/epm.py"):
            outputs[i] = outputs[i][:-3]
    return outputs
distutils.file_util.copy_file = copy_file
distutils.dir_util.copy_tree = copy_tree

setup(name="epm",
      version = VERSION,
      description = "EPM is an extended package manager aiming to replace APT",
      author = "Gustavo Niemeyer",
      author_email = "niemeyer@conectiva.com",
      license = "GPL",
      long_description =
"""EPM is an Extended Package Manager aiming to replace APT""",
      packages = ["epm"],
      scripts = ["epm.py"],
      ext_modules = [
                     Extension("epm.ccache",
      			       ["epm/ccache.c"]),
                     Extension("epm.loaders.rpm.crpmver",
                               ["epm/loaders/rpm/crpmver.c"]),
                    ],
      )

