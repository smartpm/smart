#from cpm.backends.rpm.rpmver import splitarch
from cpm.backends.rpm.crpmver import splitarch
from cpm.pm import PackageManager
from cpm import *
import sys, os
import rpm

class RPMPackageManager(PackageManager):

    def commit(self, install, remove, pkgpath):

        prog = self.getProgress()
        prog.start(True)
        prog.setTopic("Committing transaction...")
        prog.show()

        # Compute upgrading/upgraded packages
        upgrading = {}
        upgraded = {}
        for pkg in install:
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    upgd = []
                    for prvpkg in prv.packages:
                        if prvpkg.installed:
                            if prvpkg not in remove:
                                break
                            upgd.append(prvpkg)
                    else:
                        if upgd:
                            upgrading[pkg] = True
                            upgraded.update(dict.fromkeys(upgd))
        ts = rpm.ts()
        packages = 0
        for pkg in install:
            loader = [x for x in pkg.loaderinfo if not x.getInstalled()][0]
            info = loader.getInfo(pkg)
            mode = pkg in upgrading and "u" or "i"
            path = pkgpath[pkg]
            fd = os.open(path, os.O_RDONLY)
            h = ts.hdrFromFdno(fd)
            os.close(fd)
            ts.addInstall(h, (info, path), mode)
            packages += 1
        for pkg in remove:
            if pkg not in upgraded:
                version = pkg.version
                if ":" in version:
                    version = version[version.find(":")+1:]
                version, arch = splitarch(version)
                ts.addErase("%s-%s" % (pkg.name, version))
        probs = ts.check()
        if probs:
            problines = []
            for prob in probs:
                name1 = "%s-%s-%s" % prob[0]
                name2, version = prob[1]
                if version:
                    sense = prob[2]
                    name2 += " "
                    if sense & rpm.RPMSENSE_LESS:
                        name2 += "<"
                    elif sense & rpm.RPMSENSE_GREATER:
                        name2 += ">"
                    if sense & rpm.RPMSENSE_EQUAL:
                        name2 += "="
                    name2 += " "
                    name2 += version
                if prob[4] & rpm.RPMDEP_SENSE_REQUIRES:
                    line = "%s is required by %s" % (name1, name2)
                else:
                    line = "%s conflicts with %s" % (name1, name2)
                problines.append(line)
            raise Error, "\n".join(problines)
        ts.order()
        ts.setProbFilter(0)
        prog.set(0, packages or 1)
        cb = RPMCallback(prog)
        probs = ts.run(cb, None)
        prog.setDone()
        if probs:
            raise Error, "\n".join([x[0] for x in probs])
        prog.stop()

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

# vim:ts=4:sw=4:et
