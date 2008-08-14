import BaseHTTPServer
import threading
import unittest
import time

from smart.progress import Progress
from smart.fetcher import Fetcher


PORT = 43543
URL = "http://127.0.0.1:%d" % PORT


class FetcherTest(unittest.TestCase):

    def start_server(self, handler):
        def server():
            class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
                def do_GET(self):
                    return handler(self)
            httpd = BaseHTTPServer.HTTPServer(("127.0.0.1", PORT), Handler)
            httpd.handle_request()
        self.server_thread = threading.Thread(target=server)
        self.server_thread.start()
        time.sleep(0.2)

    def wait_for_server(self):
        self.server_thread.join()

    def test_user_agent(self):
        headers = []
        def handler(request):
            headers[:] = request.headers.headers
        self.start_server(handler)
        fetcher = Fetcher()
        fetcher.enqueue(URL)
        fetcher.run(progress=Progress())
        self.assertTrue("User-Agent: smart/0.52\r\n" in headers)

    def test_remove_pragma_no_cache_from_curl(self):
        headers = []
        def handler(request):
            headers[:] = request.headers.headers
        self.start_server(handler)
        old_http_proxy = os.environ.get("http_proxy")
        os.environ["http_proxy"] = URL
        try:
            fetcher = Fetcher()
            fetcher.enqueue(URL)
            fetcher.run(progress=Progress())
        finally:
            if old_http_proxy:
                os.environ["http_proxy"] = old_http_proxy
            else:
                del os.environ["http_proxy"]
        self.assertTrue("Pragma: no-cache\r\n" not in headers)
