from cpm.const import DATADIR, INFO
from cpm import *
import cPickle
import os

class SysConfig:

    def __init__(self):
        self._map = {}
        self._weakmap = {}
        self._softmap = {}
        self.set("log-level", INFO, weak=True)
        self.set("data-dir", os.path.expanduser(DATADIR), weak=True)

    def getMap(self):
        return self._map

    def getWeakMap(self):
        return self._weakmap

    def getSoftMap(self):
        return self._softmap

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

    def save(self, filepath):
        filepath = os.path.expanduser(filepath)
        if os.path.isfile(filepath):
            os.rename(filepath, filepath+".old")
        dirname = os.path.dirname(filepath)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        file = open(filepath, "w")
        cPickle.dump(self._map, file, 2)
        file.close()

    def get(self, option, default=None, setdefault=None):
        if setdefault is not None:
            return self._map.setdefault(option, setdefault)
        value = self._softmap.get(option)
        if value is None:
            value = self._map.get(option)
            if value is None:
                value = self._weakmap.get(option, default)
        return value

    def set(self, option, value, weak=False, soft=False):
        if soft:
            self._softmap[option] = value
        elif weak:
            self._weakmap[option] = value
        else:
            self._map[option] = value
            if option in self._softmap:
                del self._softmap[option]

    def remove(self, option):
        if option in self._map:
            del self._map[option]
        if option in self._weakmap:
            del self._weakmap[option]
        if option in self._softmap:
            del self._weakmap[option]

# vim:ts=4:sw=4:et
