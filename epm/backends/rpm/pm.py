from epm.backends.rpm import RPMPackage
from epm.pm import PackageManager
from epm.transaction import *
from epm import *

import sys, os
import rpm

class RPMPackageManager(PackageManager):

    def commit(self, trans, prog):
        set = trans.getChangeSet().getSet()

        # Build obsoletes relations.
        obsoleting = {}
        obsoleted = {}
        for pkg in set:
            if not isinstance(pkg, RPMPackage):
                continue
            for prv in pkg.provides:
                for obs in prv.obsoletedby:
                    for obspkg in obs.packages:
                        if set.get(obspkg) is INSTALL:
                            obsoleted[pkg] = True
                            obsoleting[obspkg] = True

        ts = rpm.ts()
        packages = 0
        for pkg in set:
            if not isinstance(pkg, RPMPackage):
                continue
            op = set[pkg]
            if op is INSTALL:
                loader = [x for x in pkg.loaderinfo if not x.getInstalled()][0]
                info = loader.getInfo(pkg)
                mode = pkg in obsoleting and "u" or "i"
                url = info.getURL()
                if not url.startswith("file://"):
                    raise Error, "Ooops.. not yet supported."
                fd = os.open(url[7:], os.O_RDONLY)
                h = ts.hdrFromFdno(fd)
                os.close(fd)
                ts.addInstall(h, info, mode)
                packages += 1
            elif pkg not in obsoleted:
                version = pkg.version
                if ":" in version:
                    version = version[version.find(":")+1:]
                ts.addErase("%s-%s" % (pkg.name, version))
        ts.order()
        prog.setTotal(packages)
        cb = RPMStandardCallback(prog)
        ts.run(cb, None)

class RPMStandardCallback:
    def __init__(self, prog):
        self.prog = prog
        self.current = 0
        self.fd = None

    def __call__(self, what, amount, total, info, data):

        if what == rpm.RPMCALLBACK_INST_OPEN_FILE:
            url = info.getURL()
            if not url.startswith("file://"):
                raise Error, "Ooops.. not yet supported."
            filename = url[7:]
            self.fd = os.open(filename, os.O_RDONLY)
            return self.fd
        
        elif what == rpm.RPMCALLBACK_INST_CLOSE_FILE:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None

        elif what == rpm.RPMCALLBACK_INST_START:
            self.current += 1
            self.prog.setTopic(info.getPackage().name)
            self.prog.setCurrent(self.current)
            self.prog.setData("item-number", self.current)

        elif (what == rpm.RPMCALLBACK_TRANS_PROGRESS or
              what == rpm.RPMCALLBACK_INST_PROGRESS):
            self.prog.setSubTotal(total)
            self.prog.setSubCurrent(amount)
            self.prog.show()

        elif what == rpm.RPMCALLBACK_TRANS_START:
            self.prog.setSubTotal(1)
            self.prog.setTopic("Preparing...")
            self.prog.show()

        elif what == rpm.RPMCALLBACK_TRANS_STOP:
            self.prog.setSubDone()
            self.prog.show()

