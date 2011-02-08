import BaseHTTPServer
import threading
import unittest
import socket
import signal
import time
import os

from smart.progress import Progress
from smart.interface import Interface
from smart.fetcher import Fetcher
from smart.const import VERSION, SUCCEEDED, FAILED
from smart import fetcher, sysconf, iface

from tests.mocker import MockerTestCase


PORT = 43543
URL = "http://127.0.0.1:%d/filename.pkg" % PORT


class HTTPServer(BaseHTTPServer.HTTPServer):

    hide_errors = False

    def handle_error(self, request, client_address):
        if not self.hide_errors:
            BaseHTTPServer.HTTPServer.handle_error(self, request, client_address)


class FetcherTest(MockerTestCase):

    def setUp(self):
        self.local_path = self.makeDir()
        self.fetcher = Fetcher()
        self.fetcher.setLocalPathPrefix(self.local_path + "/")

        # Smart changes SIGPIPE handling due to a problem which otherwise
        # happens when running external scripts.  Check out smart/__init__.py.
        # We want the normal handling here because in some cases we may
        # get SIGPIPE due to broken sockets on tests.
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)

    def tearDown(self):
        # See above.
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    def start_server(self, handler, hide_errors=False):
        startup_lock = threading.Lock()
        startup_lock.acquire()
        def server():
            class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
                def do_GET(self):
                    return handler(self)
                def log_message(self, format, *args):
                    pass
            while True:
                try:
                    httpd = HTTPServer(("127.0.0.1", PORT), Handler)
                    break
                except socket.error, error:
                    if "Address already in use" not in str(error):
                        raise
                    time.sleep(1)
            startup_lock.release()
            httpd.hide_errors = hide_errors
            httpd.handle_request()

        self.server_thread = threading.Thread(target=server)
        self.server_thread.start()

        # Wait until thread is ready.
        startup_lock.acquire()

    def wait_for_server(self):
        self.server_thread.join()

    def test_user_agent(self):
        headers = []
        def handler(request):
            headers[:] = request.headers.headers
        self.start_server(handler)
        self.fetcher.enqueue(URL)
        self.fetcher.run(progress=Progress())
        self.assertTrue(("User-Agent: smart/%s\r\n" % VERSION) in headers)

    def test_remove_pragma_no_cache_from_curl(self):
        fetcher.enablePycurl()
        headers = []
        def handler(request):
            headers[:] = request.headers.headers
        self.start_server(handler)
        old_http_proxy = os.environ.get("http_proxy")
        os.environ["http_proxy"] = URL
        try:
            self.fetcher.enqueue(URL)
            self.fetcher.run(progress=Progress())
        finally:
            if old_http_proxy:
                os.environ["http_proxy"] = old_http_proxy
            else:
                del os.environ["http_proxy"]
        self.assertTrue("Pragma: no-cache\r\n" not in headers)

    def test_401_handling(self):
        headers = []
        def handler(request):
            request.send_error(401, "Authorization Required")
            request.send_header("Content-Length", "17")
            request.wfile.write("401 Unauthorized.")
        self.start_server(handler)
        self.fetcher.enqueue(URL)
        self.fetcher.run(progress=Progress())
        item = self.fetcher.getItem(URL)
        self.assertEquals(item.getStatus(), FAILED)

    def test_404_handling(self):
        headers = []
        def handler(request):
            request.send_error(404, "An expected error")
            request.send_header("Content-Length", "6")
            request.wfile.write("Hello!")
        self.start_server(handler)
        self.fetcher.enqueue(URL)
        self.fetcher.run(progress=Progress())
        item = self.fetcher.getItem(URL)
        self.assertEquals(item.getFailedReason(), u"File not found")

    def test_timeout(self):
        timeout = 3
        sleep_time = 6

        def reset_timeout(timeout=fetcher.SOCKETTIMEOUT):
            fetcher.SOCKETTIMEOUT = timeout
        reset_timeout(timeout)
        self.addCleanup(reset_timeout)

        headers = []
        def handler(request):
            time.sleep(sleep_time)
            request.send_error(404, "After timeout sleep")
            request.send_header("Content-Length", "6")
            request.wfile.write("Hello!")

        started = time.time()

        # We hide errors here because we know we'll get a broken pipe on
        # the server side if the test succeeds.
        self.start_server(handler, hide_errors=True)
        self.fetcher.enqueue(URL)
        self.fetcher.run(progress=Progress())
        self.assertTrue(timeout <= (time.time() - started) < sleep_time-1)

        item = self.fetcher.getItem(URL)

    def test_ratelimit(self):
        bytes = 30
        rate_limit = 10
        
        sysconf.set("max-download-rate", rate_limit, soft=True)

        def handler(request):
            request.send_header("Content-Length", str(bytes))
            request.wfile.write(" " * bytes)
        
        self.start_server(handler)
        self.fetcher.enqueue(URL)
        start = time.time()
        self.fetcher.run(progress=Progress())
        stop = time.time()
        elapsed_time = stop - start
        
        self.assertTrue(elapsed_time >= bytes / rate_limit)
    
