
class GtkInteractiveInterface:

    def __init__(self):
        self._ctrl = None

        self._window = gtk.Window()
        #self._window.set_title("")
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=400, min_height=300)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._

    def run(self, ctrl):
        self._ctrl = ctrl
        self._window.show()
        gtk.main()

