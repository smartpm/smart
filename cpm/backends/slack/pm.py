from cpm.pm import PackageManager
from cpm import *
import commands

class SlackPackageManager(PackageManager):

    def commit(self, install, remove, pkgpath):

        prog = iface.getProgress(self, True)
        prog.start()
        prog.setTopic("Committing transaction...")
        prog.show()

        # Split out upgrades
        upgrade = []
        for pkg in install[:]:
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    for prvpkg in prv.packages:
                        if prvpkg.installed:
                            if prvpkg in remove:
                                remove.remove(prvpkg)
                            if pkg in install:
                                install.remove(pkg)
                            if pkg not in upgrade:
                                upgrade.append(pkg)

        total = len(install)+len(upgrade)+len(remove)
        prog.set(0, total)

        for pkg in install:
            prog.setSubTopic(pkg, "I:%s" % pkg.name)
            prog.setSub(pkg, 0, 1, 1)
            prog.show()
            status, output = commands.getstatusoutput("installpkg %s" %
                                                      pkgpath[pkg])
            prog.setSubDone(pkg)
            prog.show()
            if status != 0:
                iface.warning("Got status %d installing %s:" % (status, pkg))
                iface.warning(output)
            else:
                iface.debug("Installing %s:" % pkg)
                iface.debug(output)
        for pkg in upgrade:
            prog.setSubTopic(pkg, "U:%s" % pkg.name)
            prog.setSub(pkg, 0, 1, 1)
            prog.show()
            status, output = commands.getstatusoutput("upgradepkg %s" %
                                                      pkgpath[pkg])
            prog.setSubDone(pkg)
            prog.show()
            if status != 0:
                iface.warning("Got status %d upgrading %s:" % (status, pkg))
                iface.warning(output)
            else:
                iface.debug("Upgrading %s:" % pkg)
                iface.debug(output)
        for pkg in remove:
            prog.setSubTopic(pkg, "R:%s" % pkg.name)
            prog.setSub(pkg, 0, 1, 1)
            prog.show()
            status, output = commands.getstatusoutput("removepkg %s" %
                                                      pkg.name)
            prog.setSubDone(pkg)
            prog.show()
            if status != 0:
                iface.warning("Got status %d removing %s:" % (status, pkg))
                iface.warning(output)
            else:
                iface.debug("Removing %s:" % pkg)
                iface.debug(output)

        prog.setDone()
        prog.stop()

# vim:ts=4:sw=4:et
