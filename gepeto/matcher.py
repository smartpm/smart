
class Matcher(object):
    def __init__(self, str):
        self._str = str

    def matches(self, obj):
        return False

class MasterMatcher(object):
    def __init__(self, str):
        self._str = str
        self._matchers = {}

    def matches(self, obj):
        if hasattr(obj, "matcher"):
            matcher = self._matchers.get(obj.matcher)
            if not matcher:
                matcher = obj.matcher(self._str)
                self._matchers[obj.matcher] = matcher
            return matcher.matches(obj)
        return False

    def filter(self, lst):
        return [x for x in lst if self.matches(x)]

# vim:ts=4:sw=4:et
