#!/usr/bin/python
from cpm.interfaces.gtk import getImage
import gobject, gtk

class GtkPackageView:

    def __init__(self):
        self._scrollwin = gtk.ScrolledWindow()
        self._scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self._scrollwin.set_shadow_type(gtk.SHADOW_IN)
        self._scrollwin.show()

        self._treemodel = gtk.TreeStore(gobject.TYPE_PYOBJECT,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_OBJECT,
                                        gobject.TYPE_STRING)
        self._treeview = gtk.TreeView(self._treemodel)
        self._treeview.set_headers_visible(False)
        self._treeview.show()
        self._scrollwin.add(self._treeview)

        column = gtk.TreeViewColumn("Packages")
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, "pixbuf", 1)
        renderer = gtk.CellRendererText()
        renderer.set_fixed_height_from_font(True)
        column.pack_start(renderer, True)
        column.add_attribute(renderer, "text", 2)
        self._treeview.append_column(column)

        self._ipixbuf = getImage("package-install").get_pixbuf()
        self._Ipixbuf = getImage("package-installed").get_pixbuf()
        self._apixbuf = getImage("package-available").get_pixbuf()
        #rpixbuf = getImage("package-remove").get_pixbuf()
        #upixbuf = getImage("package-upgrade").get_pixbuf()
        #dpixbuf = getImage("package-downgrade").get_pixbuf()

    def getScrolledWindow(self):
        return self._scrollwin

    def getTreeView(self):
        return self._treeview

    def getTreeModel(self):
        return self._treemodel

    def setPackages(self, packages):
        if isinstance(packages, list):
            model = gtk.ListStore(gobject.TYPE_PYOBJECT,
                                  gobject.TYPE_OBJECT,
                                  gobject.TYPE_STRING)
        elif isinstance(packages, dict):
            model = gtk.TreeStore(gobject.TYPE_PYOBJECT,
                                  gobject.TYPE_OBJECT,
                                  gobject.TYPE_STRING)
        self._treeview.set_model(model)
        self._setPackage(None, model, None, packages)
        self._treeview.queue_draw()

    def _setPackage(self, report, model, parent, item):
        if type(item) is list:
            item.sort()
            for subitem in item:
                self._setPackage(report, model, parent, subitem)
        elif type(item) is dict:
            keys = item.keys()
            keys.sort()
            for key in keys:
                iter = self._setPackage(report, model, parent, key)
                self._setPackage(report, model, iter, item[key])
        else:
            iter = model.append(parent)
            if type(item) is str:
                model.set(iter, 2, item)
            else:
                pixbuf = item.installed and self._Ipixbuf or self._apixbuf
                model.set(iter, 0, item, 1, pixbuf, 2, str(item))
            return iter

# vim:ts=4:sw=4:et
