#!/usr/bin/python
from cpm.interfaces.gtk import getImage
from cpm.report import Report
import gobject, gtk

class GtkChanges:

    def __init__(self):

        self.window = gtk.Window()
        self.window.set_title("Transaction")
        self.window.set_modal(True)
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.set_geometry_hints(min_width=400, min_height=300)

        self.vbox = gtk.VBox()
        self.vbox.set_border_width(10)
        self.vbox.set_spacing(10)
        self.vbox.show()
        self.window.add(self.vbox)

        self.label = gtk.Label()
        self.vbox.pack_start(self.label, expand=False)

        self.scrollwin = gtk.ScrolledWindow()
        self.scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.scrollwin.set_shadow_type(gtk.SHADOW_IN)
        self.scrollwin.show()
        self.vbox.pack_start(self.scrollwin)

        self.treemodel = gtk.TreeStore(gobject.TYPE_OBJECT,
                                       gobject.TYPE_STRING)
        self.treeview = gtk.TreeView(self.treemodel)
        #self.treeview.set_property("fixed_height_mode", True)
        self.treeview.set_enable_search(True)
        self.treeview.set_search_column(1)
        def row_activated(tv, path, column):
            if tv.row_expanded(path):
                tv.collapse_row(path)
            else:
                tv.expand_row(path, False)
        self.treeview.connect("row-activated", row_activated)
        self.treeview.show()
        self.scrollwin.add(self.treeview)

        column = gtk.TreeViewColumn("Operations")
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, "pixbuf", 0)
        renderer = gtk.CellRendererText()
        renderer.set_fixed_height_from_font(True)
        column.pack_start(renderer, True)
        column.add_attribute(renderer, "text", 1)
        self.treeview.append_column(column)

        self.confirmbbox = gtk.HButtonBox()
        self.confirmbbox.set_spacing(10)
        self.confirmbbox.set_layout(gtk.BUTTONBOX_END)
        self.vbox.pack_start(self.confirmbbox, expand=False)

        self.okbutton = gtk.Button(stock="gtk-ok")
        self.okbutton.show()
        def clicked(x):
            self.result = True
            gtk.main_quit()
        self.okbutton.connect("clicked", clicked)
        self.confirmbbox.pack_start(self.okbutton)

        self.cancelbutton = gtk.Button(stock="gtk-cancel")
        self.cancelbutton.show()
        self.cancelbutton.connect("clicked", lambda x: gtk.main_quit())
        self.confirmbbox.pack_start(self.cancelbutton)

        self.closebbox = gtk.HButtonBox()
        self.closebbox.set_spacing(10)
        self.closebbox.set_layout(gtk.BUTTONBOX_END)
        self.vbox.pack_start(self.closebbox, expand=False)

        self.closebutton = gtk.Button(stock="gtk-close")
        self.closebutton.show()
        self.closebutton.connect("clicked", lambda x: gtk.main_quit())
        self.closebbox.pack_start(self.closebutton)

    def showChangeSet(self, cache, changeset, confirm=False, label=None):
        report = Report(cache, changeset)
        report.compute()

        self.treemodel.clear()
        
        ipixbuf = getImage("package-install").get_pixbuf()
        Ipixbuf = getImage("package-installed").get_pixbuf()
        rpixbuf = getImage("package-remove").get_pixbuf()
        upixbuf = getImage("package-upgrade").get_pixbuf()
        dpixbuf = getImage("package-downgrade").get_pixbuf()
        if report.install:
            iterlabel = "Install (%d)" % len(report.install)
            iiter = self.treemodel.append(None, (ipixbuf, iterlabel))
            lst = report.install.keys()
            lst.sort()
            for pkg in lst:
                iter = None
                if pkg in report.upgrading:
                    iter = self.treemodel.append(iiter, (upixbuf, str(pkg)))
                    for upgpkg in report.upgrading[pkg]:
                        if upgpkg in report.remove:
                            pixbuf = rpixbuf
                        else:
                            pixbuf = Ipixbuf
                        self.treemodel.append(iter, (pixbuf, str(upgpkg)))
                if pkg in report.downgrading:
                    if not iter:
                        iter = self.treemodel.append(iiter, (dpixbuf, str(pkg)))
                    for dwnpkg in report.downgrading[pkg]:
                        if dwnpkg in report.remove:
                            pixbuf = rpixbuf
                        else:
                            pixbuf = Ipixbuf
                        self.treemodel.append(iter, (pixbuf, str(dwnpkg)))
                if not iter:
                    self.treemodel.append(iiter, (ipixbuf, str(pkg)))

        if report.remove:
            iterlabel = "Remove (%d)" % len(report.remove)
            riter = self.treemodel.append(None, (rpixbuf, iterlabel))
            lst = report.remove.keys()
            lst.sort()
            for pkg in lst:
                iter = self.treemodel.append(riter, (rpixbuf, str(pkg)))
                if pkg in report.upgraded:
                    for upgpkg in report.upgraded[pkg]:
                        self.treemodel.append(iter, (upixbuf, str(upgpkg)))
                if pkg in report.downgraded:
                    for dwnpkg in report.downgraded[pkg]:
                        self.treemodel.append(iter, (dpixbuf, str(dwnpkg)))

        if confirm:
            self.confirmbbox.show()
            self.closebbox.hide()
        else:
            self.closebbox.show()
            self.confirmbbox.hide()

        if label:
            self.label.set_text(label)
            self.label.show()
        else:
            self.label.hide()

        self.treeview.queue_draw()

        self.result = False
        self.window.show()
        gtk.main()
        self.window.hide()

        return self.result

# vim:ts=4:sw=4:et
