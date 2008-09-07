#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Anders F Bjorklund <afb@users.sourceforge.net>
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
import re

TARGETRE = re.compile(r"^\s*(\S+?)\s*(?:([<>=]+)\s*(\S+))?\s*$")

class QtFlags(object):

    def __init__(self, parent=None):

        self._window = qt.QDialog(None)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("Flags"))
        #self._window.set_modal(True)
        
        #self._window.set_transient_for(parent)
        #self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.setMinimumSize(600, 400)

        topvbox = qt.QVBox(self._window)
        topvbox.setMinimumSize(600, 400) # HACK
        topvbox.setMargin(10)
        topvbox.setSpacing(10)
        topvbox.show()

        tophbox = qt.QHBox(topvbox)
        tophbox.setSpacing(20)
        tophbox.show()

        # Left side
        vbox = qt.QVGroupBox(tophbox)
        vbox.setInsideSpacing(10)
        vbox.show()

        #sw.set_shadow_type(gtk.SHADOW_IN)
        sv = qt.QScrollView(vbox)
        sv.show()

        #self._flagsmodel = gtk.ListStore(gobject.TYPE_STRING)
        #self._flagsview = gtk.TreeView(self._flagsmodel)
        #self._flagsview.set_rules_hint(True)
        #self._flagsview.show()
        #sw.add(self._flagsview)
        self._flagsview = qt.QListView(sv)
        self._flagsview.setMinimumSize(300, 400) # HACK
        self._flagsview.show()

        #selection = self._flagsview.get_selection()
        #selection.connect("changed", self.flagSelectionChanged)
        qt.QObject.connect(self._flagsview, qt.SIGNAL("selectionChanged()"), self.flagSelectionChanged)

        #renderer = gtk.CellRendererText()
        #renderer.set_property("xpad", 3)
        #renderer.set_property("editable", True)
        #renderer.connect("edited", self.flagEdited)
        #self._flagsview.insert_column_with_attributes(-1, _("Flags"), renderer,
        #                                              text=0)
        self._flagsview.addColumn(_("Flags"))

        bbox = qt.QHBox(vbox)
        bbox.setMargin(5)
        bbox.setSpacing(10)
        bbox.show()

        button = qt.QPushButton(_("New"), bbox)
        button.setEnabled(True)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-add")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.newFlag)
        self._newflag = button

        button = qt.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-delete")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.delFlag)
        self._delflag = button

        # Right side
        vbox = qt.QVGroupBox(tophbox)
        vbox.setInsideSpacing(10)
        vbox.show()

        #sw = gtk.ScrolledWindow()
        #sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        #sw.set_shadow_type(gtk.SHADOW_IN)
        #sw.show()
        #vbox.add(sw)
        sv = qt.QScrollView(vbox)
        sv.show()

        #self._targetsmodel = gtk.ListStore(gobject.TYPE_STRING)
        #self._targetsview = gtk.TreeView(self._targetsmodel)
        #self._targetsview.set_rules_hint(True)
        #self._targetsview.show()
        #sw.add(self._targetsview)
        self._targetsview = qt.QListView(sv)
        self._targetsview.setMinimumSize(300, 400) # HACK
        self._targetsview.show()

        #selection = self._targetsview.get_selection()
        #selection.connect("changed", self.targetSelectionChanged)
        qt.QObject.connect(self._targetsview, qt.SIGNAL("selectionChanged()"), self.targetSelectionChanged)

        #renderer = gtk.CellRendererText()
        #renderer.set_property("xpad", 3)
        #renderer.set_property("editable", True)
        #renderer.connect("edited", self.targetEdited)
        #self._targetsview.insert_column_with_attributes(-1, _("Targets"),
        #                                                renderer, text=0)
        self._targetsview.addColumn(_("Targets"))

        bbox = qt.QHBox(vbox)
        bbox.setMargin(5)
        bbox.setSpacing(10)
        bbox.show()

        button = qt.QPushButton(_("New"), bbox)
        button.setEnabled(False)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-add")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.newTarget)
        self._newtarget = button

        button = qt.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-delete")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.delTarget)
        self._deltarget = button


        # Bottom
        sep = qt.QFrame(topvbox)
        sep.setFrameShape(qt.QFrame.HLine)
        sep.setFrameShadow(qt.QFrame.Sunken)
        sep.show()

        bbox = qt.QHBox(topvbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = qt.QPushButton(_("Close"), bbox)
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))
        
        button.setDefault(True)

    def fillFlags(self):
        #self._flagsmodel.clear()
        self._flagsview.clear()
        flaglst = pkgconf.getFlagNames()
        flaglst.sort()
        for flag in flaglst:
            #self._flagsmodel.append((flag,))
            qt.QListViewItem(self._flagsview).setText(0, flag)
    
    def fillTargets(self):
        #self._targetsmodel.clear()
        self._targetsview.clear()
        if self._flag:
            names = pkgconf.getFlagTargets(self._flag)
            namelst = names.keys()
            namelst.sort()
            for name in namelst:
                for relation, version in names[name]:
                    if relation and version:
                        #self._targetsmodel.append(("%s %s %s" %
                        #                           (name, relation, version),))
                        item = qt.QListViewItem(self._targetsview)
                        item.setText(0, "%s %s %s" % (name, relation, version))
                    else:
                        #self._targetsmodel.append((name,))
                        qt.QListViewItem(self._targetsview).setText(0, name)

    def show(self):
        self.fillFlags()
        self._window.show()
        self._window.raiseW()
        self._window.exec_loop()
        self._window.hide()

    def newFlag(self):
        flag = FlagCreator(self._window).show()
        if flag:
            if pkgconf.flagExists(flag):
                iface.error(_("Flag already exists!"))
            else:
                pkgconf.createFlag(flag)
                self.fillFlags()

    def newTarget(self):
        target = TargetCreator(self._window).show()
        if target:
            m = TARGETRE.match(target)
            if m:
                name, relation, version = m.groups()
                pkgconf.setFlag(self._flag, name, relation, version)
            self.fillTargets()

    def delFlag(self):
        #selection = self._flagsview.get_selection()
        #model, iter = selection.get_selected()
        item = self._flagsview.selectedItem()
        if item:
            pkgconf.clearFlag(self._flag)
            self.fillFlags()
            self.fillTargets()

    def delTarget(self):
        #selection = self._targetsview.get_selection()
        #model, iter = selection.get_selected()
        item = self._targetsview.selectedItem()
        if item:
            target = str(item.text(0))
            m = TARGETRE.match(target)
            if not m:
                iface.error(_("Invalid target!"))
            else:
                name, relation, version = m.groups()
                pkgconf.clearFlag(self._flag, name, relation, version)
                if not pkgconf.flagExists(self._flag):
                    self.fillFlags()
                else:
                    self.fillTargets()

    def flagEdited(self, cell, row, newtext):
        model = self._flagsmodel
        iter = model.get_iter_from_string(row)
        oldtext = model.get_value(iter, 0)
        if newtext != oldtext:
            if pkgconf.flagExists(newtext):
                iface.error(_("Flag already exists!"))
            else:
                pkgconf.renameFlag(oldtext, newtext)
                model.set_value(iter, 0, newtext)

    def targetEdited(self, cell, row, newtext):
        model = self._targetsmodel
        iter = model.get_iter_from_string(row)
        oldtext = model.get_value(iter, 0)
        if newtext != oldtext:
            m = TARGETRE.match(oldtext)
            if not m:
                iface.error(_("Invalid target!"))
            else:
                oldname, oldrelation, oldversion = m.groups()
                m = TARGETRE.match(newtext)
                if not m:
                    iface.error(_("Invalid target!"))
                else:
                    newname, newrelation, newversion = m.groups()
                    pkgconf.clearFlag(self._flag, oldname,
                                      oldrelation, oldversion)
                    pkgconf.setFlag(self._flag, newname,
                                    newrelation, newversion)
                    if newrelation and newversion:
                        model.set_value(iter, 0, "%s %s %s" %
                                        (newname, newrelation, newversion))
                    else:
                        model.set_value(iter, 0, newname)

    def flagSelectionChanged(self):
        #model, iter = selection.get_selected()
        #self._delflag.set_property("sensitive", bool(iter))
        #self._newtarget.set_property("sensitive", bool(iter))
        item = self._flagsview.selectedItem()
        self._delflag.setEnabled(bool(item))
        self._newtarget.setEnabled(bool(item))
        if item:
            self._flag = str(item.text(0))
        else:
            self._flag = None
        self.fillTargets()

    def targetSelectionChanged(self):
        #model, iter = selection.get_selected()
        #self._deltarget.set_property("sensitive", bool(iter))
        item = self._targetsview.selectedItem()
        self._deltarget.setEnabled(bool(item))

class FlagCreator(object):

    def __init__(self, parent=None):

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("New Flag"))
        self._window.setModal(True)

        #self._window.set_position(gtk.WIN_POS_CENTER)
        ##self._window.set_geometry_hints(min_width=600, min_height=400)

        vbox = qt.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        table = qt.QGrid(2, vbox)
        table.setSpacing(10)
        
        label = qt.QLabel(_("Name:"), table)

        self._flag = qt.QLineEdit(table)
        self._flag.setMaxLength(20)
        self._flag.show()

        sep = qt.QFrame(vbox)
        sep.setFrameShape(qt.QFrame.HLine)
        sep.setFrameShadow(qt.QFrame.Sunken)
        sep.show()

        bbox = qt.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = qt.QPushButton(bbox.tr("OK"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))

        button = qt.QPushButton(bbox.tr("Cancel"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("reject()"))

        vbox.adjustSize()
        self._window.adjustSize()

    def show(self):

        self._window.show()
        self._window.raiseW()
        self._window.setActiveWindow()

        while True:
            self._result = self._window.exec_loop()
            if self._result == qt.QDialog.Accepted:
                flag = str(self._flag.text()).strip()
                if not flag:
                    iface.error(_("No flag name provided!"))
                    continue
                break
            flag = None
            break

        self._window.hide()

        return flag

class TargetCreator(object):

    def __init__(self, parent=None):

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("New Target"))
        self._window.setModal(True)

        #self._window.set_position(gtk.WIN_POS_CENTER)
        ##self._window.set_geometry_hints(min_width=600, min_height=400)

        vbox = qt.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        table = qt.QGrid(2, vbox)
        table.setSpacing(10)
        table.show()
        
        label = qt.QLabel(_("Target:"), table)

        self._target = qt.QLineEdit(table)
        self._target.setMaxLength(40)
        self._target.show()

        blank = qt.QWidget(table)

        label = qt.QLabel(_("Examples: \"pkgname\", \"pkgname = 1.0\" or "
                            "\"pkgname <= 1.0\""), table)

        sep = qt.QFrame(vbox)
        sep.setFrameShape(qt.QFrame.HLine)
        sep.setFrameShadow(qt.QFrame.Sunken)
        sep.show()

        bbox = qt.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = qt.QPushButton(bbox.tr("OK"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))

        button = qt.QPushButton(bbox.tr("Cancel"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("reject()"))

        vbox.adjustSize()
        self._window.adjustSize()

    def show(self):

        self._window.show()
        self._window.raiseW()
        self._window.setActiveWindow()

        while True:
            self._result = self._window.exec_loop()
            if self._result == qt.QDialog.Accepted:
                target = str(self._target.text()).strip()
                if not target:
                    iface.error(_("No target provided!"))
                    continue
                if ('"' in target or ',' in target or
                    not TARGETRE.match(target)):
                    iface.error(_("Invalid target!"))
                    continue
                break
            target = None
            break

        self._window.hide()

        return target

# vim:ts=4:sw=4:et
