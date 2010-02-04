#!/usr/bin/env python
#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
# Ported to Python by Anders F Bjorklund <afb@users.sourceforge.net>
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
import sys
from qt import Qt, QPixmap, QTimer, QObject, QToolTip, \
               SIGNAL, PYSIGNAL, SLOT

from kdecore import KUniqueApplication, KApplication, KCmdLineArgs, \
                    KNotifyClient, KProcess, KProcIO
from kdeui import KSystemTray, KMainWindow, KAction

class KMySystemTray(KSystemTray):

    def __init__(self):
        KSystemTray.__init__(self)
        self.hasActions = False
        self.checkAction = KAction()
        self.checkAction.setText("Check")
        self.startSmartAction = KAction()
        self.startSmartAction.setText("Start Smart...")
        self.stopAction = KAction()
        self.stopAction.setText("Stop")
        self.stopAction.setIcon("stop")
        self.stopAction.setEnabled(False)
    
    def contextMenuAboutToShow(self, menu):
        if not self.hasActions:
            self.hasActions = True
            self.checkAction.plug(menu, 1)
            self.startSmartAction.plug(menu, 2)
            #self.stopAction.plug(menu, 2)
    
    def enterEvent(self, event):
        self.emit(PYSIGNAL("mouseEntered()"), ())
    
    def mousePressEvent(self, event):
        if self.rect().contains(event.pos()):
            if event.button() == Qt.LeftButton:
                self.emit(PYSIGNAL("activated()"), ())
            else:
                KSystemTray.mousePressEvent(self, event)

class KSmartTray(QObject):

    class State:
         Waiting = 'StateWaiting'
         Updating = 'StateUpdating'
         Checking = 'StateChecking'
         Upgrading = 'StateUpgrading'
         RunningSmart = 'StateRunningSmart'

    def __init__(self):
        QObject.__init__(self)
        self.sysTray = KMySystemTray()
        self.sysTray.setPixmap(self.sysTray.loadIcon("ksmarttray"))
        self.sysTray.show()
    
        self.process = KProcIO()
    
        self.state = KSmartTray.State.Waiting
        self.lastKnownStatus = ""
    
        self.blinkFlag = False
        self.updateFailed = False
    
        self.checkTimer = QTimer()
        self.blinkTimer = QTimer()

        QObject.connect(self.checkTimer, SIGNAL("timeout()"), self.checkUpgrades)
        QObject.connect(self.process, SIGNAL("processExited(KProcess *)"),
                self.processDone)
    
        QObject.connect(self, PYSIGNAL("foundNewUpgrades()"), self.startBlinking)
        QObject.connect(self, PYSIGNAL("foundNoUpgrades()"), self.stopBlinking)
        QObject.connect(self.sysTray, PYSIGNAL("mouseEntered()"), self.stopBlinking)
        QObject.connect(self.blinkTimer, SIGNAL("timeout()"), self.toggleBlink)
    
        QObject.connect(self.sysTray.checkAction, SIGNAL("activated()"),
                self.manualCheckUpgrades)
        QObject.connect(self.sysTray.startSmartAction, SIGNAL("activated()"),
                self.startSmart)
        QObject.connect(self.sysTray.stopAction, SIGNAL("activated()"),
                self.stopChecking)
        QObject.connect(self.sysTray, SIGNAL("quitSelected()"),
                KApplication.kApplication(), SLOT("quit()"))
    
        QObject.connect(self.sysTray, PYSIGNAL("activated()"), self.runUpgrades)
    
        self.checkTimer.start(5*60*1000)
    
        self.checkUpgrades()
    
    def internalCheckUpgrades(self, manual):
        if not manual and self.blinkTimer.isActive():
            return
        if self.state == KSmartTray.State.Waiting:
            self.sysTray.checkAction.setEnabled(False)
            self.sysTray.startSmartAction.setEnabled(False)
            self.sysTray.stopAction.setEnabled(True)
            self.process.resetAll()
            if manual:
                self.process.setArguments(["smart-update"])
            else:
                self.process.setArguments(["smart-update", "--after", "60"])
            if not self.process.start():
                KNotifyClient.event(self.sysTray.winId(), "fatalerror",
                                     "Couldn't run 'smart-update'.")
            else:
                QToolTip.add(self.sysTray, "Updating channels...")
                self.state = KSmartTray.State.Updating
    
    def checkUpgrades(self):
        self.internalCheckUpgrades(False)
    
    def manualCheckUpgrades(self):
        self.internalCheckUpgrades(True)
    
    def runUpgrades(self):
        if self.state != KSmartTray.State.Waiting:
            KNotifyClient.event(self.sysTray.winId(), "fatalerror",
                                 "There is a running process.")
        else:
            self.sysTray.checkAction.setEnabled(False)
            self.sysTray.startSmartAction.setEnabled(False)
            self.sysTray.stopAction.setEnabled(False)
            self.process.resetAll()
            self.process.setArguments(["kdesu", "-d", "-c", "smart --gui upgrade"])
            if not self.process.start():
                KNotifyClient.event(self.sysTray.winId(), "fatalerror",
                                     "Couldn't run 'smart upgrade'.")
            else:
                self.state = KSmartTray.State.Upgrading
                QToolTip.remove(self.sysTray)
                QToolTip.add(self.sysTray, "Running Smart Package Manager...")
    
    def startSmart(self):
        if self.state != KSmartTray.State.Waiting:
            KNotifyClient.event(self.sysTray.winId(), "fatalerror",
                                 "There is a running process.")
        else:
            self.sysTray.checkAction.setEnabled(False)
            self.sysTray.startSmartAction.setEnabled(False)
            self.sysTray.stopAction.setEnabled(False)
            self.process.resetAll()
            self.process.setArguments(["kdesu", "-d", "-c", "smart --gui"])
            if not self.process.start():
                KNotifyClient.event(self.sysTray.winId(), "fatalerror",
                                     "Couldn't run 'smart'.")
            else:
                self.state = KSmartTray.State.RunningSmart
                QToolTip.remove(self.sysTray)
                QToolTip.add(self.sysTray, "Running Smart Package Manager...")
    
    def stopChecking(self):
        self.process.kill()
    
    def processDone(self, process):
        if self.state == KSmartTray.State.Updating:
            if not process.normalExit() or process.exitStatus() != 0:
                self.updateFailed = True
            if self.updateFailed and not self.lastKnownStatus == "":
                self.state = KSmartTray.State.Waiting
            else:
                process.resetAll()
                process.setArguments(["smart", "upgrade", "--check-update"])
                if not process.start():
                    KNotifyClient.event(self.sysTray.winId(), "fatalerror",
                                         "Couldn't run 'smart upgrade'.")
                    self.state = KSmartTray.State.Waiting
                    self.lastKnownStatus = ""
                else:
                    QToolTip.remove(self.sysTray)
                    QToolTip.add(self.sysTray,
                                  "Verifying upgradable packages...")
                    self.state = KSmartTray.State.Checking
        elif self.state == KSmartTray.State.Checking:
            self.state = KSmartTray.State.Waiting
            if process.normalExit():
                if process.exitStatus() == 0:
                    self.lastKnownStatus = "There are new upgrades available!"
                    KNotifyClient.event(self.sysTray.winId(), "found-new-upgrades",
                                         self.lastKnownStatus)
                    self.emit(PYSIGNAL("foundNewUpgrades()"), ())
                elif process.exitStatus() == 1:
                    self.lastKnownStatus = "There are pending upgrades!"
                    if not self.updateFailed:
                        KNotifyClient.event(self.sysTray.winId(),
                                             "found-old-upgrades",
                                             self.lastKnownStatus)
                    self.emit(PYSIGNAL("foundOldUpgrades()"), ())
                elif process.exitStatus() == 2:
                    self.lastKnownStatus = "No interesting upgrades available."
                    if not self.updateFailed:
                        KNotifyClient.event(self.sysTray.winId(),
                                             "found-no-upgrades",
                                             self.lastKnownStatus)
                    self.emit(PYSIGNAL("foundNoUpgrades()"), ())
                else:
                    self.lastKnownStatus = ""
        elif self.state == KSmartTray.State.Upgrading:
            self.state = KSmartTray.State.Waiting
            self.lastKnownStatus = ""
        elif self.state ==  KSmartTray.State.RunningSmart:
            self.state = KSmartTray.State.Waiting
            self.lastKnownStatus = ""
        else:
            # Error!
            pass

        if self.state == KSmartTray.State.Waiting:
            self.updateFailed = False
            self.sysTray.checkAction.setEnabled(True)
            self.sysTray.startSmartAction.setEnabled(True)
            self.sysTray.stopAction.setEnabled(False)
            if not self.lastKnownStatus == "":
                QToolTip.remove(self.sysTray)
                QToolTip.add(self.sysTray, self.lastKnownStatus)
            else:
                QToolTip.remove(self.sysTray)
    
    def startBlinking(self):
        if not self.blinkTimer.isActive():
            self.blinkTimer.start(500)
    
    def stopBlinking(self):
        if self.blinkTimer.isActive():
            self.blinkTimer.stop()
        self.sysTray.setPixmap(self.sysTray.loadIcon("ksmarttray"))
    
    def toggleBlink(self):
        if self.blinkFlag:
            self.sysTray.setPixmap(QPixmap())
        else:
            self.sysTray.setPixmap(self.sysTray.loadIcon("ksmarttray"))
        self.blinkFlag = not self.blinkFlag

def main(argv):
    KCmdLineArgs.init(argv, "ksmarttray", "KSmartTray", "", "")
    app = KUniqueApplication(True, True, False)
    app.dirs().addResourceDir("appicon", app.applicationDirPath())
    smarttray = KSmartTray()
    app.exec_loop()

if __name__ == "__main__":
    main(sys.argv)
