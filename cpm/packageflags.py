
class PackageFlags(object):

    _matchers = {}

    def __init__(self, map):
        self._map = map
    
    def add(self, flag, name, version=None, relation=None):
        names = self._map.get(flag)
        if names:
            lst = names.get(name)
            if lst:
                lst.append((relation, version))
            else:
                names[name] = [(relation, version)]
        else:
            self._map[flag] = {name: [(relation, version)]}

    def test(self, flag, pkg):
        names = self._map.get(flag)
        if names:
            lst = names.get(pkg.name)
            if lst:
                for item in lst:
                    if pkg.matches(*item):
                        return True
        return False

    def filter(self, flag, pkgs):
        fpkgs = []
        names = self._map.get(flag)
        if names:
            for pkg in pkgs:
                lst = names.get(pkg.name)
                if lst:
                    for item in lst:
                        if pkg.matches(*item):
                            fpkgs.append(pkg)
                            break
        return fpkgs

# vim:ts=4:sw=4:et
