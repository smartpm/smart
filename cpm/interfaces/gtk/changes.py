#!/usr/bin/python
from cpm.interfaces.gtk import getImage
from cpm.report import Report
import gobject, gtk

class GtkChanges:

    def __init__(self):

        self._window = gtk.Window()
        self._window.set_title("Transaction")
        self._window.set_modal(True)
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=400, min_height=300)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self._window.add(self._vbox)

        self._label = gtk.Label()
        self._vbox.pack_start(self._label, expand=False)

        self._scrollwin = gtk.ScrolledWindow()
        self._scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self._scrollwin.set_shadow_type(gtk.SHADOW_IN)
        self._scrollwin.show()
        self._vbox.pack_start(self._scrollwin)

        self._treemodel = gtk.TreeStore(gobject.TYPE_OBJECT,
                                        gobject.TYPE_STRING)
        self._treeview = gtk.TreeView(self._treemodel)
        #self._treeview.set_property("fixed_height_mode", True)
        self._treeview.set_enable_search(True)
        self._treeview.set_search_column(1)
        def row_activated(tv, path, column):
            if tv.row_expanded(path):
                tv.collapse_row(path)
            else:
                tv.expand_row(path, False)
        self._treeview.connect("row-activated", row_activated)
        self._treeview.show()
        self._scrollwin.add(self._treeview)

        column = gtk.TreeViewColumn("Operations")
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, "pixbuf", 0)
        renderer = gtk.CellRendererText()
        renderer.set_fixed_height_from_font(True)
        column.pack_start(renderer, True)
        column.add_attribute(renderer, "text", 1)
        self._treeview.append_column(column)

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

    def showChangeSet(self, cache, changeset, confirm=False, label=None):
        report = Report(cache, changeset)
        report.compute()

        self._treemodel.clear()
        
        ipixbuf = getImage("package-install").get_pixbuf()
        Ipixbuf = getImage("package-installed").get_pixbuf()
        rpixbuf = getImage("package-remove").get_pixbuf()
        upixbuf = getImage("package-upgrade").get_pixbuf()
        dpixbuf = getImage("package-downgrade").get_pixbuf()
        if report.install:
            iterlabel = "Install (%d)" % len(report.install)
            iiter = self._treemodel.append(None, (ipixbuf, iterlabel))
            lst = report.install.keys()
            lst.sort()
            for pkg in lst:
                iter = None
                if pkg in report.upgrading:
                    iter = self._treemodel.append(iiter, (upixbuf, str(pkg)))
                    for upgpkg in report.upgrading[pkg]:
                        if upgpkg in report.remove:
                            pixbuf = rpixbuf
                        else:
                            pixbuf = Ipixbuf
                        self._treemodel.append(iter, (pixbuf, str(upgpkg)))
                if pkg in report.downgrading:
                    if not iter:
                        iter = self._treemodel.append(iiter,
                                                      (dpixbuf, str(pkg)))
                    for dwnpkg in report.downgrading[pkg]:
                        if dwnpkg in report.remove:
                            pixbuf = rpixbuf
                        else:
                            pixbuf = Ipixbuf
                        self._treemodel.append(iter, (pixbuf, str(dwnpkg)))
                if not iter:
                    self._treemodel.append(iiter, (ipixbuf, str(pkg)))

        if report.remove:
            iterlabel = "Remove (%d)" % len(report.remove)
            riter = self._treemodel.append(None, (rpixbuf, iterlabel))
            lst = report.remove.keys()
            lst.sort()
            for pkg in lst:
                iter = self.treemodel.append(riter, (rpixbuf, str(pkg)))
                if pkg in report.upgraded:
                    for upgpkg in report.upgraded[pkg]:
                        self._treemodel.append(iter, (upixbuf, str(upgpkg)))
                if pkg in report.downgraded:
                    for dwnpkg in report.downgraded[pkg]:
                        self._treemodel.append(iter, (dpixbuf, str(dwnpkg)))

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

        self._treeview.queue_draw()

        self._result = False
        self._window.show()
        gtk.main()
        self._window.hide()

        return self._result

# vim:ts=4:sw=4:et
