#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Gepeto.
#
# Gepeto is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gepeto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gepeto; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from gepeto.interfaces.gtk.progress import GtkProgress
from gepeto.interfaces.gtk.changes import GtkChanges
from gepeto.interfaces.gtk.log import GtkLog
from gepeto.interface import Interface
from gepeto.fetcher import Fetcher
import gtk

class GtkInterface(Interface):

    def __init__(self):
        self._log = GtkLog()
        self._progress = GtkProgress(False)
        self._hassubprogress = GtkProgress(True)
        self._changes = GtkChanges()

    def getProgress(self, obj, hassub=False):
        if hassub:
            self._progress.hide()
            self._hassubprogress.setFetcherMode(isinstance(obj, Fetcher))
            return self._hassubprogress
        else:
            self._hassubprogress.hide()
            return self._progress

    def getSubProgress(self, obj):
        return self._hassubprogress

    def message(self, level, msg):
        self._log.message(level, msg)

    def confirmChange(self, oldchangeset, newchangeset):
        changeset = newchangeset.difference(oldchangeset)
        keep = []
        for pkg in oldchangeset:
            if pkg not in newchangeset:
                keep.append(pkg)
        if len(keep)+len(changeset) <= 1:
            return True
        return self._changes.showChangeSet(changeset, keep=keep, confirm=True)

    def confirmTransaction(self, trans):
        return self._changes.showChangeSet(trans.getChangeSet(), confirm=True)

    # Non-standard interface methods

    def hideProgress(self):
        self._progress.hide()
        self._hassubprogress.hide()

