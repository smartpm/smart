#!/usr/bin/python
from distutils.command.install_scripts import install_scripts
from distutils.core import setup, Extension
import sys
import re

verpat = re.compile("VERSION *= *\"(.*)\"")
data = open("gepeto/const.py").read()
m = verpat.search(data)
if not m:
    sys.exit("error: can't find VERSION")
VERSION = m.group(1)

setup(name="gepeto",
      version = VERSION,
      description = "Gepeto is an advanced packaging tool",
      author = "Gustavo Niemeyer",
      author_email = "niemeyer@conectiva.com",
      license = "GPL",
      long_description =
"""\
Gepeto is an advanced packaging tool.
""",
      packages = [
                  "gepeto",
                  "gepeto.backends",
                  "gepeto.backends.rpm",
                  "gepeto.backends.slack",
                  "gepeto.channels",
                  "gepeto.commands",
                  "gepeto.interfaces",
                  "gepeto.interfaces.gtk",
                  "gepeto.interfaces.text",
                  "gepeto.interfaces.images",
                  "gepeto.util",
                  "gepeto.util.elementtree",
                 ],
      scripts = ["gpt"],
      ext_modules = [
                     Extension("gepeto.ccache", ["gepeto/ccache.c"]),
                     Extension("gepeto.backends.rpm.crpmver",
                               ["gepeto/backends/rpm/crpmver.c"]),
                    ],
      )

