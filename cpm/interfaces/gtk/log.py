from cpm.const import ERROR, WARNING, DEBUG
import gtk

class GtkLog:

    def __init__(self):
        self.window = gtk.Window()
        self.window.set_title("Log")
        self.window.set_geometry_hints(min_width=400, min_height=300)
        self.window.set_modal(True)

        self.vbox = gtk.VBox()
        self.vbox.set_border_width(10)
        self.vbox.set_spacing(10)
        self.vbox.show()
        self.window.add(self.vbox)

        self.scrollwin = gtk.ScrolledWindow()
        self.scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrollwin.set_shadow_type(gtk.SHADOW_IN)
        self.scrollwin.show()
        self.vbox.add(self.scrollwin)

        self.textview = gtk.TextView()
        self.textview.set_editable(False)
        self.textview.show()
        self.scrollwin.add(self.textview)

        self.buttonbox = gtk.HButtonBox()
        self.buttonbox.set_spacing(10)
        self.buttonbox.set_layout(gtk.BUTTONBOX_END)
        self.buttonbox.show()
        self.vbox.pack_start(self.buttonbox, expand=False, fill=False)

        self.clearbutton = gtk.Button(stock="gtk-clear")
        self.clearbutton.show()
        self.clearbutton.connect("clicked",
                                 lambda x: self.textview.get_buffer()
                                                        .set_text(""))
        self.buttonbox.pack_start(self.clearbutton)

        self.closebutton = gtk.Button(stock="gtk-close")
        self.closebutton.show()
        self.closebutton.connect("clicked", lambda x: self.window.hide())
        self.buttonbox.pack_start(self.closebutton)

    def isVisible(self):
        return self.window.get_property("visible")

    def message(self, level, msg):
        prefix = {ERROR: "error", WARNING: "warning",
                  DEBUG: "debug"}.get(level)
        buffer = self.textview.get_buffer()
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
            self.window.show()

