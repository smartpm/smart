import thread
import time
import sys

INTERVAL = 0.1

class Progress:

    def __init__(self):
        self.__topic = ""
        self.__progress = (0, 0, {}) # (current, total, data)
        self.__lastshown = None
        self.__subtopic = {}
        self.__subprogress = {} # (subcurrent, subtotal, fragment, subdata)
        self.__sublastshown = {}
        self.__subdone = {}
        self.__lasttime = 0
        self.__lock = thread.allocate_lock()
        self._hassub = False

    def start(self, hassub=False):
        self._hassub = hassub

    def stop(self):
        self.__topic = ""
        self.__progress = (0, 0, {})
        self.__lastshown = None
        self.__subtopic.clear()
        self.__subprogress.clear()
        self.__sublastshown.clear()
        self.__subdone.clear()
        self.__lasttime = 0

    def show(self):
        now = time.time()
        if self.__lasttime > now-INTERVAL:
            return
        self.__lock.acquire()
        self.__lasttime = now
        current, total, data = self.__progress
        subexpose = []
        for subkey in self.__subprogress.keys():
            subcurrent, subtotal, fragment, subdata = self.__subprogress[subkey]
            subpercent = int(100*float(subcurrent)/(subtotal or 1))
            if fragment:
                current += int(fragment*float(subpercent)/100)
            subtopic = self.__subtopic.get(subkey)
            if (subtopic, subpercent) == self.__sublastshown.get(subkey):
                continue
            self.__sublastshown[subkey] = (subtopic, subpercent)
            if subpercent == 100:
                if fragment:
                    _current, _total, _data = self.__progress
                    self.__progress = (_current+fragment, _total, _data)
                    if _current == _total:
                        self.__lasttime = 0
                self.__subdone[subkey] = True
                del self.__subprogress[subkey]
                del self.__sublastshown[subkey]
                del self.__subtopic[subkey]
            subexpose.append((subkey, subtopic, subpercent, subdata))
        topic = self.__topic
        percent = int(100*float(current)/(total or 1))
        if subexpose:
            for info in subexpose:
                self.expose(topic, percent, *info)
            self.expose(topic, percent, None, None, None, data)
        elif (topic, percent) != self.__lastshown:
            self.expose(topic, percent, None, None, None, data)
        self.__lock.release()

    def expose(self, topic, percent, subkey, subtopic, subpercent, data):
        pass

    def setTopic(self, topic):
        self.__topic = topic

    def set(self, current, total, data={}):
        self.__lock.acquire()
        if current > total:
            current = total
        self.__progress = (current, total, data)
        if current == total:
            self.__lasttime = 0
        self.__lock.release()

    def add(self, value):
        self.__lock.acquire()
        current, total, data = self.__progress
        current += value
        if current > total:
            current = total
        self.__progress = (current, total, data)
        if current == total:
            self.__lasttime = 0
        self.__lock.release()

    def addTotal(self, value):
        self.__lock.acquire()
        current, total, data = self.__progress
        self.__progress = (current, total+value, data)
        self.__lock.release()

    def setSubTopic(self, subkey, subtopic):
        self.__lock.acquire()
        if subkey not in self.__subtopic:
            self.__lasttime = 0
        self.__subtopic[subkey] = subtopic
        self.__lock.release()

    def setSub(self, subkey, subcurrent, subtotal, fragment=0, subdata={}):
        self.__lock.acquire()
        if subkey in self.__subdone:
            self.__lock.release()
            return
        if subkey not in self.__subtopic:
            self.__subtopic[subkey] = ""
            self.__lasttime = 0
        if subcurrent > subtotal:
            subcurrent = subtotal
        if subcurrent == subtotal:
            self.__lasttime = 0
        self.__subprogress[subkey] = (subcurrent, subtotal, fragment, subdata)
        self.__lock.release()

    def addSub(self, subkey, value):
        self.__lock.acquire()
        if subkey in self.__subdone:
            self.__lock.release()
            return
        subcurrent, subtotal, fragment, subdata = self.__subprogress[subkey]
        subcurrent += value
        if subcurrent > subtotal:
            subcurrent = subtotal
        self.__subprogress[subkey] = (subcurrent, subtotal, fragment, subdata)
        if subcurrent == subtotal:
            self.__lasttime = 0
        self.__lock.release()

    def addSubTotal(self, subkey, value):
        self.__lock.acquire()
        if subkey in self.__subdone:
            self.__lock.release()
            return
        subcurrent, subtotal, fragment, subdata = self.__subprogress[subkey]
        self.__subprogress[subkey] = (subcurrent, subtotal+value,
                                     fragment, subdata)
        self.__lock.release()

    def setDone(self):
        self.__lock.acquire()
        current, total, data = self.__progress
        self.__progress = (total, total, data)
        for subkey in self.__subprogress:
            subcurrent, subtotal, fragment, subdata = self.__subprogress[subkey]
            if subcurrent != subtotal:
                self.__subprogress[subkey] = (subtotal, subtotal,
                                             fragment, subdata)
        self.__lasttime = 0
        self.__lock.release()

    def setSubDone(self, subkey):
        self.__lock.acquire()
        if subkey in self.__subdone:
            self.__lock.release()
            return
        subcurrent, subtotal, fragment, subdata = self.__subprogress[subkey]
        if subcurrent != subtotal:
            self.__subprogress[subkey] = (subtotal, subtotal, fragment, subdata)
        self.__lasttime = 0
        self.__lock.release()

    def resetSub(self, subkey):
        self.__lock.acquire()
        if subkey in self.__subdone:
            del self.__subdone[subkey]
        if subkey in self.__subprogress:
            del self.__subprogress[subkey]
        self.__lasttime = 0
        self.__lock.release()

# vim:ts=4:sw=4:et
