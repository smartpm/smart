from cpm.const import ERROR, WARNING, DEBUG
import gtk, gobject

class GtkLog(gtk.Window):

    def __init__(self):
        gtk.Window.__init__(self)
        self.__gobject_init__()

        self.set_title("Log")
        self.set_geometry_hints(min_width=400, min_height=300)
        self.set_modal(True)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self.add(self._vbox)

        self._scrollwin = gtk.ScrolledWindow()
        self._scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._scrollwin.set_shadow_type(gtk.SHADOW_IN)
        self._scrollwin.show()
        self._vbox.add(self._scrollwin)

        self._textview = gtk.TextView()
        self._textview.set_editable(False)
        self._textview.show()
        self._scrollwin.add(self._textview)

        self._buttonbox = gtk.HButtonBox()
        self._buttonbox.set_spacing(10)
        self._buttonbox.set_layout(gtk.BUTTONBOX_END)
        self._buttonbox.show()
        self._vbox.pack_start(self._buttonbox, expand=False, fill=False)

        self._clearbutton = gtk.Button(stock="gtk-clear")
        self._clearbutton.show()
        self._clearbutton.connect("clicked",
                                  lambda x: self._textview.get_buffer()
                                                         .set_text(""))
        self._buttonbox.pack_start(self._clearbutton)

        self._closebutton = gtk.Button(stock="gtk-close")
        self._closebutton.show()
        self._closebutton.connect("clicked", lambda x: self.hide())
        self._buttonbox.pack_start(self._closebutton)

    def isVisible(self):
        return self.get_property("visible")

    def message(self, level, msg):
        prefix = {ERROR: "error", WARNING: "warning",
                  DEBUG: "debug"}.get(level)
        buffer = self._textview.get_buffer()
        iter = buffer.get_end_iter()
        if prefix:
            for line in msg.split("\n"):
                buffer.insert(iter, "%s: %s\n" % (prefix, line))
        else:
            buffer.insert(iter, msg)
        buffer.insert(iter, "\n")

        if level == ERROR:
            dialog = gtk.MessageDialog(self, flags=gtk.DIALOG_MODAL,
                                       type=gtk.MESSAGE_ERROR,
                                       buttons=gtk.BUTTONS_OK,
                                       message_format=msg)
            dialog.run()
            dialog.hide()
            del dialog
        else:
            self.show()

gobject.type_register(GtkLog)

