
class Sorter(object):
    def __init__(self, lst):
        self._list = lst

    def cmp(self, pkg1, pkg2):
        if self._primary:
            return self._primary.cmp(pkg1, pkg2)
        return 0

    def sort(self, lst=None):
        if not lst:
            lst = self._list
        lst.sort(self.cmp)
        return lst

class ObsoletesSorter(Sorter):
    def __init__(self, lst):
        Sorter.__init__(self, lst)

        obspkgs = {}
        robs = recursiveObsoletes
        for pkg in lst:
            dct = {}
            robs(pkg, dct)
            obspkgs[pkg] = dct

        self._obspkgs = obspkgs

    def sort(self, lst=None):
        if not lst:
            lst = self._list
        mylst = []
        for pkg in lst:
            obspkgs = self._obspkgs[pkg]
            for i in range(len(mylst)):
                if mylst[i] in obspkgs:
                    mylst.insert(i, pkg)
                    break
            else:
                mylst.append(pkg)
        lst[:] = mylst
        return lst

class RequireNumSorter(Sorter):
    def __init__(self, lst):
        Sorter.__init__(self, lst)

        reqpkgs = {}
        rreqby = recursiveRequiredBy
        for pkg in lst:
            dct = {}
            rreqby(pkg, dct)
            reqpkgs[pkg] = len(dct)

        self._reqpkgs = reqpkgs

    def cmp(self, pkg1, pkg2):
        return -cmp(self._reqpkgs[pkg1], self._reqpkgs[pkg2])

class UpgradeSorter(Sorter):
    def __init__(self, lst):
        Sorter.__init__(self, lst)
        self._reqnsrtr = RequireNumSorter(lst)
        self._obssrtr = ObsoletesSorter(lst)

    def sort(self, lst=None):
        if not lst:
            lst = self._list
        self._reqnsrtr.sort(lst)
        self._obssrtr.sort(lst)
        return lst

def recursiveRequiredBy(pkg, set):
    set[pkg] = True
    for prv in pkg.provides:
        for req in prv.requiredby:
            for reqpkg in req.packages:
                if reqpkg not in set:
                    recursiveRequiredBy(reqpkg, set)

def recursiveObsoletes(pkg, set):
    set[pkg] = True
    for obs in pkg.obsoletes:
        for prv in obs.providedby:
            for prvpkg in prv.packages:
                if prvpkg not in set:
                    recursiveObsoletes(prvpkg, set)

# vim:ts=4:sw=4:et
