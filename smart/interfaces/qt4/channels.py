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
from smart.interfaces.qt4 import getPixmap, centerWindow
from smart.util.strtools import strToBool
from smart.const import NEVER
from smart.channel import *
from smart import *
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import textwrap
import os

class RadioAction(QtGui.QAction):

    def __init__(self, radio, name, label=None):
        QtGui.QAction.__init__(self, name, radio)
        self._radio = radio
    
    def connect(self, object, field, userdata):
        self._object = object
        self._field = field
        self._userdata = userdata
        signal = "toggled(bool)"
        QtCore.QObject.connect(self._radio, QtCore.SIGNAL(signal), self.slot)
    
    def slot(self, state):
        if state:
            setattr(self._object, self._field, self._userdata)
         
class QtChannels(object):

    def __init__(self, parent=None):

        self._changed = False

        self._window = QtGui.QDialog(None)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("Channels"))
        self._window.setModal(True)

        self._window.setMinimumSize(600, 400)

        vbox = QtGui.QWidget(self._window)
        layout = QtGui.QVBoxLayout(vbox) 
        #layout.setResizeMode(QtGui.QLayout.FreeResize)

        #vbox = QtGui.QVBox(self._window)
        layout.setMargin(10)
        layout.setSpacing(10)
        vbox.show()

        self._vbox = vbox

        self._treeview = QtGui.QTreeWidget(vbox)
        self._treeview.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        #self._treeview.setAllColumnsShowFocus(True)
        #self._treeview.setSelectionMode(QtGui.QListView.Single)
        self._treeview.show()
        layout.addWidget(self._treeview)

        QtCore.QObject.connect(self._treeview, QtCore.SIGNAL("itemSelectionChanged ()"), self.selectionChanged)
        QtCore.QObject.connect(self._treeview, QtCore.SIGNAL("itemDoubleClicked (QTableWidgetItem *)"), self.doubleClicked)

        #self._treeview.addColumn("")
        #self._treeview.addColumn(_("Pri"))
        #self._treeview.addColumn(_("Alias"))
        #self._treeview.addColumn(_("Type"))
        #self._treeview.addColumn(_("Name"))
        self._treeview.setHeaderLabels(["", _("Pri"), _("Alias"), _("Type"), _("Name")])
        
        #bbox = QtGui.QHBox(vbox)
        bbox = QtGui.QWidget(vbox)
        layout.addWidget(bbox)
        layout = QtGui.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtGui.QPushButton(_("New"), bbox)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-add")))
        button.show()
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.newChannel)
        self._newchannel = button
        layout.addWidget(button)

        button = QtGui.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-delete")))
        button.show()
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.delChannel)
        self._delchannel = button
        layout.addWidget(button)

        button = QtGui.QPushButton(_("Edit"), bbox)
        button.setEnabled(False)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-edit")))
        button.show()
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.editChannel)
        self._editchannel = button
        layout.addWidget(button)

        button = QtGui.QPushButton(_("Close"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))
        layout.addWidget(button)

        button.setDefault(True)
        vbox.adjustSize()

    def fill(self):
        self._treeview.clear()
        channels = sysconf.get("channels", {})
        aliases = channels.keys()
        aliases.sort()
        for alias in aliases:
            channel = channels[alias]
            #item = QtGui.QCheckListItem(self._treeview, "", QtGui.QCheckListItem.CheckBoxController)
            item = QtGui.QTreeWidgetItem(self._treeview)
            item.setCheckState(0, not strToBool(channel.get("disabled")) and QtCore.Qt.Checked or QtCore.Qt.Unchecked)
            item.setText(1, str(channel.get("priority", 0)))
            item.setText(2, alias)
            item.setText(3, channel.get("type", ""))
            item.setText(4, channel.get("name", ""))

    def enableDisable(self):
        iter = 0
        while iter < self._treeview.topLevelItemCount():
            item = self._treeview.topLevelItem(iter)
            disabled = strToBool(sysconf.get(("channels", str(item.text(2)), "disabled")))
            if item.checkState(0) == QtCore.Qt.Checked:
                if disabled:
                    sysconf.remove(("channels", str(item.text(1)), "disabled"))
                    self._changed = True
            else:
                if not disabled:
                    sysconf.set(("channels", str(item.text(1)), "disabled"), True)
                    self._changed = True
            iter += 1
            
    def show(self):
        self.fill()
        self._vbox.adjustSize()
        self._window.show()
        centerWindow(self._window)
        self._window.raise_()
        self._window.activateWindow()
        self._window.exec_()
        self._window.hide()
        self.enableDisable()
        return self._changed

    def newChannel(self):
        self.enableDisable()

        method = MethodSelector(self._window).show()
        if not method:
            return

        editor = ChannelEditor(self._window)

        path = None
        removable = []

        if method == "manual":

            type = TypeSelector(self._window).show()
            if not type:
                return

            newchannel = {"type": type}
            if editor.show(None, newchannel, editalias=True):
                alias = newchannel["alias"]
                del newchannel["alias"]
                sysconf.set(("channels", alias),
                            parseChannelData(newchannel))
                self._changed = True
                if newchannel.get("removable"):
                    removable.append(alias)

        elif method in ("descriptionpath", "descriptionurl"):

            if method == "descriptionpath":
                filename = QtGui.QFileDialog.getOpenFileName(self._window,
                    _("Select Channel Description"), "", "", "")
                if not filename:
                    return
                if not os.path.isfile(filename):
                    iface.error(_("File not found: %s") % filename)
                    return
                file = open(filename)
                data = file.read()
                file.close()
            elif method == "descriptionurl":
                url = iface.askInput(_("Description URL"))
                if not url:
                    return
                ctrl = iface.getControl()
                succ, fail = ctrl.downloadURLs([url], _("channel description"))
                if fail:
                    iface.error(_("Unable to fetch channel description: %s")
                                % fail[url])
                    return
                file = open(succ[url])
                data = file.read()
                file.close()
                if succ[url].startswith(sysconf.get("data-dir")):
                    os.unlink(succ[url])
            
            newchannels = parseChannelsDescription(data)
            for alias in newchannels:
                newchannel = newchannels[alias]
                if editor.show(alias, newchannel, editalias=True):
                    alias = newchannel["alias"]
                    del newchannel["alias"]
                    sysconf.set(("channels", alias),
                                parseChannelData(newchannel))
                    self._changed = True
                    if newchannel.get("removable"):
                        removable.append(alias)

        elif method in ("detectmedia", "detectpath"):

            if method == "detectmedia":
                path = MountPointSelector().show()
                if not path:
                    return
            elif method == "detectpath":
                path = QtGui.QFileDialog.getExistingDirectory(self._window,
                     _("Select Path"), "", QtGui.QFileDialog.ShowDirsOnly)
                if not path:
                    return
                if not os.path.isdir(path):
                    iface.error(_("Directory not found: %s") % path)
                    return

            sysconf.set("default-localmedia", path, soft=True)

            foundchannel = False
            for newchannel in detectLocalChannels(path):
                foundchannel = True
                if editor.show(newchannel.get("alias"), newchannel,
                               editalias=True):
                    alias = newchannel["alias"]
                    del newchannel["alias"]
                    sysconf.set(("channels", alias),
                                parseChannelData(newchannel))
                    self._changed = True
                    if newchannel.get("removable"):
                        removable.append(alias)
            
            if not foundchannel:
                iface.error(_("No channels detected!"))
                return

        if removable:
            ctrl = iface.getControl()
            ctrl.rebuildSysConfChannels()
            channels = [x for x in ctrl.getChannels()
                        if x.getAlias() in removable]
            iface.updateChannels(channels=channels)

        if path:
            sysconf.remove("default-localmedia", soft=True)

        if self._changed:
            self.fill()

    def editChannel(self):
        item = self._treeview.selectedItems()
        if item:
            item = item[0]
            alias = str(item.text(2))
        else:
            return
        self.enableDisable()
        channel = sysconf.get(("channels", alias), {})
        editor = ChannelEditor(self._window)
        if editor.show(alias, channel):
            sysconf.set(("channels", alias),
                        parseChannelData(channel))
            self._changed = True
            self.fill()

    def delChannel(self):
        item = self._treeview.selectedItems()
        if item:
            item = item[0]
            alias = item.text(2)
        else:
            return
        if sysconf.remove(("channels", alias)):
            self._changed = True
            self.fill()

    def selectionChanged(self):
        item = self._treeview.selectedItems()
        if item:
            item = item[0]
            self._editchannel.setEnabled(True)
            self._delchannel.setEnabled(True)
        else:
            self._editchannel.setEnabled(False)
            self._delchannel.setEnabled(False)

    def doubleClicked(self, item):
        self.editChannel()

class QtChannelSelector(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("Select Channels"))
        self._window.setModal(True)

        self._window.setMinimumSize(600, 400)

        layout = QtGui.QVBoxLayout(self._window) 
        #layout.setResizeMode(QtGui.QLayout.FreeResize)
        
        #vbox = QtGui.QVBox(self._window)
        vbox = QtGui.QWidget(self._window)
        layout.addWidget(vbox)
        layout = QtGui.QVBoxLayout(vbox)
        layout.setMargin(10)
        layout.setSpacing(10)
        vbox.show()

        self._treeview = QtGui.QTableWidget(vbox)
        self._treeview.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        #self._treeview.setAllColumnsShowFocus(True)
        self._treeview.show()
        layout.addWidget(self._treeview)

        #self._treeview.addColumn("")
        #self._treeview.addColumn(_("Alias"))
        #self._treeview.addColumn(_("Type"))
        #self._treeview.addColumn(_("Name"))
        self._treeview.setHorizontalHeaderLabels(["", _("Alias"), _("Type"), _("Name")])

        bbox = QtGui.QWidget(vbox)
        layout.addWidget(bbox)
        layout = QtGui.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtGui.QPushButton(_("Cancel"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("reject()"))
        layout.addWidget(button)

        button = QtGui.QPushButton(_("OK"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))
        layout.addWidget(button)

        button.setDefault(True)

    def fill(self):
        self._treeview.clear()
        channels = sysconf.get("channels", {})
        aliases = channels.keys()
        aliases.sort()
        for alias in aliases:
            channel = channels[alias]
            if not channel.get("disabled"):
                row = self._treeview.rowCount()
                #item = QtGui.QCheckListItem(self._treeview, "", QtCore.QCheckListItem.CheckBox)
                item = QtGui.QTableWidgetItem()
                #item.setOn(False)
                item.setCheckState(QtCore.Qt.Unchecked)
                self._treeview.setItem(row, 0, item)
                item = QtGui.QTableWidgetItem()
                item.setText(str(alias))
                self._treeview.setItem(row, 1, item)
                item = QtGui.QTableWidgetItem()
                item.setText(channel.get("type", ""))
                self._treeview.setItem(row, 2, item)
                item = QtGui.QTableWidgetItem()
                item.setText(channel.get("name", ""))
                self._treeview.setItem(row, 3, item)

    def show(self):
        self.fill()
        self._result = False
        self._treeview.adjustSize()
        self._window.show()
        centerWindow(self._window)
        self._window.raise_()
        self._result = self._window.exec_()
        self._window.hide()

        result = []
        if self._result == QtGui.QDialog.Accepted:
            iter = 0
            while iter < self._treeview.rowCount():
                item = self._treeview.itemAt(iter, 0)
                if item.checkState() == QtCore.Qt.Checked:
                      result.append(item.text(1)) 
                iter += 1

        return result

class ChannelEditor(object):

    def __init__(self, parent=None):

        self._fields = {}
        self._fieldn = 0

        self._window = QtGui.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("Edit Channel"))
        self._window.setModal(True)

        layout = QtGui.QVBoxLayout(self._window)
        #layout.setResizeMode(QtGui.QLayout.FreeResize)

        vbox = QtGui.QWidget(self._window)
        layout.addWidget(vbox)
        layout = QtGui.QVBoxLayout(vbox) 
        layout.setMargin(10)
        layout.setSpacing(10)
        vbox.show()

        #layout.addWidget(vbox)
        self._vbox = vbox

        #self._table = QtGui.QGrid(2, vbox)
        self._table = QtGui.QWidget(vbox)
        QtGui.QGridLayout(self._table)
        self._table.layout().setSpacing(10)
        self._table.show()
        layout.addWidget(self._table)

        sep = QtGui.QFrame(vbox)
        sep.setFrameShape(QtGui.QFrame.HLine)
        sep.setFrameShadow(QtGui.QFrame.Sunken)
        sep.show()
        layout.addWidget(sep)

        #bbox = QtGui.QHBox(vbox)
        bbox = QtGui.QWidget(vbox)
        layout.addWidget(bbox)
        layout = QtGui.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtGui.QPushButton(_("Cancel"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("reject()"))
        layout.addWidget(button)

        button = QtGui.QPushButton(_("OK"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))
        layout.addWidget(button)

        button.setDefault(True)

    def addField(self, key, label, value, ftype,
                 editable=True, tip=None, needed=False):

        row = self._table.layout().rowCount()
        if ftype is bool:
            spacer = QtGui.QWidget(self._table)
            spacer.show()
            self._table.layout().addWidget(spacer, row, 0)
            widget = QtGui.QCheckBox(label, self._table)
            widget.setChecked(value)
        else:
            _label = QtGui.QLabel("%s:" % label, self._table)
            _label.show()
            if tip:
                _label.setToolTip(tip)
            self._table.layout().addWidget(_label, row, 0)
            if ftype is int:
                widget = QtGui.QSpinBox(self._table)
                widget.setSingleStep(1)
                widget.setRange(-100000,+100000)
                widget.setValue(value)
            elif ftype is str:
                widget = QtGui.QLineEdit(self._table)
                widget.setText(value)
                if key in ("alias", "type"):
                    #widget.setMaxLength(20)
                    pass # "usually enough for about 15 to 20 characters"
                else:
                    widget.resize(QtCore.QSize(widget.sizeHint().width()*2,
                                               widget.sizeHint().height()))
            else:
                raise Error, _("Don't know how to handle %s fields") % ftype

        widget.show()
        self._table.layout().addWidget(widget, row, 1)

        widget.setEnabled(bool(editable))
        if tip:
            widget.setToolTip(tip)

        self._fields[key] = widget
        self._fieldn += 1

    def show(self, alias, oldchannel, editalias=False):
        # reset the dialog fields
        for item in self._table.children():
            if isinstance(item, QtGui.QWidget): 
                self._table.removeChild(item)
                del item
        
        self._fieldn = 0

        if len(oldchannel) > 1:
            # This won't be needed once old format channels
            # are converted.
            channel = parseChannelData(oldchannel)
        else:
            channel = oldchannel.copy()

        info = getChannelInfo(channel.get("type"))

        for key, label, ftype, default, descr in info.fields:
            if key == "type" or (key == "alias" and not editalias):
                editable = False
            else:
                editable = True
            if key == "alias":
                value = alias
            else:
                value = channel.get(key, default)
            if value is None:
                value = ftype()
            tip = "\n".join(textwrap.wrap(text=descr, width=40))
            self.addField(key, label, value, ftype, editable, tip)

        self._vbox.adjustSize()
        self._window.adjustSize()

        self._window.show()
        self._window.raise_()

        while True:
            self._result = self._window.exec_()
            if self._result == QtGui.QDialog.Accepted:
                newchannel = {}
                for key, label, ftype, default, descr in info.fields:
                    widget = self._fields[key]
                    if ftype == str:
                        newchannel[key] = str(widget.text()).strip()
                    elif ftype == int:
                        newchannel[key] = int(str(widget.text()))
                    elif ftype == bool:
                        newchannel[key] = widget.isChecked()
                    else:
                        raise Error, _("Don't know how to handle %s fields") %\
                                     ftype
                try:
                    if editalias:
                        value = newchannel["alias"]
                        if not value:
                            raise Error, _("Invalid alias!")
                        if (value != alias and 
                            sysconf.has(("channels", value))):
                            raise Error, _("Alias already in use!")
                        if not alias:
                            alias = value
                    createChannel(alias, newchannel)
                except Error, e:
                    self._result == QtGui.QDialog.Rejected
                    iface.error(unicode(e))
                    continue
                else:
                    oldchannel.clear()
                    oldchannel.update(newchannel)
            break

        self._window.hide()

        return self._result

class TypeSelector(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("New Channel"))
        self._window.setModal(True)

        layout = QtGui.QVBoxLayout(self._window) 
        
        #vbox = QtGui.QVBox(self._window)
        vbox = QtGui.QWidget(self._window)
        layout.addWidget(vbox)
        layout = QtGui.QVBoxLayout(vbox) 
        layout.setMargin(10)
        layout.setSpacing(10)
        vbox.show()
        self._vbox = vbox

        #table = QtGui.QGrid(2, vbox)
        table = QtGui.QWidget(vbox)
        layout.addWidget(table)
        QtGui.QGridLayout(table)
        table.layout().setSpacing(10)
        table.show()
        self._table = table
        
        label = QtGui.QLabel(_("Type:"), table)
        table.layout().addWidget(label)

        self._typevbox = QtGui.QGroupBox(table)
        QtGui.QVBoxLayout(self._typevbox)
        #self._typevbox.setFrameStyle(QtGui.QFrame.NoFrame)
        self._typevbox.show()
        table.layout().addWidget(self._typevbox)

        sep = QtGui.QFrame(vbox)
        sep.setFrameShape(QtGui.QFrame.HLine)
        sep.setFrameShadow(QtGui.QFrame.Sunken)
        sep.show()
        layout.addWidget(sep)

        #bbox = QtGui.QHBox(vbox)
        bbox = QtGui.QWidget(vbox)
        layout.addWidget(bbox)
        layout = QtGui.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtGui.QPushButton(_("Cancel"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("reject()"))
        layout.addWidget(button)

        button = QtGui.QPushButton(_("OK"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))
        layout.addWidget(button)

        self._ok = button
        self._ok.setEnabled(False)

    def show(self):
        for item in self._typevbox.children():
            if isinstance(item, QtGui.QWidget): 
                self._typevbox.removeChild(item)
                del item
        self._type = None

        infos = [(info.name, type) for type, info in
                 getAllChannelInfos().items()]
        infos.sort()
        for name, type in infos:
            if not self._type:
                self._type = type
            radio = QtGui.QRadioButton(name, self._typevbox)
            radio.setObjectName(type)
            self._typevbox.layout().addWidget(radio)
            QtCore.QObject.connect(radio, QtCore.SIGNAL("clicked()"), self.ok)
            act = RadioAction(radio, type, name)
            act.connect(self, "_type", type)
            radio.show()

        self._typevbox.adjustSize()
        self._table.adjustSize()
        self._vbox.adjustSize()
        self._window.adjustSize()

        self._window.show()
        self._window.raise_()

        type = None
        while True:
            self._result = self._window.exec_()
            if self._result == QtGui.QDialog.Accepted:
                type = self._type
                break
            type = None
            break

        self._window.hide()

        return type

    def ok(self):
        self._ok.setEnabled(True)
        self._ok.setDefault((True))

class MethodSelector(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("New Channel"))
        self._window.setModal(True)

        vbox = QtGui.QWidget(self._window)
        layout = QtGui.QVBoxLayout(vbox) 
        vbox.layout().setMargin(10)
        vbox.layout().setSpacing(10)
        vbox.show()

        table = QtGui.QWidget(vbox)
        QtGui.QGridLayout(table) 
        table.layout().setSpacing(10)
        table.show()
        layout.addWidget(table)
        
        label = QtGui.QLabel(_("Method:"), table)
        table.layout().addWidget(label)
 
        methodvbox = QtGui.QGroupBox(table)
        QtGui.QVBoxLayout(methodvbox) 
        methodvbox.show()
        table.layout().addWidget(methodvbox)
 
        sep = QtGui.QFrame(vbox)
        sep.setFrameShape(QtGui.QFrame.HLine)
        sep.setFrameShadow(QtGui.QFrame.Sunken)
        sep.show()
        vbox.layout().addWidget(sep)

        bbox = QtGui.QWidget(vbox)
        layout = QtGui.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()
        vbox.layout().addWidget(bbox)

        button = QtGui.QPushButton(_("Cancel"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("reject()"))
        layout.addWidget(button)

        button = QtGui.QPushButton(_("OK"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))
        layout.addWidget(button)

        self._ok = button
        self._ok.setEnabled(False)
        
        self._method = None
        #group = QtGui.QButtonGroup(methodvbox)
        for method, descr in [("manual",
                               _("Provide channel information")),
                              ("descriptionpath",
                               _("Read channel description from local path")),
                              ("descriptionurl",
                               _("Read channel description from URL")),
                              ("detectmedia",
                               _("Detect channel in media (CDROM, DVD, etc)")),
                              ("detectpath",
                               _("Detect channel in local path"))]:
            if not self._method:
                self._method = method
            radio = QtGui.QRadioButton(method, methodvbox)
            radio.setText(descr)
            methodvbox.layout().addWidget(radio)
            #group.addButton(radio)
            QtCore.QObject.connect(radio, QtCore.SIGNAL("clicked()"), self.ok)
            act = RadioAction(radio, method, descr)
            act.connect(self, "_method", method)
            radio.show()
        
        methodvbox.adjustSize()
        vbox.adjustSize()
        self._window.adjustSize()

    def show(self):

        self._window.show()
        self._window.raise_()

        method = None
        while True:
            self._result = self._window.exec_()
            if self._result == QtGui.QDialog.Accepted:
                method = self._method
                break
            method = None
            break

        self._window.hide()

        return method

    def ok(self):
        self._ok.setEnabled(True)
        self._ok.setDefault((True))

class MountPointSelector(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("New Channel"))
        self._window.setModal(True)

        vbox = QtGui.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        table = QtGui.QWidget(vbox)
        QtGui.QGridLayout(table) 
        table.layout().setSpacing(10)
        table.show()
        
        label = QtGui.QLabel(_("Media path:"), table)

        self._mpvbox = QtGui.QWidget(table)
        QtGui.QVBoxLayout(self._mpvbox) 
        self._mpvbox.layout().setSpacing(10)
        self._mpvbox.show()

        sep = QtGui.QFrame(vbox)
        sep.setFrameShape(QtGui.QFrame.HLine)
        sep.setFrameShadow(QtGui.QFrame.Sunken)
        sep.show()

        bbox = QtGui.QWidget(vbox)
        QtGui.QHBoxLayout(bbox) 
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtGui.QPushButton(_("OK"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))
        bbox.layout().addWidget(button)

        button = QtGui.QPushButton(_("Cancel"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("reject()"))
        bbox.layout().addWidget(button)

    def show(self):
        for item in self._mpvbox.children():
            if isinstance(item, QtGui.QWidget): 
                self._mpvbox.removeChild(item)
                del item
        self._mp = None

        group = QtGui.QButtonGroup(None, "mp")
        n = 0
        for media in iface.getControl().getMediaSet():
            mp = media.getMountPoint()
            if not self._mp:
                self._mp = mp
            QtCore.QObject.connect(radio, QtCore.SIGNAL("clicked()"), self.ok)
            radio = QtGui.QRadioButton(mp, self._mpvbox)
            group.insert(radio)
            act = RadioAction(radio, mp)
            act.connect(self, "_mp", mp)
            radio.show()
            n += 1

        if n == 0:
            iface.error(_("No local media found!"))
            return None
        elif n == 1:
            return self._mp

        self._window.show()
        self._window.raise_()

        mp = None
        while True:
            self._result = self._window.exec_()
            if self._result == QtGui.QDialog.Accepted:
                mp = self._mp
                break
            mp = None
            break

        self._window.hide()

        return mp

    def ok(self):
        self._ok.setEnabled(True)
        self._ok.setDefault((True))

# vim:ts=4:sw=4:et
