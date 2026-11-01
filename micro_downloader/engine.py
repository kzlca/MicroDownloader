"""Private loopback-only aria2 JSON-RPC service for standard downloads."""
import json
import os
import secrets
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from .tools import find_tool


class AriaError(RuntimeError):
    pass


class AriaController:
    def __init__(self, logdir):
        self.logdir = Path(logdir)
        self.proc = None
        self.port = None
        self.secret = secrets.token_urlsafe(32)
        self.stderr = None

    @property
    def available(self):
        return find_tool('aria2c') is not None

    def start(self, parallel=3, speed_kib=0):
        if self.proc is not None and self.proc.poll() is None:
            return
        if not self.available:
            raise AriaError('aria2c not found. Install aria2 or use a release containing the bundled aria2c executable.')
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            self.port = s.getsockname()[1]
        self.stderr = open(self.logdir / 'aria2.log', 'a', buffering=1)
        args = [find_tool('aria2c'), '--no-conf=true', '--enable-rpc=true',
                '--rpc-listen-all=false', f'--rpc-listen-port={self.port}',
                f'--rpc-secret={self.secret}', '--rpc-allow-origin-all=false',
                '--file-allocation=none', '--continue=true',
                '--auto-file-renaming=false', '--allow-overwrite=false',
                '--check-certificate=true', '--console-log-level=warn',
                f'--max-concurrent-downloads={max(1, int(parallel))}',
                f'--max-overall-download-limit={max(0, int(speed_kib))*1024}',
                '--enable-color=false', '--max-download-result=2000']
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=self.stderr,
                                     start_new_session=True)
        for _ in range(40):
            if self.proc.poll() is not None:
                raise AriaError(f'aria2c exited with code {self.proc.returncode}; see aria2.log')
            try:
                self.call('getVersion')
                return
            except (AriaError, OSError):
                time.sleep(0.1)
        self.stop()
        raise AriaError('aria2c did not respond to local JSON-RPC startup')

    def call(self, method, *args):
        if self.proc is None or self.proc.poll() is not None:
            raise AriaError('aria2 backend is not running')
        request_data = json.dumps({'jsonrpc': '2.0', 'id': 'micro-downloader',
                                   'method': 'aria2.' + method,
                                   'params': ['token:' + self.secret, *args]}).encode('utf-8')
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}/jsonrpc',
                                     request_data, {'Content-Type': 'application/json'})
        try:
            # Bypass desktop proxy settings for loopback service.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=2) as response:
                obj = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise AriaError(str(exc)) from exc
        if 'error' in obj:
            raise AriaError(obj['error'].get('message', str(obj['error'])))
        return obj.get('result')

    def add(self, url, path, connections=8, proxy=''):
        path = Path(path)
        opts = {'dir': str(path.parent), 'out': path.name, 'continue': 'true',
                'auto-file-renaming': 'false', 'allow-overwrite': 'false',
                'split': str(max(1, int(connections))),
                'max-connection-per-server': str(max(1, int(connections))),
                'min-split-size': '1M', 'file-allocation': 'none'}
        if proxy:
            opts['all-proxy'] = proxy
        return self.call('addUri', [url], opts)

    def status(self, gid):
        return self.call('tellStatus', gid, ['gid','status','totalLength','completedLength',
                                             'downloadSpeed','errorCode','errorMessage','files'])

    def pause(self, gid):
        return self.call('pause', gid)

    def unpause(self, gid):
        return self.call('unpause', gid)

    def remove(self, gid):
        try:
            return self.call('forceRemove', gid)
        except AriaError:
            return None

    def set_limits(self, parallel, speed_kib):
        return self.call('changeGlobalOption', {'max-concurrent-downloads': str(max(1, int(parallel))),
                        'max-overall-download-limit': str(max(0, int(speed_kib))*1024)})

    def global_stat(self):
        return self.call('getGlobalStat')

    def stop(self):
        p, self.proc = self.proc, None
        if p is None:
            return
        if p.poll() is None:
            # Request graceful shutdown so aria2 flushes .aria2 state files.
            try:
                data = json.dumps({'jsonrpc':'2.0', 'id':'shutdown', 'method':'aria2.shutdown',
                                   'params':['token:' + self.secret]}).encode()
                req = urllib.request.Request(f'http://127.0.0.1:{self.port}/jsonrpc', data,
                                             {'Content-Type':'application/json'})
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                opener.open(req, timeout=1).close()
            except Exception:
                pass
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.terminate()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
        if self.stderr:
            self.stderr.close()
            self.stderr = None
