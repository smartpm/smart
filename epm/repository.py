
class Repository:

    def __init__(self, node):
        self._node = node
        self._loader = None

        self._name = node.get("name")
        if not self._name:
            raise Error, "unnamed repository"

    def getName(self):
        return self._name

    def getLoader(self):
        return self._loader

    def acquire(self, fetcher):
        pass

# vim:ts=4:sw=4:et
