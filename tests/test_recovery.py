"""Integration test: curl HTTP range server repairs holes + bad boundary bytes."""
import os
import re
import sys
import tempfile
import threading
import types
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

# These tests exercise the QThread worker's synchronous run method without
# importing Qt: the application still requires real PySide6 to show its UI.
class DummySignal:
    def __init__(self, *args): self.history=[]
    def emit(self, *args): self.history.append(args)

class DummyThread:
    def __init__(self, parent=None): pass

qt = types.ModuleType('PySide6.QtCore')
qt.Signal = DummySignal
qt.QThread = DummyThread
sys.modules.setdefault('PySide6', types.ModuleType('PySide6'))
sys.modules.setdefault('PySide6.QtCore', qt)

from micro_downloader.recovery import RecoveryWorker
from micro_downloader.sparse import inspect, MIB


class TestRecovery(unittest.TestCase):
    def test_repair_missing_and_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            data = os.urandom(17 * MIB)
            original = root/'server.bin'
            original.write_bytes(data)
            partial = root/'partial.bin'
            with partial.open('wb') as f:
                f.truncate(len(data))
            regions=[(0, 5*MIB), (7*MIB, 11*MIB), (13*MIB, len(data))]
            with partial.open('r+b', buffering=0) as f:
                for a,b in regions:
                    os.pwrite(f.fileno(), data[a:b], a)
                # A damaged 4KiB allocated block immediately before the first hole
                os.pwrite(f.fileno(), b'X'*4096, 5*MIB-4096)
            self.assertTrue(inspect(partial)['holes'])

            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    m = re.fullmatch(r'bytes=(\d+)-(\d+)',self.headers.get('Range',''))
                    if not m:
                        self.send_response(200)
                        self.send_header('Content-Length',str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                        return
                    a,b=map(int,m.groups())
                    if a>=len(data) or b>=len(data):
                        self.send_error(416)
                        return
                    body=data[a:b+1]
                    self.send_response(206)
                    self.send_header('Content-Length',str(len(body)))
                    self.send_header('Content-Range',f'bytes {a}-{b}/{len(data)}')
                    self.send_header('ETag','"test-local-version"')
                    self.send_header('Last-Modified','Sun, 01 Nov 2026 00:00:00 GMT')
                    self.end_headers()
                    self.wfile.write(body)
                def log_message(self,*args): pass
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            url=f'http://127.0.0.1:{server.server_port}/data.bin'
            try:
                check = RecoveryWorker(str(partial),url, repair=False,
                                       margin_mib=1,chunk_mib=2)
                check.run()
                self.assertTrue(check.finished_result.history[-1][0], check.finished_result.history)
                self.assertNotEqual(partial.read_bytes(), data)
                repair=RecoveryWorker(str(partial),url, repair=True,
                                      margin_mib=1,chunk_mib=2)
                repair.run()
                self.assertTrue(repair.finished_result.history[-1][0], repair.finished_result.history)
                self.assertEqual(partial.read_bytes(),data)
                self.assertEqual(inspect(partial)['missing'],0)
                self.assertTrue(list(root.glob('partial.bin.micro-downloader-edge-backup-*')))
            finally:
                server.shutdown()
                thread.join()
                server.server_close()


if __name__=='__main__': unittest.main()
