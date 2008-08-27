#
# Copyright (c) 2006 FoXLinux.org
#
# Written by Luca Ferrari <luka4e@foxlinux.org>
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
from smart.interface import getScreenWidth
from smart.util.strtools import ShortURL, sizeToStr
from smart.progress import Progress, INTERVAL
import posixpath
import time
import sys
import thread
from qt import *

class QtProgress(Progress):

    #def __init__(self):
        #Progress.__init__(self)
        #self._lasttopic = None
        #self._lastsubkey = None
        #self._lastsubkeystart = 0
        #self._fetchermode = False
        #self._seentopics = {}
        #self._addline = False
        #self.setScreenWidth(getScreenWidth())

    def __init__(self, hassub):
	Progress.__init__(self)
        self.win = QWidget(None, "Progress",Qt.WType_Dialog  )
        self.win.setName("Progress")
	
        self._lasttopic = None
        self._lastsubkey = None
        self._lastsubkeystart = 0
        self._fetchermode = False
        self._seentopics = {}
        self._addline = False
	self._subiters = {}
	self._shorturl = ShortURL(50)
	self._hassub = hassub

	

	#aggiungo il movie dal file png
        self.win.movie = QMovie("reload.mng")
	self.win.iconwait = QLabel(self.win,"Wait")
	#self.win.iconwait.setPixmap( QPixmap("info.png"))
	self.win.iconwait.setMovie(self.win.movie)


        ProgressFormLayout = QGridLayout(self.win,1,1,11,6,"ProgressFormLayout")
        spacer1 = QSpacerItem(391,21,QSizePolicy.Expanding,QSizePolicy.Minimum)
        ProgressFormLayout.addMultiCell(spacer1,3,3,2,3)
        spacer2 = QSpacerItem(431,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        ProgressFormLayout.addMultiCell(spacer2,5,5,0,2)

        self.win.pleaseWaitLabel = QLabel(self.win,"pleaseWaitLabel")
        self.win.pleaseWaitLabel.setAlignment(QLabel.WordBreak | QLabel.AlignVCenter)
	self.win.pleaseWaitLabel.setText("Please wait, operation in progress...")

        ProgressFormLayout.addMultiCellWidget(self.win.pleaseWaitLabel,0,0,0,3)

        self.win.mainStepLabel = QLabel(self.win,"mainStepLabel")
	self.win.mainStepLabel.setText("Main step label")

        ProgressFormLayout.addMultiCellWidget(self.win.mainStepLabel,1,1,1,3)

        ProgressFormLayout.addMultiCellWidget(self.win.iconwait,1,2,0,0)

        self.win.mainProgressBar = QProgressBar(self.win,"mainProgressBar")

        ProgressFormLayout.addMultiCellWidget(self.win.mainProgressBar,2,2,1,3)

	#se ci sono sottoprocessi
	if hassub:
		self.win.showHideDetailsBtn = QPushButton(self.win,"Show details")
		self.win.showHideDetailsBtn.setText("Show details")
		QObject.connect(self.win.showHideDetailsBtn, SIGNAL ("clicked()"), self.setStepListViewVisible)
        	ProgressFormLayout.addMultiCellWidget(self.win.showHideDetailsBtn,3,3,0,1)

        	self.win.cancelBtn = QPushButton(self.win,"cancelBtn")
		self.win.cancelBtn.setText("Cancel")
		QObject.connect(self.win.cancelBtn, SIGNAL ("clicked()"), self._cancel)
        	ProgressFormLayout.addWidget(self.win.cancelBtn,5,3)

        	self.win.stepListView = QListView(self.win,"stepListView")
		self.win.stepListView.setSorting(-1, False);
		self.win.stepListView.setSelectionMode(QListView.NoSelection )
		#creo le colonne per la lista
	
		self.win.stepListView.addColumn("Subpercent")
		self.win.stepListView.addColumn("Current")
		self.win.stepListView.addColumn("Total")
		self.win.stepListView.addColumn("Speed")
		self.win.stepListView.addColumn("Description")
		self.win.stepListView.hideColumn(1)		
		self.win.stepListView.hideColumn(2)
		self.win.stepListView.hideColumn(3)
		
        	ProgressFormLayout.addMultiCellWidget(self.win.stepListView,4,4,0,3)
		self.win.stepListView.show()
		self.setStepListViewVisible()

	
    def setFetcherMode(self, flag):
        self._fetchermode = flag


    def setStepListViewVisible(self):
	toShow = not self.win.stepListView.isVisible()
	
	if toShow:
	    self.win.stepListView.show()
	    self.win.showHideDetailsBtn.setText("Hide details")
	else:
	    self.win.stepListView.hide()
	    self.win.showHideDetailsBtn.setText("Show details")

    def _cancel(self):
        if self._fetcher:
            self._fetcher.cancel()

    def setFetcher(self, fetcher):
        if fetcher:
            self.win.cancelBtn.show()
            self._fetcher = fetcher
        else:
            self.win.cancelBtn.hide()
            self._fetcher = None

    def tick(self):
        while not self._stopticking:
           self.lock()
           while QApplication.eventLoop().hasPendingEvents():
		   QApplication.eventLoop().processEvents(QEventLoop.AllEvents)
           self.unlock()
           time.sleep(INTERVAL)
        self._ticking = False


    def start(self):
        Progress.start(self)
        self.setHasSub(self._hassub)
        self._ticking = True
        self._stopticking = False
        if self._hassub:
            self.setStepListViewVisible()
	
        thread.start_new_thread(self.tick, ())

	
	
    def stop(self):
        self._stopticking = True
        while self._ticking: pass

        Progress.stop(self)

        if self._hassub:
            self.win.stepListView.clear()
	    self._subiters.clear()
            self._subindex = 0
            self._lastpath = None

        self._shorturl.reset()
        self.hide()
	#QApplication.eventLoop().exit()
	
	
    def hide(self):
	QWidget.close(self.win)
	

    def expose(self, topic, percent, subkey, subtopic, subpercent, data, done):
	#print '\n\n\nexpose richiamato'    
	#print "topic= " +topic
	#print "percent= " + str(percent)
	#print "subkey= " + str(subkey)
	#print "subtopic= " + str(subtopic)
	#print "subpercent= " + str(subpercent)
	#print "data= " + str(data)
	#print "done= " + str(done)
	
	QWidget.show(self.win)
	if self._hassub and subkey:
	    #metto a posto i sottoprocessi	
            if subkey in self._subiters:
		#se il sottoprocesso e gia stato analizzato lo prendo dal dizionario
                iter = self._subiters[subkey]
		
            else:
		#altrimenti ne aggiungo uno alla lista
                #iter = self._treemodel.append()
		
		#creo l'elemento
		iter = QListViewItem(self.win.stepListView)
		
		#lo aggiungo al dizionario
                self._subiters[subkey] = iter
		
		
                #path = self._treemodel.get_path(iter)
                #if self._lastpath:
                    #column = self._treeview.get_column(1)
                    #cellarea = self._treeview.get_cell_area(self._lastpath,
                                                            #column)
                    #cellarea.x, cellarea.y = self._treeview.\
                                             #widget_to_tree_coords(cellarea.x,
                                                                   #cellarea.y)
                    #visiblearea = self._treeview.get_visible_rect()
                    #isvisible = visiblearea.intersect(cellarea).height
                #if not self._lastpath or isvisible:
                    #self._treeview.scroll_to_cell(path, None, True, 0, 0)
                #self._lastpath = path

            current = data.get("current", "")
            if current:
                self.win.stepListView.setColumnWidth(1, 30)
				
            total = data.get("total", "")
            if total:
                self.win.stepListView.setColumnWidth(2, 30)
		
            speed = data.get("speed", "")
            if speed:
                self.win.stepListView.setColumnWidth(3, 30)
		
            if current or total or speed:
		iter.setText(1, current)
	        iter.setText(2, total)
	        iter.setText(3, speed)    

                subtopic = self._shorturl.get(subtopic)
		
	    iter.setText(4, subtopic)
	    iter.setText(0, str(subpercent))
	    #print subtopic

	    #aggiungo alla listview l'elemento
	    self.win.stepListView.insertItem(iter)
        else:
            self.win.mainStepLabel.setText('<b>'+topic+'</b>')
	    self.win.mainProgressBar.setProgress(percent, 100)
            #self._progress.set_fraction(percent/100.)
            #self._progress.set_text("%d%%" % percent)
            if self._hassub:
                self.win.stepListView.repaint()
	
	self.win.update()
	QApplication.eventLoop().processEvents(QEventLoop.AllEvents)
		

    

def test():
    data = {"item-number": 0}
    total, subtotal = 20, 5
    prog = QtProgress(True)
    
    prog.start()
    prog.setTopic("Installing packages...")
    for n in range(1,total+1):
        data["item-number"] = n
        prog.set(n, total)
        prog.setSubTopic(n, "package-name%d" % n)
        for i in range(0,subtotal+1):
            prog.setSub(n, i, subtotal, subdata=data)
            prog.show()
            time.sleep(0.1)
    prog.stop()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    test()
    #prog = QtProgress(True)
    #prog.win.show()
    #app.connect(app, SIGNAL('lastWindowClosed()'), app, SLOT('quit()'))
    ##test()
    #thread.start_new_thread(test, ())
    #app.exec_loop()
    
    

# vim:ts=4:sw=4:et
