#from cpm.backends.rpm.rpmver import splitarch
from cpm.backends.rpm.crpmver import splitarch
from cpm.pm import PackageManager
from cpm import *
import sys, os
import errno
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
        cb.grabOutput(True)
        probs = ts.run(cb, None)
        cb.grabOutput(False)
        prog.setDone()
        if probs:
            raise Error, "\n".join([x[0] for x in probs])
        prog.stop()

class RPMCallback:
    def __init__(self, prog):
        self.data = {"item-number": 0}
        self.prog = prog
        self.fd = None
        self.rpmout = None

    def grabOutput(self, flag):
        if flag:
            if not self.rpmout:
                # Grab rpm output, but not the python one.
                sys.stdout = os.fdopen(os.dup(1), "w")
                sys.stderr = os.fdopen(os.dup(2), "w")
                self.stdout = sys.stdout
                self.stderr = sys.stderr
                pipe = os.pipe()
                os.dup2(pipe[1], 1)
                os.dup2(pipe[1], 2)
                os.close(pipe[1])
                self.rpmout = pipe[0]
                import fcntl
                flags = fcntl.fcntl(self.rpmout, fcntl.F_GETFL, 0)
                flags |= os.O_NONBLOCK
                fcntl.fcntl(self.rpmout, fcntl.F_SETFL, flags)
        else:
            if self.rpmout:
                self._rpmout()
                os.dup2(sys.stdout.fileno(), 1)
                os.dup2(sys.stderr.fileno(), 2)
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = self.stdout
                sys.stderr = self.stderr
                del self.stdout
                del self.stderr
                os.close(self.rpmout)
                self.rpmout = None

    def _rpmout(self):
        if self.rpmout:
            try:
                output = os.read(self.rpmout, 8192)
            except OSError, e:
                if e[0] != errno.EWOULDBLOCK:
                    raise
            else:
                if output:
                    logger.info(output)

    def __call__(self, what, amount, total, infopath, data):

        self._rpmout()

        if what == rpm.RPMCALLBACK_INST_OPEN_FILE:
            info, path = infopath
            logger.debug("processing %s in %s" % (info.getPackage(), path))
            self.fd = os.open(path, os.O_RDONLY)
            return self.fd
        
        elif what == rpm.RPMCALLBACK_INST_CLOSE_FILE:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None

        elif what == rpm.RPMCALLBACK_INST_START:
            info, path = infopath
            pkg = info.getPackage()
            self.data["item-number"] += 1
            self.prog.add(1)
            self.prog.setSubTopic(infopath, pkg.name)
            self.prog.setSub(infopath, 0, 1, subdata=self.data)
            self.prog.show()

        elif (what == rpm.RPMCALLBACK_TRANS_PROGRESS or
              what == rpm.RPMCALLBACK_INST_PROGRESS):
            self.prog.setSub(infopath or "trans", amount, total,
                             subdata=self.data)
            self.prog.show()

        elif what == rpm.RPMCALLBACK_TRANS_START:
            self.prog.setSubTopic("trans", "Preparing...")
            self.prog.setSub("trans", 0, 1)
            self.prog.show()

        elif what == rpm.RPMCALLBACK_TRANS_STOP:
            self.prog.setSubDone("trans")
            self.prog.show()

# vim:ts=4:sw=4:et
