import thread
import time
import sys

INTERVAL = 0.1

class Progress:

    def __init__(self):
        self.reset()

    def reset(self):
        self._topic = ""
        self._progress = None # (current, total, data)
        self._lastshown = None
        self._subtopic = {}
        self._subprogress = {} # (subcurrent, subtotal, fragment, subdata)
        self._sublastshown = {}
        self._subdone = {}
        self._lasttime = 0
        self._lock = thread.allocate_lock()

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
            subpercent = int(100*float(subcurrent)/subtotal)
            if fragment:
                current += int(fragment*float(subpercent)/100)
            subtopic = self._subtopic.get(subkey)
            if (subtopic, subpercent) == self._sublastshown.get(subkey):
                continue
            self._sublastshown[subkey] = (subtopic, subpercent)
            if subpercent == 100:
                if fragment and current != total:
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
        percent = int(100*float(current)/total)
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
        self._progress = (current, total, data)
        if current == total:
            self._lasttime = 0
        self._lock.release()

    def add(self, value):
        self._lock.acquire()
        current, total, data = self._progress
        self._progress = (current+value, total, data)
        if current == total:
            self._lasttime = 0
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
        self._subprogress[subkey] = (subcurrent+value, subtotal,
                                     fragment, subdata)
        if subcurrent == subtotal:
            self._lasttime = 0
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

class RPMStyleProgress(Progress):

    HASHES = 44

    def __init__(self):
        Progress.__init__(self)
        self._lasttopic = None
        self._lastsubkey = None
        self._lastsubkeytime = 0

    def expose(self, topic, percent, subkey, subtopic, subpercent, data):
        out = sys.stdout
        if subkey:
            if topic != self._lasttopic:
                self._lasttopic = topic
                print topic
            if subpercent != 100:
                now = time.time()
                if subkey == self._lastsubkey:
                    if (self._lastsubkeytime+2 < now and
                        len(self._subprogress) > 1):
                        return
                else:
                    if (self._lastsubkeytime+2 > now and
                        len(self._subprogress) > 1):
                        return
                    self._lastsubkey = subkey
                    self._lastsubkeytime = now
            elif subkey == self._lastsubkey:
                    self._lastsubkeytime = 0
            current = subpercent
            topic = subtopic
        elif not self._subprogress and not self._subdone:
            current = percent
        else:
            return
        hashes = int(self.HASHES*current/100)
        n = data.get("item-number")
        if n:
            if len(topic) > 22:
                topic = topic[:20]+".."
            out.write("%4d:%-23.23s" % (n, topic))
        else:
            if len(topic) > 27:
                topic = topic[:25]+".."
            out.write("%-28.28s" % topic)
        out.write("#"*hashes)
        out.write(" "*(self.HASHES-hashes+1))
        if current != 100:
            out.write("(%3d%%)\r" % current)
        elif subpercent is None:
            out.write("[100%]\n")
        else:
            out.write("[%3d%%]\n" % percent)
        out.flush()

def test():
    prog = RPMStyleProgress()
    data = {"item-number": 0}
    total, subtotal = 100, 1000
    prog.setTopic("Installing packages...")
    for n in range(1,total+1):
        data["item-number"] = n
        prog.set(n, total)
        prog.setSubTopic(n, "package-name%d" % n)
        for i in range(0,subtotal+1):
            prog.setSub(n, i, subtotal, subdata=data)
            prog.show()
            #time.sleep(0.02)

if __name__ == "__main__":
    test()

# vim:ts=4:sw=4:et
