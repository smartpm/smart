#!/usr/bin/python
from cpm.interfaces.gtk.packageview import GtkPackageView
from cpm.interfaces.gtk import getPixbuf
from cpm.report import Report
import gobject, gtk

class GtkChanges:

    def __init__(self):

        self._window = gtk.Window()
        self._window.set_title("Transaction")
        self._window.set_modal(True)
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=600, min_height=400)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self._window.add(self._vbox)

        self._label = gtk.Label()
        self._vbox.pack_start(self._label, expand=False)

        self._pv = GtkPackageView()
        self._pv.getTreeView().set_headers_visible(False)
        self._pv.setExpandPackage(True)
        self._pv.show()
        self._vbox.pack_start(self._pv)

        self._confirmbbox = gtk.HButtonBox()
        self._confirmbbox.set_spacing(10)
        self._confirmbbox.set_layout(gtk.BUTTONBOX_END)
        self._vbox.pack_start(self._confirmbbox, expand=False)

        self._okbutton = gtk.Button(stock="gtk-ok")
        self._okbutton.show()
        def clicked(x):
            self._result = True
            gtk.main_quit()
        self._okbutton.connect("clicked", clicked)
        self._confirmbbox.pack_start(self._okbutton)

        self._cancelbutton = gtk.Button(stock="gtk-cancel")
        self._cancelbutton.show()
        self._cancelbutton.connect("clicked", lambda x: gtk.main_quit())
        self._confirmbbox.pack_start(self._cancelbutton)

        self._closebbox = gtk.HButtonBox()
        self._closebbox.set_spacing(10)
        self._closebbox.set_layout(gtk.BUTTONBOX_END)
        self._vbox.pack_start(self._closebbox, expand=False)

        self._closebutton = gtk.Button(stock="gtk-close")
        self._closebutton.show()
        self._closebutton.connect("clicked", lambda x: gtk.main_quit())
        self._closebbox.pack_start(self._closebutton)

    def showChangeSet(self, changeset, keep=None, confirm=False, label=None):

        report = Report(changeset)
        report.compute()
        
        packages = {}

        if report.install:
            install = {}
            lst = report.install.keys()
            lst.sort()
            for pkg in lst:
                package = {}
                done = {}
                if pkg in report.upgrading:
                    for upgpkg in report.upgrading[pkg]:
                        package.setdefault("Upgrades", []).append(upgpkg)
                        done[upgpkg] = True
                if pkg in report.downgrading:
                    for dwnpkg in report.downgrading[pkg]:
                        package.setdefault("Downgrades", []).append(dwnpkg)
                        done[dwnpkg] = True
                if pkg in report.conflicts:
                    for cnfpkg in report.conflicts[pkg]:
                        if cnfpkg in done:
                            continue
                        package.setdefault("Conflicts", []).append(cnfpkg)
                install[pkg] = package
            packages["Install (%d)" % len(report.install)] = install

        if report.remove:
            remove = {}
            lst = report.remove.keys()
            lst.sort()
            for pkg in lst:
                package = {}
                done = {}
                if pkg in report.upgraded:
                    for upgpkg in report.upgraded[pkg]:
                        package.setdefault("Upgraded By", []).append(upgpkg)
                        done[upgpkg] = True
                if pkg in report.downgraded:
                    for dwnpkg in report.downgraded[pkg]:
                        package.setdefault("Downgraded By", []).append(upgpkg)
                        done[dwnpkg] = True
                if pkg in report.conflicts:
                    for cnfpkg in report.conflicts[pkg]:
                        if cnfpkg in done:
                            continue
                        package.setdefault("Conflicts", []).append(cnfpkg)
                remove[pkg] = package
            packages["Remove (%d)" % len(report.remove)] = remove

        if keep:
            packages["Keep (%d)" % len(keep)] = keep

        if confirm:
            self._confirmbbox.show()
            self._closebbox.hide()
        else:
            self._closebbox.show()
            self._confirmbbox.hide()

        if label:
            self._label.set_text(label)
            self._label.show()
        else:
            self._label.hide()

        self._pv.setPackages(packages, changeset)

        # Expand first level
        treeview = self._pv.getTreeView()
        treemodel = treeview.get_model()
        child = treemodel.iter_children(None)
        while child:
            path = treemodel.get_path(child)
            treeview.expand_row(path, False)
            child = treemodel.iter_next(child)

        self._result = False
        self._window.show()
        gtk.main()
        self._window.hide()

        return self._result

# vim:ts=4:sw=4:et
