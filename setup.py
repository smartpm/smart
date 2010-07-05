#!/usr/bin/env python
from distutils.command.install_data import install_data
from distutils.sysconfig import get_python_lib, get_config_var
from distutils.core import setup, Extension
from distutils.dep_util import newer
from distutils.log import info
from distutils import sysconfig
import distutils.file_util
import distutils.dir_util
import sys, os
import glob
import re

class InstallData(install_data):
    def run(self):
        self.data_files.extend(self._compile_po_files())
        install_data.run(self)

    def _compile_po_files(self):
        i18nfiles = []
        for directory in glob.glob("locale/*/LC_MESSAGES"):
            po = os.path.join(directory, 'smart.po')
            mo = os.path.join(directory, 'smart.mo')
            if not os.path.exists(mo) or newer(po, mo):
                cmd = 'msgfmt -o %s %s' % (mo, po)
                info('compiling %s -> %s' % (po, mo))
                if os.system(cmd) != 0:
                    info('Error while running msgfmt on %s' % directory)
            dest = os.path.dirname(os.path.join('share', mo))
            i18nfiles.append((dest, [mo]))
        return i18nfiles

if os.path.isfile("MANIFEST"):
    os.unlink("MANIFEST")

verpat = re.compile("VERSION *= *\"(.*)\"")
data = open("smart/const.py").read()
m = verpat.search(data)
if not m:
    sys.exit("error: can't find VERSION")
VERSION = m.group(1)

# Make distutils copy smart.py to smart.
copy_file_orig = distutils.file_util.copy_file
copy_tree_orig = distutils.dir_util.copy_tree
def copy_file(src, dst, *args, **kwargs):
    if dst.endswith("bin/smart.py"):
        dst = dst[:-3]
    return copy_file_orig(src, dst, *args, **kwargs)
def copy_tree(*args, **kwargs):
    outputs = copy_tree_orig(*args, **kwargs)
    for i in range(len(outputs)):
        if outputs[i].endswith("bin/smart.py"):
            outputs[i] = outputs[i][:-3]
    return outputs
distutils.file_util.copy_file = copy_file
distutils.dir_util.copy_tree = copy_tree

# Some Python sysconfig use different directories for different prefixes
EXEC_PREFIX = get_config_var('exec_prefix')
PYTHONLIB = get_python_lib(plat_specific=1, standard_lib=0,
                           prefix=EXEC_PREFIX).replace(EXEC_PREFIX+os.sep, "")

config_h = sysconfig.get_config_h_filename()
config_h_vars = sysconfig.parse_config_h(open(config_h))

ext_modules = [
               Extension("smart.ccache", ["smart/ccache.c"]),
               Extension("smart.backends.rpm.crpmver",
                         ["smart/backends/rpm/crpmver.c"]),
               Extension("smart.backends.deb.cdebver",
                         ["smart/backends/deb/cdebver.c"]),
               Extension("smart.util.ctagfile",
                         ["smart/util/ctagfile.c"]),
               Extension("smart.util.cdistance",
                         ["smart/util/cdistance.c"])
              ]

packages = [
            "smart",
            "smart.backends",
            "smart.backends.rpm",
            "smart.backends.deb",
            "smart.backends.slack",
            "smart.backends.arch",
            "smart.channels",
            "smart.commands",
            "smart.interfaces",
            "smart.interfaces.gtk",
            "smart.interfaces.text",
            "smart.interfaces.qt",
            "smart.interfaces.qt4",
            "smart.interfaces.images",
            "smart.plugins",
            "smart.util"
           ]
                    
try:
    import cElementTree
except ImportError:
    try:
        from xml.etree import cElementTree
    except ImportError:
        # we need to build in-tree cElementTree
        # cElementTree needed defines
        CET_DEFINES = [
            ("XML_STATIC", None),
            ("XML_NS", "1"),
            ("XML_DTD", "1"),
            ("XML_CONTEXT_BYTES", "1024")
            ]
        
        if "HAVE_MEMMOVE" in config_h_vars:
            CET_DEFINES.append(("HAVE_MEMMOVE", "1"))
        if "HAVE_BCOPY" in config_h_vars:
            CET_DEFINES.append(("HAVE_BCOPY", "1"))
        if sys.byteorder == "little":
            CET_DEFINES.append(("BYTEORDER", "1234"))
        else:
            CET_DEFINES.append(("BYTEORDER", "4321"))

        ext_modules.append(
          Extension("smart.util.cElementTree",
                    ["smart/util/celementtree/cElementTree.c",
                     "smart/util/celementtree/expat/xmlparse.c",
                     "smart/util/celementtree/expat/xmlrole.c",
                     "smart/util/celementtree/expat/xmltok.c"],
                    include_dirs=["smart/util/celementtree/expat"],
                    define_macros=CET_DEFINES)
                   )
        packages.append("smart.util.elementtree")

try:
    from hashlib import sha256
except ImportError:
    ext_modules.append(
      Extension("smart.util.sha256",
                ["smart/util/sha256module.c"])
               )


setup(name="smart",
      version = VERSION,
      description = "Smart Package Manager is a next generation package "
                    "handling tool",
      author = "Gustavo Niemeyer",
      author_email = "gustavo@niemeyer.net",
      license = "GPL",
      url = "http://smartpm.org",
      long_description =
"""\
Smart Package Manager is a next generation package handling tool.
""",
      packages = packages,
      scripts = ["smart.py"],
      ext_modules = ext_modules,
      data_files = [(PYTHONLIB+"/smart/interfaces/images", 
                     glob.glob("smart/interfaces/images/*.png")),
                    ("share/man/man8/", glob.glob("doc/*.8"))
                   ],
      cmdclass={'install_data': InstallData}
      )

