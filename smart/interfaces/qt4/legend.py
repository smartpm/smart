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
from smart.interfaces.qt4 import getPixmap
from smart import *
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

class QtLegend(QtGui.QDialog):

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self.setWindowTitle(_("Icon Legend"))

        layout = QtGui.QVBoxLayout(self)

        self._vbox = QtGui.QWidget(self)
        QtGui.QVBoxLayout(self._vbox)
        self._vbox.layout().setMargin(10)
        self._vbox.layout().setSpacing(10)

        layout.addWidget(self._vbox)

        label = QtGui.QLabel("<b>" + _("The following icons are used to indicate\nthe current status of a package:").replace("\n", "<br>") + "</b>", self._vbox)
        label.show()
        self._vbox.layout().addWidget(label)

        grid = QtGui.QWidget(self)
        QtGui.QGridLayout(grid)
        grid.layout().setSpacing(5)
        grid.layout().setMargin(5)
        grid.layout().setColumnStretch(1, 1)
        grid.show()
        self._vbox.layout().addWidget(grid)
  
        row = 0
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
            image = QtGui.QLabel("", grid)
            image.setPixmap(icon)
            image.show()
            grid.layout().addWidget(image, row, 0, QtCore.Qt.AlignLeft)
            label = QtGui.QLabel(legend, grid)
            label.show()
            grid.layout().addWidget(label, row, 1, QtCore.Qt.AlignLeft)
            row = row + 1
        
        self._buttonbox = QtGui.QWidget(self._vbox)
        QtGui.QHBoxLayout(self._buttonbox)
        self._buttonbox.layout().setSpacing(10)
        self._buttonbox.layout().addStretch(1)
        self._buttonbox.show()
        self._vbox.layout().addWidget(self._buttonbox)

        self._closebutton = QtGui.QPushButton(_("Close"), self._buttonbox)
        self._closebutton.show()
        QtCore.QObject.connect(self._closebutton, QtCore.SIGNAL("clicked()"), self, QtCore.SLOT("hide()"))
        self._buttonbox.layout().addWidget(self._closebutton)

    def isVisible(self):
        return QtGui.QDialog.isVisible(self)

