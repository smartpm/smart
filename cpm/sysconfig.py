from cpm.util.elementtree import ElementTree
from cpm.repository import createRepository
from cpm.packageflags import PackageFlags
from cpm.const import DATADIR
from cpm import *
import cPickle
import os

class SysConfig:

    def __init__(self):
        self._map = {}
        self.set("data-dir", os.path.expanduser(DATADIR))

    def getMap(self):
        return self._map

    def load(self, filepath):
        filepath = os.path.expanduser(filepath)
        if not os.path.isfile(filepath):
            raise Error, "file not found: %s" % filepath
        file = open(filepath)
        self._map.clear()
        try:
            self._map.update(cPickle.load(file))
        except:
            if os.path.isfile(filepath+".old"):
                file.close()
                file = open(filepath+".old")
                self._map.update(cPickle.load(file))
        file.close()

        if "data-dir" not in self._map:
            self.set("data-dir", os.path.expanduser(DATADIR))

    def save(self, filepath):
        filepath = os.path.expanduser(filepath)
        if os.path.isfile(filepath):
            os.rename(filepath, filepath+".old")
        file = open(filepath, "w")
        cPickle.dump(self._map, file, 2)
        file.close()

    def get(self, option, default=None, setdefault=False):
        if setdefault:
            return self._map.setdefault(option, default)
        else:
            return self._map.get(option, default)

    def set(self, option, value):
        self._map[option] = value

    def remove(self, option):
        if option in self._map:
            self._map[option]

# vim:ts=4:sw=4:et
