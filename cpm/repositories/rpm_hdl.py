from cpm.backends.rpm.header import RPMHeaderListLoader
from cpm.repository import Repository
from cpm import *
import posixpath

class RPMHeaderListRepository(Repository):

    def __init__(self, node):
        Repository.__init__(self, node)
        
        self._hdlurl = None
        self._pkgurl = None

        for n in node.getchildren():
            if n.tag == "hdlurl":
                self._hdlurl = n.text
            elif n.tag == "pkgurl":
                self._pkgurl = n.text

        if not self._pkgurl:
            raise Error, "no pkgurl found in repository '%s'" % self._name
        elif not self._hdlurl:
            raise Error, "no hdlurl found in repository '%s'" % self._name

    def acquire(self, fetcher):
        filename = fetcher.get(self._hdlurl)
        if filename:
            self._loader = RPMHeaderListLoader(filename, self._pkgurl)

repository = RPMHeaderListRepository

# vim:ts=4:sw=4:et
