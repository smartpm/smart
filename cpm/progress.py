import thread
import time
import sys

INTERVAL = 0.1

class Progress:

    def __init__(self):
        self._topic = ""
        self._progress = (0, 0, {}) # (current, total, data)
        self._lastshown = None
        self._hassub = False
        self._subtopic = {}
        self._subprogress = {} # (subcurrent, subtotal, fragment, subdata)
        self._sublastshown = {}
        self._subdone = {}
        self._lasttime = 0
        self._lock = thread.allocate_lock()

    def start(self, hassub=False):
        self._hassub = hassub

    def stop(self):
        self._topic = ""
        self._progress = (0, 0, {})
        self._lastshown = None
        self._subtopic.clear()
        self._subprogress.clear()
        self._sublastshown.clear()
        self._subdone.clear()
        self._lasttime = 0

    def show(self):
        now = time.time()
        if self._lasttime > now-INTERVAL:
            return
        self._lock.acquire()
        self._lasttime = now
        current, total, data = self._progress
        subexpose = []
        for subkey in self._subprogress.keys():
            subcurrent, subtotal, fragment, subdata = self._subprogress[subkey]
            subpercent = int(100*float(subcurrent)/(subtotal or 1))
            if fragment:
                current += int(fragment*float(subpercent)/100)
            subtopic = self._subtopic.get(subkey)
            if (subtopic, subpercent) == self._sublastshown.get(subkey):
                continue
            self._sublastshown[subkey] = (subtopic, subpercent)
            if subpercent == 100:
                if fragment:
                    _current, _total, _data = self._progress
                    self._progress = (_current+fragment, _total, _data)
                    if _current == _total:
                        self._lasttime = 0
                self._subdone[subkey] = True
                del self._subprogress[subkey]
                del self._sublastshown[subkey]
                del self._subtopic[subkey]
            subexpose.append((subkey, subtopic, subpercent, subdata))
        topic = self._topic
        percent = int(100*float(current)/(total or 1))
        if subexpose:
            for info in subexpose:
                self.expose(topic, percent, *info)
            self.expose(topic, percent, None, None, None, data)
        elif (topic, percent) != self._lastshown:
            self.expose(topic, percent, None, None, None, data)
        self._lock.release()

    def expose(self, topic, percent, subkey, subtopic, subpercent, data):
        pass

    def setTopic(self, topic):
        self._topic = topic

    def set(self, current, total, data={}):
        self._lock.acquire()
        if current > total:
            current = total
        self._progress = (current, total, data)
        if current == total:
            self._lasttime = 0
        self._lock.release()

    def add(self, value):
        self._lock.acquire()
        current, total, data = self._progress
        current += value
        if current > total:
            current = total
        self._progress = (current, total, data)
        if current == total:
            self._lasttime = 0
        self._lock.release()

    def addTotal(self, value):
        self._lock.acquire()
        current, total, data = self._progress
        self._progress = (current, total+value, data)
        self._lock.release()

    def setSubTopic(self, subkey, subtopic):
        self._lock.acquire()
        if subkey not in self._subtopic:
            self._lasttime = 0
        self._subtopic[subkey] = subtopic
        self._lock.release()

    def setSub(self, subkey, subcurrent, subtotal, fragment=0, subdata={}):
        self._lock.acquire()
        if subkey in self._subdone:
            self._lock.release()
            return
        if subkey not in self._subtopic:
            self._subtopic[subkey] = ""
            self._lasttime = 0
        if subcurrent > subtotal:
            subcurrent = subtotal
        if subcurrent == subtotal:
            self._lasttime = 0
        self._subprogress[subkey] = (subcurrent, subtotal, fragment, subdata)
        self._lock.release()

    def addSub(self, subkey, value):
        self._lock.acquire()
        if subkey in self._subdone:
            self._lock.release()
            return
        subcurrent, subtotal, fragment, subdata = self._subprogress[subkey]
        subcurrent += value
        if subcurrent > subtotal:
            subcurrent = subtotal
        self._subprogress[subkey] = (subcurrent, subtotal, fragment, subdata)
        if subcurrent == subtotal:
            self._lasttime = 0
        self._lock.release()

    def addSubTotal(self, subkey, value):
        self._lock.acquire()
        if subkey in self._subdone:
            self._lock.release()
            return
        subcurrent, subtotal, fragment, subdata = self._subprogress[subkey]
        self._subprogress[subkey] = (subcurrent, subtotal+value,
                                     fragment, subdata)
        self._lock.release()

    def setDone(self):
        self._lock.acquire()
        current, total, data = self._progress
        self._progress = (total, total, data)
        for subkey in self._subprogress:
            subcurrent, subtotal, fragment, subdata = self._subprogress[subkey]
            if subcurrent != subtotal:
                self._subprogress[subkey] = (subtotal, subtotal,
                                             fragment, subdata)
        self._lasttime = 0
        self._lock.release()

    def setSubDone(self, subkey):
        self._lock.acquire()
        if subkey in self._subdone:
            self._lock.release()
            return
        subcurrent, subtotal, fragment, subdata = self._subprogress[subkey]
        if subcurrent != subtotal:
            self._subprogress[subkey] = (subtotal, subtotal, fragment, subdata)
        self._lasttime = 0
        self._lock.release()

    def resetSub(self, subkey):
        self._lock.acquire()
        if subkey in self._subdone:
            del self._subdone[subkey]
        if subkey in self._subprogress:
            del self._subprogress[subkey]
        self._lasttime = 0
        self._lock.release()

# vim:ts=4:sw=4:et
