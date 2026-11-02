#!/usr/bin/env python3
"""CI test for a *real* aria2 binary: launch RPC, download 128 KiB, shutdown.

Uses an HTTP server bound only to 127.0.0.1; no external network needed.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from unittest.mock import patch

from micro_downloader.engine import AriaController

CONTENT = bytes(range(256)) * 512


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Length', str(len(CONTENT)))
        self.end_headers()
        self.wfile.write(CONTENT)

    def log_message(self, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--binary', required=True)
    args = ap.parse_args()
    binary = Path(args.binary).resolve()
    if not binary.is_file():
        raise SystemExit(f'aria2 executable missing: {binary}')
    with TemporaryDirectory(prefix='micro-aria2-smoke-') as td:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        controller = AriaController(td)
        try:
            with patch('micro_downloader.engine.find_tool', return_value=str(binary)):
                controller.start(parallel=1)
                target = Path(td)/'test.bin'
                gid = controller.add(f'http://127.0.0.1:{server.server_port}/file.bin', target, connections=1)
                deadline = monotonic() + 20
                while monotonic() < deadline:
                    result = controller.status(gid)
                    if result['status'] == 'complete':
                        if target.read_bytes() != CONTENT:
                            raise AssertionError('Downloaded bytes differ')
                        print('PASS aria2 downloaded and verified local test bytes via RPC')
                        break
                    if result['status'] == 'error':
                        raise AssertionError('aria2 download error: ' + str(result.get('errorMessage')))
                    sleep(0.2)
                else:
                    raise AssertionError('aria2 RPC download timed out')
        finally:
            controller.stop()
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
