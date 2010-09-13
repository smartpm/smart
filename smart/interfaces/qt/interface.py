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
from smart.interfaces.qt.progress import QtProgress
from smart.interfaces.qt.changes import QtChanges
from smart.interfaces.qt.log import QtLog
from smart.interface import Interface, getScreenWidth
from smart.fetcher import Fetcher
from smart.const import DEBUG
from smart import *
import qt
import sys


app = qt.QApplication(sys.argv)

class QtInterface(Interface):

    def _currentThread(self):
        if hasattr(qt, 'QThread'):
            return qt.QThread.currentThread()
        else:
            return None

    def __init__(self, ctrl, argv):
        Interface.__init__(self, ctrl)
        self._log = QtLog()
        self._progress = QtProgress(False)
        self._progress.setMainThread(self._currentThread())
        self._hassubprogress = QtProgress(True)
        self._hassubprogress.setMainThread(self._currentThread())
        self._changes = QtChanges()
        self._window = None
        self._sys_excepthook = sys.excepthook

    def run(self, command=None, argv=None):
        self.setCatchExceptions(True)
        result = Interface.run(self, command, argv)
        self.setCatchExceptions(False)
        return result

    def eventsPending(self):
        return qt.QApplication.eventLoop().hasPendingEvents()

    def processEvents(self):
        qt.QApplication.eventLoop().processEvents(qt.QEventLoop.AllEvents)

    def getProgress(self, obj, hassub=False):
        if hassub:
            self._progress.hide()
            fetcher = isinstance(obj, Fetcher) and obj or None
            self._hassubprogress.setFetcher(fetcher)
            return self._hassubprogress
        else:
            self._hassubprogress.hide()
            return self._progress

    def getSubProgress(self, obj):
        return self._hassubprogress

    def askYesNo(self, question, default=False):
        response = qt.QMessageBox.question(self._window,
                                        _("Question..."),
                                        question,
                                        qt.QMessageBox.Yes,
                                        qt.QMessageBox.No)


        if response == qt.QMessageBox.Yes:
            return True
        elif response == qt.QMessageBox.No:
            return False
        else:
            return default

    def askContCancel(self, question, default=False):
        response = qt.QMessageBox.question(self._window,
                                   _("Question..."),
                                   question,
                                   _("Continue"),
                                   _("Cancel"),
                                   )

        #response.setButtonText(QMessageBox.Ok, )
        
        if response == 0:
            return True
        elif response == 1:
            return False
        else:
            return default

    def askOkCancel(self, question, default=False):
        response = qt.QMessageBox.question(self._window,
                                   _("Question..."),
                                   question,
                                   qt.QMessageBox.Ok,
                                   qt.QMessageBox.Cancel)

        
        if response == qt.QMessageBox.Ok:
            return True
        elif response == qt.QMessageBox.Cancel:
            return False
        else:
            return default

    def askInput(self, prompt, message=None, widthchars=40, echo=True):
        if (message != None):
            stringToShow = message + "\n" + prompt
        else:
            stringToShow = prompt
        if echo:
            echoMode = qt.QLineEdit.Normal
        else:
            echoMode = qt.QLineEdit.Password

        text, ok = qt.QInputDialog.getText( _("Input"), stringToShow, echoMode)
                
        if (ok and text != None):
            return text[0:widthchars]
        else:
            return ""

    def insertRemovableChannels(self, channels):
        question = _("Insert one or more of the following removable "
                     "channels:\n")
        question += "\n"
        for channel in channels:
            question += "    "
            question += channel.getName()
            question += "\n"
        return self.askOkCancel(question, default=True)

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

    def confirmChangeSet(self, changeset):
        return self._changes.showChangeSet(changeset, confirm=True)

    # Non-standard interface methods

    def _excepthook(self, type, value, tb):
        if issubclass(type, Error) and not sysconf.get("log-level") is DEBUG:
            self._hassubprogress.hide()
            self._progress.hide()
            iface.error(unicode(value[0]))
        else:
            import traceback
            lines = traceback.format_exception(type, value, tb)
            iface.error("\n".join(lines))

    def setCatchExceptions(self, flag):
        if flag:
            sys.excepthook = self._excepthook
        else:
            sys.excepthook = self._sys_excepthook

    def hideProgress(self):
        self._progress.hide()
        self._hassubprogress.hide()


# vim:ts=4:sw=4:et
