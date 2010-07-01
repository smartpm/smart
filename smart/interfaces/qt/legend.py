#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from smart.interfaces.qt import getPixmap
from smart import *
import qt

class QtLegend(qt.QDialog):

    def __init__(self, parent=None):
        qt.QDialog.__init__(self, parent)

        self.setIcon(getPixmap("smart"))
        self.setCaption(_("Icon Legend"))

        layout = qt.QVBoxLayout(self)

        self._vbox = qt.QVBox(self)
        self._vbox.setMargin(10)
        self._vbox.setSpacing(10)

        layout.add(self._vbox)

        label = qt.QLabel("<b>" + _("The following icons are used to indicate\nthe current status of a package:") + "</b>", self._vbox)
        label.show()

        grid = qt.QGrid(2, self._vbox)
        grid.setSpacing(5)
        grid.setMargin(5)
        grid.show()
  
        for icon, legend in [
        (getPixmap("package-install"),            _("Marked for installation")),
        (getPixmap("package-reinstall"),          _("Marked for re-installation")),
        (getPixmap("package-upgrade"),            _("Marked for upgrade")),
        (getPixmap("package-downgrade"),          _("Marked for downgrade")),
        (getPixmap("package-remove"),             _("Marked for removal")),
        (getPixmap("package-available"),          _("Not installed")),
        (getPixmap("package-new"),                _("Not installed (new)")),
        (getPixmap("package-available-locked"),   _("Not installed (locked)")),
        (getPixmap("package-installed"),          _("Installed")),
        (getPixmap("package-installed-outdated"), _("Installed (upgradable)")),
        (getPixmap("package-installed-locked"),   _("Installed (locked)")),
        (getPixmap("package-broken"),             _("Broken")),
        ]:
            image = qt.QLabel("", grid)
            image.setPixmap(icon)
            image.show()
            label = qt.QLabel(legend, grid)
            label.show()
        
        self._buttonbox = qt.QHBox(self._vbox)
        self._buttonbox.setSpacing(10)
        self._buttonbox.layout().addStretch(1)
        self._buttonbox.show()

        self._closebutton = qt.QPushButton(_("Close"), self._buttonbox)
        self._closebutton.show()
        qt.QObject.connect(self._closebutton, qt.SIGNAL("clicked()"), self, qt.SLOT("hide()"))

    def isVisible(self):
        return qt.QDialog.isVisible(self)

