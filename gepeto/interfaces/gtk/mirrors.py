#!/usr/bin/python
from gepeto import *
import gobject, gtk

class GtkMirrors(object):

    def __init__(self):

        self._window = gtk.Window()
        self._window.set_title("Mirrors")
        self._window.set_modal(True)
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=600, min_height=400)
        def delete(widget, event):
            gtk.main_quit()
            return True
        self._window.connect("delete-event", delete)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self._window.add(self._vbox)

        self._scrollwin = gtk.ScrolledWindow()
        self._scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self._scrollwin.set_shadow_type(gtk.SHADOW_IN)
        self._scrollwin.show()
        self._vbox.add(self._scrollwin)

        self._treemodel = gtk.TreeStore(gobject.TYPE_STRING)
        self._treeview = gtk.TreeView(self._treemodel)
        self._treeview.set_rules_hint(True)
        self._treeview.set_headers_visible(False)
        self._treeview.show()
        self._scrollwin.add(self._treeview)

        renderer = gtk.CellRendererText()
        renderer.set_property("xpad", 3)
        renderer.set_property("editable", True)
        renderer.connect("edited", self.rowEdited)
        self._treeview.insert_column_with_attributes(-1, "Mirror", renderer,
                                                     text=0)

        bbox = gtk.HButtonBox()
        bbox.set_spacing(10)
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.show()
        self._vbox.pack_start(bbox, expand=False)

        self._newbutton = gtk.Button(stock="gtk-new")
        self._newbutton.show()
        self._newbutton.connect("clicked", lambda x: self.newMirror())
        bbox.pack_start(self._newbutton)

        self._deletebutton = gtk.Button(stock="gtk-delete")
        self._deletebutton.show()
        self._deletebutton.connect("clicked", lambda x: self.delMirror())
        bbox.pack_start(self._deletebutton)

        self._closebutton = gtk.Button(stock="gtk-close")
        self._closebutton.show()
        self._closebutton.connect("clicked", lambda x: gtk.main_quit())
        bbox.pack_start(self._closebutton)

    def fill(self):
        self._treemodel.clear()
        mirrors = sysconf.get("mirrors", setdefault={})
        for origin in mirrors:
            parent = self._treemodel.append(None, (origin,))
            for mirror in mirrors[origin]:
                iter = self._treemodel.append(parent, (mirror,))
        self._treeview.expand_all()
            
    def show(self):
        self.fill()
        self._window.show()
        gtk.main()
        self._window.hide()

    def newMirror(self):
        selection = self._treeview.get_selection()
        model, iter = selection.get_selected()
        if iter:
            path = model.get_path(iter)
            if len(path) == 2:
                iter = model.get_iter(path[:1])
            origin = model.get_value(iter, 0)
        else:
            origin = ""
        origin, mirror = MirrorEditor().show(origin)
        if origin and mirror:
            mirrors = sysconf.get("mirrors", setdefault={})
            if origin in mirrors:
                if mirror not in mirrors[origin]:
                    mirrors[origin].append(mirror)
            else:
                mirrors[origin] = [mirror]
        self.fill()


    def delMirror(self):
        selection = self._treeview.get_selection()
        model, iter = selection.get_selected()
        if not iter:
            return
        path = model.get_path(iter)
        mirrors = sysconf.get("mirrors", setdefault={})
        if len(path) == 1:
            origin = model.get_value(iter, 0)
            del mirrors[origin]
        else:
            mirror = model.get_value(iter, 0)
            iter = model.get_iter(path[:1])
            origin = model.get_value(iter, 0)
            mirrors[origin].remove(mirror)
            if not mirrors[origin]:
                del mirrors[origin]
        self.fill()

    def rowEdited(self, cell, row, newtext):
        model = self._treemodel
        iter = model.get_iter_from_string(row)
        path = model.get_path(iter)
        mirrors = sysconf.get("mirrors", setdefault={})
        oldtext = model.get_value(iter, 0)
        if newtext == oldtext:
            return
        if len(path) == 1:
            if newtext in mirrors:
                iface.error("Origin already exists!")
            else:
                mirrors[newtext] = mirrors[oldtext]
                del mirrors[oldtext]
                model.set_value(iter, 0, newtext)
        else:
            origin = model.get_value(model.get_iter(path[1:]), 0)
            if newtext in mirrors[origin]:
                iface.error("Mirror already exists!")
            else:
                mirrors[origin].append(newtext)
                mirrors[origin].remove(oldtext)
                model.set_value(iter, 0, newtext)

class MirrorEditor(object):

    def __init__(self):

        self._window = gtk.Window()
        self._window.set_title("Mirror")
        self._window.set_modal(True)
        self._window.set_position(gtk.WIN_POS_CENTER)
        #self._window.set_geometry_hints(min_width=600, min_height=400)
        def delete(widget, event):
            gtk.main_quit()
            return True
        self._window.connect("delete-event", delete)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self._window.add(self._vbox)

        table = gtk.Table()
        table.set_row_spacings(10)
        table.set_col_spacings(10)
        table.show()
        self._vbox.pack_start(table)
        
        label = gtk.Label("Origin URL:")
        label.set_alignment(1.0, 0.5)
        label.show()
        table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL)

        self._origin = gtk.Entry()
        self._origin.set_width_chars(40)
        self._origin.show()
        table.attach(self._origin, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL, gtk.FILL)

        label = gtk.Label("Mirror URL:")
        label.set_alignment(1.0, 0.5)
        label.show()
        table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL)

        self._mirror = gtk.Entry()
        self._mirror.set_width_chars(40)
        self._mirror.show()
        table.attach(self._mirror, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, gtk.FILL)

        sep = gtk.HSeparator()
        sep.show()
        self._vbox.pack_start(sep, expand=False)

        bbox = gtk.HButtonBox()
        bbox.set_spacing(10)
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.show()
        self._vbox.pack_start(bbox, expand=False)

        self._okbutton = gtk.Button(stock="gtk-ok")
        self._okbutton.show()
        def clicked(x):
            self._result = True
            gtk.main_quit()
        self._okbutton.connect("clicked", clicked)
        bbox.pack_start(self._okbutton)

        self._cancelbutton = gtk.Button(stock="gtk-cancel")
        self._cancelbutton.show()
        self._cancelbutton.connect("clicked", lambda x: gtk.main_quit())
        bbox.pack_start(self._cancelbutton)

    def show(self, origin="", mirror=""):

        self._origin.set_text(origin)
        self._mirror.set_text(mirror)
        origin = mirror = None

        self._window.show()

        self._result = False
        while True:
            gtk.main()
            if self._result:
                self._result = False
                origin = self._origin.get_text().strip()
                if not origin:
                    iface.error("No origin provided!")
                    continue
                mirror = self._mirror.get_text().strip()
                if not mirror:
                    iface.error("No mirror provided!")
                    continue
                break
            origin = mirror = None
            break

        self._window.hide()

        return origin, mirror

# vim:ts=4:sw=4:et
