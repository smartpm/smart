from cpm.pm import PackageManager
from cpm import *
import sys, os
import rpm

class RPMPackageManager(PackageManager):

    def commit(self, install, remove, pkgpath):

        prog = self.getProgress()
        prog.setTopic("Committing transaction...")

        # Build obsoletes relations.
        obsoleting = {}
        obsoleted = {}
        for pkg in set:
            for prv in pkg.provides:
                for obs in prv.obsoletedby:
                    for obspkg in obs.packages:
                        if set.get(obspkg) is INSTALL:
                            obsoleted[pkg] = True
                            obsoleting[obspkg] = True

        ts = rpm.ts()
        packages = 0
        for pkg in install:
            loader = [x for x in pkg.loaderinfo if not x.getInstalled()][0]
            info = loader.getInfo(pkg)
            mode = pkg in obsoleting and "u" or "i"
            path = pkgpath[pkg]
            fd = os.open(path, os.O_RDONLY)
            h = ts.hdrFromFdno(fd)
            os.close(fd)
            ts.addInstall(h, (info, path), mode)
            packages += 1
        for pkg in remove:
            if pkg not in obsoleted:
                version = pkg.version
                if ":" in version:
                    version = version[version.find(":")+1:]
                ts.addErase("%s-%s" % (pkg.name, version))
        ts.order()
        prog.set(0, packages)
        cb = RPMCallback(prog)
        ts.run(cb, None)

class RPMCallback:
    def __init__(self, prog):
        self.data = {"item-number": 0}
        self.prog = prog
        self.fd = None

    def __call__(self, what, amount, total, infopath, data):

        if what == rpm.RPMCALLBACK_INST_OPEN_FILE:
            info, path = infopath
            self.fd = os.open(path, os.O_RDONLY)
            return self.fd
        
        elif what == rpm.RPMCALLBACK_INST_CLOSE_FILE:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None

        elif what == rpm.RPMCALLBACK_INST_START:
            info, path = infopath
            self.data["item-number"] += 1
            self.prog.add(1)
            self.prog.setSubTopic(infopath, info.getPackage().name)
            self.prog.setSub(info, 0, 1, subdata=self.data)

        elif (what == rpm.RPMCALLBACK_TRANS_PROGRESS or
              what == rpm.RPMCALLBACK_INST_PROGRESS):
            self.prog.setSub(infopath, amount, total, subdata=self.data)
            self.prog.show()

        elif what == rpm.RPMCALLBACK_TRANS_START:
            self.prog.setSubTopic(infopath, "Preparing...")
            self.prog.setSub(infopath, 0, 1)
            self.prog.show()

        elif what == rpm.RPMCALLBACK_TRANS_STOP:
            self.prog.setSubDone(infopath)
            self.prog.show()

