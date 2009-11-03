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
from smart.const import INSTALL, REMOVE
from smart import *
import qt

class PackageListViewItem(qt.QListViewItem):
    def __init__(self, parent, package = None):
        qt.QListViewItem.__init__(self, parent)
        self._pkg = package

class QtPackageView(qt.QWidget):

    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)

        self.show()
        self._expandpackage = False

        self._changeset = {}
        self._vbox = qt.QVBoxLayout(self)
        
        self._treeview = qt.QListView(self)
        qt.QObject.connect(self._treeview, qt.SIGNAL("clicked(QListViewItem *, const QPoint &, int)"), self._clicked)
        qt.QObject.connect(self._treeview, qt.SIGNAL("doubleClicked(QListViewItem *, const QPoint &, int)"), self._doubleClicked)
        qt.QObject.connect(self._treeview, qt.SIGNAL("rightButtonPressed(QListViewItem *, const QPoint &, int)"), self._rightButtonPressed)
        qt.QObject.connect(self._treeview, qt.SIGNAL("selectionChanged()"), self._selectionChanged)
        self._treeview.setAllColumnsShowFocus(True)
        self._treeview.setRootIsDecorated(True)
        self._treeview.show()
        self._vbox.addWidget(self._treeview)
        
        self._treeview.setSelectionMode(qt.QListView.Extended)
        
        self._treeview.addColumn("") # pixmap
        self._treeview.addColumn(_("Package"))
        self._treeview.addColumn(_("Version"))

        self._ipixbuf = getPixmap("package-installed")
        self._ilpixbuf = getPixmap("package-installed-locked")
        self._apixbuf = getPixmap("package-available")
        self._alpixbuf = getPixmap("package-available-locked")
        self._npixbuf = getPixmap("package-new")
        self._nlpixbuf = getPixmap("package-new-locked")
        self._fpixbuf = getPixmap("folder")
        self._Ipixbuf = getPixmap("package-install")
        self._Rpixbuf = getPixmap("package-remove")
        self._rpixbuf = getPixmap("package-reinstall")

    def _getPixmap(self, pkg):
            
            if not hasattr(pkg, "name"):
                    return self._fpixbuf
            else:
                    if pkg.installed:
                            if self._changeset.get(pkg) is REMOVE:
                                    return self._Rpixbuf
                            elif self._changeset.get(pkg) is INSTALL:
                                    return self._rpixbuf
                            elif pkgconf.testFlag("lock", pkg):
                                    return self._ilpixbuf
                            else:
                                    return self._ipixbuf
                    else:
                            if self._changeset.get(pkg) is INSTALL:
                                    return self._Ipixbuf
                            elif pkgconf.testFlag("lock", pkg):
                                    if pkgconf.testFlag("new", pkg):
                                            return self._nlpixbuf
                                    else:
                                            return self._alpixbuf
                            elif pkgconf.testFlag("new", pkg):
                                    return self._npixbuf
                            else:
                                    return self._apixbuf
            return self._fpixbuf #default

    def _setPixmap(self, iter, pkg):
        iter.setPixmap(0, self._getPixmap(pkg))

    def _setNameVersion(self, iter, pkg):
        if hasattr(pkg, "name"):
            iter.setText(1, pkg.name)
        else:
            iter.setText(1, unicode(pkg))

        if hasattr(pkg, "version"):
            iter.setText(2, pkg.version)


    def getTreeView(self):
        return self._treeview

    def expandAll(self):
        iter = qt.QListViewItemIterator(self._treeview)
        while iter.current():
            iter.current().setOpen(True)
            iter += 1

    def collapseAll(self):
        iter = qt.QListViewItemIterator(self._treeview)
        while iter.current():
            iter.current().setOpen(False)
            iter += 1

    def getSelectedPkgs(self):
        iter = qt.QListViewItemIterator(self._treeview)
        lst = []
        while iter.current():
            item = iter.current()
            if item.isSelected():
                value = item._pkg
                if hasattr(value, "name"):
                    lst.append(value)
            iter += 1
        return lst

    def setExpandPackage(self, flag):
        self._expandpackage = flag

    def getCursor(self):
        treeview = self._treeview
        model = treeview.get_model()
        path = treeview.get_cursor()[0]
        if not path:
            return None
        cursor = [None]*len(path)
        for i in range(len(path)):
            iter = model.get_iter(path[:i+1])
            cursor[i] = model.get_value(iter, 0)
        return cursor

    def setCursor(self, cursor):
        if not cursor:
            return
        treeview = self._treeview
        #model = treeview.get_model()
        #iter = None
        #bestiter = None
        #for i in range(len(cursor)):
        #    cursori = cursor[i]
        #    iter = model.iter_children(iter)
        #    while iter:
        #        value = model.get_value(iter, 0)
        #        if value == cursori:
        #            bestiter = iter
        #            break
        #        # Convert to str to protect against comparing
        #        # packages and strings.
        #        if str(value) < str(cursori):
        #            bestiter = iter
        #        iter = model.iter_next(iter)
        #    else:
        #        break
        #if bestiter:
        #    path = model.get_path(bestiter)
        #    treeview.set_cursor(path)
        #    treeview.scroll_to_cell(path)

    def getExpanded(self):
        expanded = []
        treeview = self._treeview
        model = treeview.get_model()
        def set(treeview, path, data):
            item = [None]*len(path)
            for i in range(len(path)):
                iter = model.get_iter(path[:i+1])
                item[i] = model.get_value(iter, 0)
            expanded.append(tuple(item))
        treeview.map_expanded_rows(set, None)
        return expanded

    def setExpanded(self, expanded):
        if not expanded:
            return
        treeview = self._treeview
        cache = {}
        for item in expanded:
            item = tuple(item)
            iter = None
            for i in range(len(item)):
                cached = cache.get(item[:i+1])
                if cached:
                    iter = cached
                    continue
                itemi = item[i]
                #iter = model.iter_children(iter)
                #while iter:
                #    value = model.get_value(iter, 0)
                #    if value == itemi:
                #        cache[item[:i+1]] = iter
                #        treeview.expand_row(model.get_path(iter), False)
                #        break
                #    iter = model.iter_next(iter)
                #else:
                #    break
                break

    def setChangeSet(self, changeset):
        if changeset is None:
            self._changeset = {}
        else:
            self._changeset = changeset

    def updatePackages(self, packages, changeset=None):
        treeview = self._treeview
        for pkg in packages:
            if hasattr(pkg, "name"):
                name = pkg.name
            else:
                name = str(pkg)
            iter = treeview.findItem(name, 1)
            if iter:
                if iter._pkg == pkg:
                    self._setNameVersion(iter, pkg)
                    self._setPixmap(iter, pkg)
        treeview.adjustColumn(0)

    def setPackages(self, packages, changeset=None, keepstate=False):
        treeview = self._treeview
        if not packages:
            treeview.clear()
            return
        self.setChangeSet(changeset)
        
        if keepstate: ###TO IMPLEMENT IN QT
            if False: #treeview.get_model():
                expanded = self.getExpanded()
                #cursor = self.getCursor()
            else:
                keepstate = False
        
        # clear the model until the new one is ready
        treeview.clear()
        self._setPackage(None, None, packages)
        
        #if keepstate:
            #self.setExpanded(expanded)
            #self.setCursor(cursor)
        treeview.update()

    def _setPackage(self, report, parent, item):
        if type(item) is list:
            item.sort()
            for subitem in item:
                self._setPackage(report, parent, subitem)
        elif type(item) is dict:
            keys = item.keys()
            keys.sort()
            for key in keys:
                iter = self._setPackage(report, parent, key)
                self._setPackage(report, iter, item[key])
        else:
            if parent is None:
                iter = PackageListViewItem(self._treeview, item)
            else:
                iter = PackageListViewItem(parent, item)
            #iter.setText(0, str(item))
            self._setNameVersion(iter, item)
            self._setPixmap(iter, item)
            
            return iter

    def _doubleClicked(self, item, pnt, c):
         if not item:
             return
         value = item._pkg
         if not self._expandpackage and hasattr(value, "name"):
             pkgs = self.getSelectedPkgs()
             if len(pkgs) > 1:
                 self.emit(qt.PYSIGNAL("packageActivated"), (pkgs, ))
             else:
                 self.emit(qt.PYSIGNAL("packageActivated"), ([value], ))

    def _rightButtonPressed(self, item, pnt, c):
         if not item:
             return
         value = item._pkg
         if item and hasattr(value, "name"):
             pkgs = self.getSelectedPkgs()
             if len(pkgs) > 1:
                 self.emit(qt.PYSIGNAL("packagePopup"), (self, pkgs, pnt))
             else:
                 self.emit(qt.PYSIGNAL("packagePopup"), (self, [value], pnt))

    def _clicked(self, item, pnt, c):
        if not item:
            return
        value = item._pkg
        if c == 0 and hasattr(value, "name"):
            self.emit(qt.PYSIGNAL("packageActivated"), ([value], ))

    def _selectionChanged(self):
        item = self._treeview.currentItem()
        if item and hasattr(item._pkg, "name"):
            self.emit(qt.PYSIGNAL("packageSelected"), (item._pkg, ))
        else:
            self.emit(qt.PYSIGNAL("packageSelected"), (None, ))

# vim:ts=4:sw=4:et
