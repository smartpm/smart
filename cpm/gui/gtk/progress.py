#!/usr/bin/python
from cpm.progress import Progress
import gobject, gtk

class ProgressCellRenderer(gtk.GenericCellRenderer):

    __gproperties__ = {
        "percent": (gobject.TYPE_INT, "Percent", 
                    "Progress percentage", 0, 100, 0,
                    gobject.PARAM_READWRITE),
    }
                     
    def __init__(self):
        self.__gobject_init__()
        self.percent = 0

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def on_render(self, window, widget, background_area,
                  cell_area, expose_area, flags):
        x_offset, y_offset, width, height = self.on_get_size(widget, cell_area)
        widget.style.paint_box(window, gtk.STATE_NORMAL, gtk.SHADOW_IN,
                               None, widget, "trough",
                               cell_area.x+x_offset, cell_area.y+y_offset,
                               width, height)
        xt = widget.style.xthickness
        xpad = self.get_property("xpad")
        space = (width-2*xt-2*xpad)*(self.percent/100.)
        widget.style.paint_box(window, gtk.STATE_PRELIGHT, gtk.SHADOW_OUT,
                               None, widget, "bar",
                               cell_area.x+x_offset+xt,
                               cell_area.y+y_offset+xt,
                               int(space), height-2*xt)

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
            width = self.get_property("width")
            height = self.get_property("height")
            if width == -1: width = 100
            if height == -1: height = 30
            width += xpad*2
            height += ypad*2
            x_offset = 0
            y_offset = 0
        return x_offset, y_offset, width, height

gobject.type_register(ProgressCellRenderer)

class GtkProgress(Progress):

    def __init__(self):
        Progress.__init__(self)

        self.window = gtk.Window()
        self.window.set_title("Operation Progress")
        self.window.set_modal(True)
        self.window.set_position(gtk.WIN_POS_CENTER)

        self.vbox = gtk.VBox()
        self.vbox.set_border_width(10)
        self.vbox.set_spacing(10)
        self.vbox.show()
        self.window.add(self.vbox)

        self.topic = gtk.Label()
        self.topic.set_alignment(0, 0.5)
        self.topic.show()
        self.vbox.pack_start(self.topic, 0, 0)

        self.progress = gtk.ProgressBar()
        self.progress.set_size_request(-1, 25)
        self.progress.show()
        self.vbox.pack_start(self.progress, 0, 0)

        self.scrollwin = gtk.ScrolledWindow()
        self.scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrollwin.set_shadow_type(gtk.SHADOW_IN)
        self.vbox.pack_start(self.scrollwin,
                             gtk.EXPAND|gtk.FILL, gtk.EXPAND|gtk.FILL)

        self.treemodel = gtk.ListStore(gobject.TYPE_INT,
                                       gobject.TYPE_STRING)
        self.treeview = gtk.TreeView(self.treemodel)
        #self.treeview.set_property("fixed_height_mode", True)
        self.treeview.show()
        self.scrollwin.add(self.treeview)

        renderer = ProgressCellRenderer()
        column = gtk.TreeViewColumn("Progress", renderer, percent=0)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(110)
        self.treeview.append_column(column)

        renderer = gtk.CellRendererText()
        renderer.set_fixed_height_from_font(True)
        column = gtk.TreeViewColumn("Description", renderer, text=1)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self.treeview.append_column(column)

        self.subprogress = {}
        self.subindex = 0
        self.lastpath = None

    def start(self, hassub=False):
        Progress.start(self, hassub)
        if hassub:
            self.scrollwin.show()
            self.window.set_size_request(500, 400)
        else:
            self.scrollwin.hide()
            self.window.set_size_request(300, 80)

    def stop(self):
        Progress.stop(self)
        self.subprogress.clear()
        self.subindex = 0
        self.lastpath = None
        #self.hide()

    def hide(self):
        self.window.hide()
        self.window.unrealize()

    def expose(self, topic, percent, subkey, subtopic, subpercent, data):
        self.window.show()
        
        if self._hassub and subkey:
            if subkey in self.subprogress:
                iter = self.subprogress[subkey]
            else:
                iter = self.treemodel.append()
                self.subprogress[subkey] = iter
                path = self.treemodel.get_path(iter)
                if self.lastpath:
                    column = self.treeview.get_column(1)
                    cellarea = self.treeview.get_cell_area(self.lastpath,
                                                           column)
                    cellarea.x, cellarea.y = self.treeview.\
                                             widget_to_tree_coords(cellarea.x,
                                                                   cellarea.y)
                    visiblearea = self.treeview.get_visible_rect()
                    isvisible = visiblearea.intersect(cellarea).height
                if not self.lastpath or isvisible:
                    self.treeview.scroll_to_cell(path, None, True, 0, 0)
                self.lastpath = path
            self.treemodel.set(iter, 0, subpercent, 1, subtopic)
        else:
            self.topic.set_text(topic)
            self.progress.set_fraction(percent/100.)
            self.progress.set_text("%d%%" % percent)
            self.treeview.queue_draw()
            while gtk.events_pending():
                gtk.main_iteration()

def test():
    import sys, time

    prog = GtkProgress()

    data = {"item-number": 0}
    total, subtotal = 100, 100
    prog.start(True)
    prog.setTopic("Installing packages...")
    for n in range(1,total+1):
        data["item-number"] = n
        prog.set(n, total)
        prog.setSubTopic(n, "package-name%d" % n)
        for i in range(0,subtotal+1):
            prog.setSub(n, i, subtotal, subdata=data)
            prog.show()
            time.sleep(0.01)
    prog.stop()


if __name__ == "__main__":
    test()

# vim:ts=4:sw=4:et
