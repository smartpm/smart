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
        self._window = None

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

    def askYesNo(self, question, default=False):
        dialog = gtk.MessageDialog(parent=self._window,
                                   flags=gtk.DIALOG_MODAL,
                                   type=gtk.MESSAGE_QUESTION,
                                   buttons=gtk.BUTTONS_YES_NO,
                                   message_format=question+"?")
        dialog.set_default_response(default and gtk.RESPONSE_YES
                                             or gtk.RESPONSE_NO)
        response = dialog.run()
        dialog.destroy()
        print response
        if response == gtk.RESPONSE_YES:
            return True
        elif response == gtk.RESPONSE_NO:
            return False
        else:
            return default

    def askContCancel(self, question, default=False):
        return self.askYesNo(question+". Continue", default)

    def askOkCancel(self, question, default=False):
        dialog = gtk.MessageDialog(parent=self._window,
                                   flags=gtk.DIALOG_MODAL,
                                   type=gtk.MESSAGE_INFO,
                                   buttons=gtk.BUTTONS_OK_CANCEL,
                                   message_format=question+".")
        dialog.set_default_response(default and gtk.RESPONSE_OK
                                             or gtk.RESPONSE_CANCEL)
        response = dialog.run()
        dialog.destroy()
        print response
        if response == gtk.RESPONSE_OK:
            return True
        elif response == gtk.RESPONSE_CANCEL:
            return False
        else:
            return default

    def message(self, level, msg):
        self._log.message(level, msg)

    def confirmChange(self, oldchangeset, newchangeset, expected=1):
        changeset = newchangeset.difference(oldchangeset)
        keep = []
        for pkg in oldchangeset:
            if pkg not in newchangeset:
                keep.append(pkg)
        if len(keep)+len(changeset) <= expected:
            return True
        return self._changes.showChangeSet(changeset, keep=keep, confirm=True)

    def confirmTransaction(self, trans):
        return self._changes.showChangeSet(trans.getChangeSet(), confirm=True)

    # Non-standard interface methods

    def hideProgress(self):
        self._progress.hide()
        self._hassubprogress.hide()

