import sys

class Progress:
    def __init__(self):
        self._hooks = []
        self.reset()

    def reset(self):
        self._topic = ""
        self._total = 0
        self._current = 0
        self._subcurrent = 0
        self._subtotal = 0
        self._fragment = 0
        self._lastshown = None
        self._data = {}

    def show(self):
        info = self.getInfo()
        if self._lastshown != info:
            self._lastshown = info
            self.expose(*info)
            for hook in self._hooks:
                hook(self, *info)

    def expose(self, topic, percent, subpercent):
        pass

    def addHook(self, hook):
        self._hooks.append(hook)

    def removeHook(self, hook):
        self._hooks.remove(hook)

    def getInfo(self):
        if self._subtotal:
            subpercent = int(100*float(self._subcurrent)/self._subtotal)
        else:
            subpercent = None
        if self._total:
            current = self._current
            if self._subtotal and self._fragment:
                current += int(self._fragment*float(subpercent)/100)
            percent = int(100*float(current)/self._total)
        return self._topic, percent, subpercent

    def setTopic(self, topic):
        self._topic = topic

    def getTopic(self):
        return self._topic

    def setCurrent(self, current):
        self._current = current

    def getCurrent(self):
        return self._current

    def setDone(self):
        self._current = self._total

    def setTotal(self, total):
        self._current = 0
        self._total = total

    def getTotal(self):
        return self._total

    def setSubCurrent(self, subcurrent):
        self._subcurrent = subcurrent

    def getSubCurrent(self):
        return self._subcurrent

    def setSubTotal(self, subtotal, fragment=0):
        self._subcurrent = 0
        self._subtotal = subtotal
        self._fragment = fragment

    def getSubTotal(self):
        return self._subtotal

    def getFragment(self):
        return self._fragment

    def setSubDone(self):
        self._subcurrent = self._subtotal

    def getData(self, key):
        return self._data.get(key)

    def setData(self, key, value):
        self._data[key] = value

class RPMStyleProgress(Progress):

    HASHES = 44

    def expose(self, topic, percent, subpercent):
        out = sys.stdout
        if subpercent is not None:
            current = subpercent
        else:
            current = percent
        hashes = int(self.HASHES*current/100)
        n = self.getData("item-number")
        if n is not None:
            out.write("%4d:%-23.23s" % (n, topic))
        else:
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
    import time
    prog = RPMStyleProgress(None)
    prog.setTotal(100)
    for n in range(1,prog.getTotal()+1):
        prog.setData("item-number", n)
        prog.setTopic("package-name%d" % n)
        prog.setCurrent(n)
        prog.setSubTotal(50)
        for i in range(1,prog.getSubTotal()+1):
            prog.setSubCurrent(i)
            prog.show()
            time.sleep(0.05)

if __name__ == "__main__":
    test()

# vim:ts=4:sw=4:et
