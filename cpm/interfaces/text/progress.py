from cpm.util.strtools import ShortURL
from cpm.progress import Progress
import posixpath
import time
import sys

class TextProgress(Progress):

    HASHES = 44

    def __init__(self):
        Progress.__init__(self)
        self._lasttopic = None
        self._lastsubkey = None
        self._lastsubkeystart = 0
        self._fetchermode = False
        self._seentopics = {}
        self._addline = False
        self._shorturl = ShortURL(self.HASHES+34)

    def setFetcherMode(self, flag):
        self._fetchermode = flag

    def stop(self):
        Progress.stop(self)
        self._shorturl.reset()

    def expose(self, topic, percent, subkey, subtopic, subpercent, data, done):
        out = sys.stdout
        if self.getHasSub():
            if topic != self._lasttopic:
                self._lasttopic = topic
                out.write(" "*(self.HASHES+34)+"\r")
                if self._addline:
                    print
                else:
                    self._addline = True
                print topic
            if not subkey:
                return
            if not done:
                now = time.time()
                if subkey == self._lastsubkey:
                    if (self._lastsubkeystart+2 < now and
                        self.getSubCount() > 1):
                        return
                else:
                    if (self._lastsubkeystart+2 > now and
                        self.getSubCount() > 1):
                        return
                    self._lastsubkey = subkey
                    self._lastsubkeystart = now
            elif subkey == self._lastsubkey:
                    self._lastsubkeystart = 0
            current = subpercent
            topic = subtopic
            if self._fetchermode:
                if topic not in self._seentopics:
                    self._seentopics[topic] = True
                    out.write(" "*(self.HASHES+34)+"\r")
                    print "->", self._shorturl.get(topic)
                topic = posixpath.basename(topic)
        else:
            current = percent
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
        if not done:
            out.write("(%3d%%)\r" % current)
        elif subpercent is None:
            out.write("[%3d%%]\n" % current)
        else:
            out.write("[%3d%%]\n" % percent)
        out.flush()

def test():
    prog = TextProgress()
    data = {"item-number": 0}
    total, subtotal = 100, 100
    prog.start(True)
    prog.setTopic("Installing packages...")
    for n in range(1,total+1):
        data["item-number"] = n
        prog.set(n, total)
        prog.setSubTopic(n, "package-name%d" % n)
        for i in range(0,subtotal+1):
            prog.setSub(n, i, subtotal, subdata=data)
            prog.show()
            time.sleep(0.01)
    prog.stop()

if __name__ == "__main__":
    test()

# vim:ts=4:sw=4:et
