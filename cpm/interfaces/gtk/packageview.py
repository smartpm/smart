#!/usr/bin/python
from cpm.interfaces.gtk import getImage
import gobject, gtk

class PackageViewCellRenderer(gtk.GenericCellRenderer):

    __gproperties__ = {
        "object":  (gobject.TYPE_PYOBJECT, "Object",
                    "Object to be shown",
                    gobject.PARAM_READWRITE),
        "spacing": (gobject.TYPE_INT, "Spacing",
                    "Internal spacing between objects", 0, 100, 5,
                    gobject.PARAM_READWRITE),
    }

    def __init__(self):
        self.__gobject_init__()
        self.object = None
        self.spacing = 5 
        self._ipixbuf = getImage("package-installed").get_pixbuf()
        self._apixbuf = getImage("package-available").get_pixbuf()

    def do_set_property(self, pspec, value):
        if pspec.name == "object":
            if type(value) is str:
                self._pixbuf = None
            else:
                if value.installed:
                    self._pixbuf = self._ipixbuf
                else:
                    self._pixbuf = self._apixbuf
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def on_render(self, window, widget, background_area,
                  cell_area, expose_area, flags):
        x_offset, y_offset, width, height = self.on_get_size(widget, cell_area)

        x = cell_area.x+x_offset
        y = cell_area.y+y_offset

        if self._pixbuf:
            pixbuf_width = self._pixbuf.get_width()
            pixbuf_height = self._pixbuf.get_height()
            pixbuf_y = y+(height-pixbuf_height)/2
            window.draw_pixbuf(widget.style.black_gc,
                               self._pixbuf, 0, 0, x, pixbuf_y,
                               pixbuf_width, pixbuf_height,
                               gtk.gdk.RGB_DITHER_NORMAL, 0, 0)
            x += pixbuf_width+self.spacing

        text = str(self.object)
        layout = widget.create_pango_layout(text)

        widget.style.paint_layout(window, gtk.STATE_NORMAL, True,
                                  expose_area, widget, "cellrenderertext",
                                  x, y, layout)

    def on_get_size(self, widget, cell_area):

        xpad = self.get_property("xpad")
        ypad = self.get_property("ypad")
        if cell_area:
            width = cell_area.width
            height = cell_area.height
            xalign = self.get_property("xalign")
            x_offset = int(xalign*(cell_area.width-width-2*xpad))
            x_offset = max(x_offset, 0) + xpad
            yalign = self.get_property("yalign")
            y_offset = int(yalign*(cell_area.height-height-2*ypad))
            y_offset = max(y_offset, 0) + ypad
        else:
            text = str(self.object)
            layout = widget.create_pango_layout(text)
            _, rect = layout.get_pixel_extents()
            width = rect[2]
            height = rect[3]
            width += xpad*2
            height += ypad*2
            if self._pixbuf:
                width += self._pixbuf.get_width()+self.spacing
            x_offset = 0
            y_offset = 0
        return x_offset, y_offset, width, height

gobject.type_register(PackageViewCellRenderer)

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
        self._treeview.set_rules_hint(True)
        self._treeview.show()
        self._scrollwin.add(self._treeview)

        column = gtk.TreeViewColumn("Packages")
        renderer = PackageViewCellRenderer()
        renderer.set_property("xpad", 5)
        column.pack_start(renderer, True)
        column.add_attribute(renderer, "object", 0)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self._treeview.append_column(column)

        #self._ipixbuf = getImage("package-install").get_pixbuf()
        #self._Ipixbuf = getImage("package-installed").get_pixbuf()
        #self._apixbuf = getImage("package-available").get_pixbuf()
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
            model = gtk.ListStore(gobject.TYPE_PYOBJECT)
        elif isinstance(packages, dict):
            model = gtk.TreeStore(gobject.TYPE_PYOBJECT)
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
            # On lists, first argument is the row itself, but since
            # in these cases parent must be None, this works.
            iter = model.append(parent)
            model.set(iter, 0, item)
            return iter

# vim:ts=4:sw=4:et
