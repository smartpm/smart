from cpm.const import ERROR, WARNING, DEBUG
import gtk

class GtkLog:

    def __init__(self):
        self._window = gtk.Window()
        self._window.set_title("Log")
        self._window.set_geometry_hints(min_width=400, min_height=300)
        self._window.set_modal(True)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self._window.add(self._vbox)

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
        self._closebutton.connect("clicked", lambda x: self._window.hide())
        self._buttonbox.pack_start(self._closebutton)

    def isVisible(self):
        return self._window.get_property("visible")

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
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                                       buttons=gtk.BUTTONS_OK,
                                       message_format=msg)
            dialog.run()
        else:
            self._window.show()

