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
from smart.interfaces.qt.packageview import QtPackageView
from smart.util.strtools import sizeToStr
from smart import *
import qt
import subprocess

class QtPackageInfo(qt.QWidget):
    def __init__(self, parent):
        qt.QWidget.__init__(self, parent)

        self._pkg = None
        self._changeset = None

        self._tabwidget = qt.QTabWidget(self)
        self._tabwidget.setMinimumSize(640,200) #HACK
        self._tabwidget.show()

        sv = qt.QScrollView(self)
        #sv.setMinimumSize(640,200) #HACK
        sv.setMargin(5)
        sv.show()

        bg = qt.QVBox(sv)
        bg.setMinimumSize(640,200) #HACK
        bg.show()

        grid = qt.QGrid(2, bg)
        grid.setSpacing(5)
        grid.setMargin(5)
        grid.show()

        self._info = type("Info", (), {})()

        row = 1
        for attr, text in [("status", _("Status:")),
                           ("priority", _("Priority:")),
                           ("group", _("Group:")),
                           ("installedsize", _("Installed Size:")),
                           ("channels", _("Channels:")),
                           ("reference", _("Reference URLs:"))]:
            label = qt.QLabel(text, grid)
            label.show()
            setattr(self._info, attr+"_label", label)
            label = qt.QLabel("", grid)
            label.show()
            setattr(self._info, attr, label)
            row += 1
        
        grid.adjustSize()
        self._grid = grid
        
        self._tabwidget.addTab(sv, _("General"))

        sv = qt.QScrollView(None)
        sv.setMargin(5)
        sv.show()

        bg = qt.QVBox(sv)
        bg.setMinimumSize(600, 200) # HACK
        bg.show()

        self._descr = qt.QLabel(bg)
        self._descr.setMinimumSize(600, 200) #HACK
        self._descr.setAlignment(qt.Qt.AlignTop)
        self._descr.setSizePolicy(qt.QSizePolicy.Expanding,qt.QSizePolicy.Expanding)
        self._descr.show()

        self._tabwidget.addTab(sv, _("Description"))

        sv = qt.QScrollView(self)
        #sv.setMinimumSize(600, 400) # HACK
        sv.setVScrollBarMode(qt.QScrollView.AlwaysOn)
        sv.setMargin(5)
        sv.show()

        bg = qt.QVBox(sv)
        bg.setMinimumSize(600, 400) # HACK
        bg.show()

        self._cont = qt.QLabel(bg)
        self._cont.setAlignment(qt.Qt.AlignTop)
        self._cont.setSizePolicy(qt.QSizePolicy.Expanding,qt.QSizePolicy.Expanding)
        self._cont.show()

        self._tabwidget.addTab(sv, _("Content"))

        self._relations = QtPackageView()
        self._relations.getTreeView().header().hide()
        self._relations.show()

        self._tabwidget.addTab(self._relations, _("Relations"))

        sv = qt.QScrollView(self)
        sv.setMargin(5)
        sv.show()

        self._urls = qt.QListView(sv)
        self._urls.setMinimumSize(600, 200)
        self._urls.setSizePolicy(qt.QSizePolicy.Expanding,qt.QSizePolicy.Expanding)
        self._urls.setAllColumnsShowFocus(True)
        self._urls.header().hide()
        self._urls.show()
        self._urls.addColumn(_("Channel"))
        self._urls.addColumn(_("Size"))
        self._urls.addColumn(_("URL"))
        
        self._tabwidget.addTab(sv, _("URLs"))

        qt.QObject.connect(self._tabwidget, qt.SIGNAL("currentChanged(QWidget *)"), self._currentChanged)
         
    def _currentChanged(self, widget):
        pagenum = qt.QTabWidget.indexOf(self._tabwidget, widget)
        self.setPackage(self._pkg, pagenum)

    def setChangeSet(self, changeset):
        self._changeset = changeset

    def setPackage(self, pkg, _pagenum=None):

        self._pkg = pkg

        if _pagenum is not None:
            num = _pagenum
        else:
            num = self._tabwidget.currentPageIndex()

        if num == 0:

            # Update general information

            if not pkg:
                self._info.status.setText("")
                self._info.group.setText("")
                self._info.installedsize.setText("")
                self._info.priority.setText("")
                self._info.channels.setText("")
                return

            group = None
            installedsize = None
            channels = []
            urls = []
            for loader in pkg.loaders:
                info = loader.getInfo(pkg)
                if group is None:
                    group = info.getGroup()
                if installedsize is None:
                    installedsize = info.getInstalledSize()
                channel = loader.getChannel()
                channels.append("%s (%s)" %
                                (channel.getName() or channel.getAlias(),
                                 channel.getAlias()))
                urls.extend(info.getReferenceURLs())

            flags = pkgconf.testAllFlags(pkg)
            if flags:
                flags.sort()
                flags = " (%s)" % ", ".join(flags)
            else:
                flags = ""

            def bold(text):
                return "<b>"+qt.QStyleSheet.escape(text)+"</b>"
            
            status = pkg.installed and _("Installed") or _("Available")
            self._info.status.setText(bold(status+flags))
            self._info.group.setText(bold(group or _("Unknown")))
            self._info.priority.setText(bold(str(pkg.getPriority())))
            self._info.channels.setText(bold("\n".join(channels)))
            for url in urls:
                pass

            if installedsize:
                self._info.installedsize.setText(bold(sizeToStr(installedsize)))
                self._info.installedsize.show()
                self._info.installedsize_label.show()
            else:
                self._info.installedsize.hide()
                self._info.installedsize_label.hide()
                pass
                
            self._grid.adjustSize()

        elif num == 1:

            # Update summary/description

            self._descr.setText("")
            if not pkg: return

            #iter = descrbuf.get_end_iter()
            text = ""
            for loader in pkg.loaders:
                info = loader.getInfo(pkg)
                summary = info.getSummary()
                if summary:
                    text += "<b>"+qt.QStyleSheet.escape(summary)+"</b><br><br>"
                    description = info.getDescription()
                    if description != summary:
                         text += description+"\n\n"
                    break
            else:
                loader = pkg.loaders.keys()[0]

            self._descr.setText(text)

        elif num == 2:

            # Update contents

            self._cont.setText("")
            if not pkg: return

            text = ""
            for loader in pkg.loaders:
                if loader.getInstalled():
                    break
            else:
                loader = pkg.loaders.keys()[0]
            info = loader.getInfo(pkg)
            pathlist = info.getPathList()
            pathlist.sort()
            for path in pathlist:
                text += path+"\n"

            self._cont.setText(text)
            self._cont.adjustSize()

        elif num == 3:

            # Update relations

            if not pkg:
                self._relations.setPackages([])
                return

            self._setRelations(pkg)

        elif num == 4:

            # Update URLs

            self._urls.clear()

            if not pkg:
                return

            items = []
            for loader in pkg.loaders:
                channel = loader.getChannel()
                alias = channel.getAlias()
                info = loader.getInfo(pkg)
                for url in info.getURLs():
                    items.append((alias, sizeToStr(info.getSize(url)), url))

            items.sort()

            lastitem = None
            for item in items:
                if item != lastitem:
                    lastitem = item
                    listitem = qt.QListViewItem(self._urls)
                    listitem.setText(0, item[0])
                    listitem.setText(1, item[1])
                    listitem.setText(2, item[2])

    def _setRelations(self, pkg):

        class Sorter(str):
            ORDER = [_("Provides"), _("Upgrades"),
                     _("Requires"), _("Conflicts")]
            def __cmp__(self, other):
                return cmp(self.ORDER.index(str(self)),
                           self.ORDER.index(str(other)))
            def __lt__(self, other):
                return cmp(self, other) < 0

        relations = {}

        for prv in pkg.provides:

            prvmap = {}
            
            requiredby = []
            for req in prv.requiredby:
                requiredby.extend(req.packages)
            if requiredby:
                prvmap[_("Required By")] = requiredby

            upgradedby = []
            for upg in prv.upgradedby:
                upgradedby.extend(upg.packages)
            if upgradedby:
                prvmap[_("Upgraded By")] = upgradedby

            conflictedby = []
            for cnf in prv.conflictedby:
                conflictedby.extend(cnf.packages)
            if conflictedby:
                prvmap[_("Conflicted By")] = conflictedby

            if prvmap:
                relations.setdefault(Sorter(_("Provides")), {})[str(prv)] = \
                                                                        prvmap

        requires = {}
        for req in pkg.requires:
            lst = requires.setdefault(str(req), [])
            for prv in req.providedby:
                lst.extend(prv.packages)
            lst[:] = dict.fromkeys(lst).keys()
        if requires:
            relations[Sorter(_("Requires"))] = requires

        upgrades = {}
        for upg in pkg.upgrades:
            lst = upgrades.setdefault(str(upg), [])
            for prv in upg.providedby:
                lst.extend(prv.packages)
            lst[:] = dict.fromkeys(lst).keys()
        if upgrades:
            relations[Sorter(_("Upgrades"))] = upgrades

        conflicts = {}
        for cnf in pkg.conflicts:
            lst = conflicts.setdefault(str(cnf), [])
            for prv in cnf.providedby:
                lst.extend(prv.packages)
            lst[:] = dict.fromkeys(lst).keys()
        if conflicts:
            relations[Sorter(_("Conflicts"))] = conflicts

        self._relations.setPackages(relations, self._changeset)

# vim:ts=4:sw=4:et
