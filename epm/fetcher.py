
class Fetcher:

    def get(self, url):
        assert url.startswith("file://")
        return url[7:]
        return None

# vim:ts=4:sw=4
