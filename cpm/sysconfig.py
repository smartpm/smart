from cpm.elementtree import ElementTree
from cpm.repository import createRepository
from cpm import *
import os

# Important options:
# - repositories
# - package flags
# - package manager options
# - logging options

class SysConfig:

    def __init__(self, options=None):
        if options:
            self._data = options.copy()
        else:
            self._data = {}

    def load(self):
        pass

    def get(self, option, default=None):
        return self._data.get(option, default)

    def set(self, option, value):
        self._data[option] = value

    def append(self, option, value):
        oldvalue = self._data.get(option)
        if oldvalue:
            if type(oldvalue) is list:
                oldvalue.append(value)
            else:
                self._data[option] = [value, oldvalue]
        else:
            self._data[option] = [value]

class XMLSysConfig(SysConfig):

    CONFIG = [
        ("~/.cpm/config", "~/.cpm/"),
        ("/etc/cpm.conf", "/var/state/cpm/"),
    ]

    def load(self):
        root = None
        conffile = self.get("config-file")
        if conffile:
            conffile = os.path.expanduser(conffile)
            if not os.path.isfile(conffile):
                raise Error, "configuration file not found: %s" % conffile
            root = ElementTree.parse(opts.conffile).getroot()
        else:
            for conffile, datadir in self.CONFIG:
                conffile = os.path.expanduser(conffile)
                if os.path.isfile(conffile):
                    root = ElementTree.parse(conffile).getroot()
                    if not self.get("data-dir"):
                        datadir = os.path.expanduser(datadir)
                        self.set("data-dir", datadir)
                    break
            else:
                raise Error, "no configuration file found in: " + \
                             ", ".join([x[0] for x in self.CONFIG])

        repositories = []
        names = {}
        for node in root.getchildren():
            if node.tag == "repositories":
                for node in node.getchildren():
                    type = node.get("type")
                    if not type:
                        raise Error, "repository without type in %s" % conffile
                    repos = createRepository(type, node)
                    name = repos.getName()
                    if names.get(name):
                        raise Error, "'%s' is not a unique repository name" % \
                                     name
                    else:
                        names[name] = True
                    repositories.append(repos)

        self.set("repositories", repositories)

# vim:ts=4:sw=4:et
