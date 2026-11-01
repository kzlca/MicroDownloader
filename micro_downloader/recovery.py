"""Safeguarded HTTP range recovery of sparse files using curl, on a QThread.

No writes occur until existing remote/local samples and fingerprint agree.
Every chunk response must be HTTP 206 with exactly the requested Content-Range.
Allocated edge bytes overwritten are backed up. Full-file integrity is still
only established through an external checksum or archive verification.
"""
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

from .tools import find_tool

from PySide6.QtCore import QThread, Signal

from .sparse import MIB, complement, holes_of_fd, inspect, planned_repair, sample_spans, read_at, write_at


class Interrupted(Exception):
    pass


class RecoveryWorker(QThread):
    progress = Signal(int, int, float)    # done, planned, bytes/sec
    stage = Signal(str)
    finished_result = Signal(bool, str)   # succeeded, summary
    map_update = Signal()

    def __init__(self, path, url, repair=False, speed_kib=0, proxy='',
                 margin_mib=1, chunk_mib=8, retries=4, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.url = url.strip()
        self.repair = repair
        self.speed_kib = speed_kib
        self.proxy = proxy.strip()
        self.margin = margin_mib * MIB
        self.chunk = chunk_mib * MIB
        self.retries = retries
        self._cancel = threading.Event()
        self._resume = threading.Event()
        self._resume.set()
        self._remote_identity = None
        self._temp = None

    def cancel(self):
        self._cancel.set()
        self._resume.set()

    def pause(self):
        self._resume.clear()

    def unpause(self):
        self._resume.set()

    def _checkpoint(self):
        if self._cancel.is_set():
            raise Interrupted('Operation stopped at your request.')
        while not self._resume.wait(0.1):
            if self._cancel.is_set():
                raise Interrupted('Operation stopped at your request.')

    @staticmethod
    def _response(headers_file):
        raw = headers_file.read_text('iso-8859-1', errors='replace')
        blocks = re.split(r'\r?\n\r?\n', raw)
        http = [b for b in blocks if re.match(r'^HTTP/\S+\s+\d{3}', b)]
        if not http:
            raise RuntimeError('No HTTP headers returned by server.')
        lines = http[-1].splitlines()
        m = re.match(r'^HTTP/\S+\s+(\d{3})', lines[0])
        if not m:
            raise RuntimeError('Invalid final HTTP status.')
        d = {}
        for line in lines[1:]:
            if ':' in line:
                k, v = line.split(':', 1)
                d[k.lower().strip()] = v.strip()
        return int(m.group(1)), d

    def _fetch(self, start, end, full_size):
        """Return temp file path containing exactly remote [start,end)."""
        self._checkpoint()
        n = end - start
        if not 0 < n <= 32 * MIB:
            raise RuntimeError('Invalid request size.')
        out = self._temp / 'piece.bin'
        hdr = self._temp / 'headers.txt'
        for attempt in range(1, self.retries + 1):
            self._checkpoint()
            out.unlink(missing_ok=True)
            hdr.unlink(missing_ok=True)
            cmd = [find_tool('curl'), '-4', '--http1.1', '-L', '-sS', '--fail',
                   '--connect-timeout', '20', '--max-time', '240',
                   '--proto', '=http,https', '--proto-redir', '=http,https',
                   '--max-filesize', str(n+1), '--range', f'{start}-{end-1}',
                   '-A', 'Mozilla/5.0', '-H', 'Accept-Encoding: identity',
                   '-D', str(hdr), '-o', str(out)]
            if self.speed_kib:
                cmd += ['--limit-rate', str(int(self.speed_kib)*1024)]
            if self.proxy:
                cmd += ['--proxy', self.proxy]
            cmd.append(self.url)
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            while proc.poll() is None:
                if self._cancel.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    raise Interrupted('Operation cancelled. Completed chunks were saved.')
                time.sleep(0.1)
            stderr = proc.communicate()[1].decode(errors='replace').strip()
            try:
                if proc.returncode:
                    raise RuntimeError(f'curl exit {proc.returncode}: {stderr[-350:]}')
                status, headers = self._response(hdr)
                expected = f'bytes {start}-{end-1}/{full_size}'
                if status != 206 or headers.get('content-range') != expected:
                    raise RuntimeError(f'Refusing HTTP {status}, Content-Range={headers.get("content-range")} (wanted {expected})')
                if headers.get('content-encoding', 'identity').lower() != 'identity':
                    raise RuntimeError('Server returned content-encoded data')
                if 'content-length' in headers and int(headers['content-length']) != n:
                    raise RuntimeError('Server returned incorrect Content-Length')
                if not out.exists() or out.stat().st_size != n:
                    raise RuntimeError('Received wrong byte count')
                new_id = (headers.get('etag'), headers.get('last-modified'))
                if self._remote_identity is None:
                    self._remote_identity = new_id
                elif self._remote_identity != new_id:
                    raise RuntimeError('Remote ETag/Last-Modified changed or disappeared; refusing to mix file versions')
                return out
            except (RuntimeError, ValueError, OSError) as exc:
                if attempt == self.retries:
                    raise RuntimeError(f'Range {start}-{end-1} failed: {exc}') from exc
                self.stage.emit(f'Retrying range {start:,} ({attempt}/{self.retries}): {exc}')
                for _ in range(10 * attempt):
                    time.sleep(0.1)
                    self._checkpoint()
        raise RuntimeError('Fetch failed')

    def _verify(self, fd, safe, full_size):
        samples = sample_spans(safe)
        if not samples:
            raise RuntimeError('No known-good allocated data to compare. Automatic recovery refused.')
        self.stage.emit(f'Verifying {len(samples)} existing file samples against the server…')
        t0 = time.monotonic()
        for idx, (a, b) in enumerate(samples, 1):
            self._checkpoint()
            received = self._fetch(a, b, full_size)
            with received.open('rb') as src:
                remote = src.read()
            if read_at(fd, b-a, a) != remote:
                raise RuntimeError(f'Existing bytes differ from server at {a:,}. Recovery stopped before any writes.')
            self.progress.emit(idx, len(samples), idx*4096/max(.01, time.monotonic()-t0))
        self.stage.emit(f'All {len(samples)} existing samples matched the remote file.')

    def _backup_edges(self, fd, holes, planned, size):
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        root = Path(str(self.path) + f'.micro-downloader-edge-backup-{stamp}')
        suffix = 0
        while root.exists():
            suffix += 1
            root = Path(str(self.path) + f'.micro-downloader-edge-backup-{stamp}-{suffix}')
        root.mkdir(mode=0o700)
        count = 0
        for a, b in complement(holes, size):
            for x, y in planned:
                start, end = max(a, x), min(b, y)
                if start < end:
                    dest = root / f'edge-{count:03d}-at-{start}-length-{end-start}.bin'
                    with dest.open('wb') as w:
                        pos = start
                        while pos < end:
                            block = read_at(fd, min(MIB, end-pos), pos)
                            if not block:
                                raise RuntimeError('Could not read backup edge data.')
                            w.write(block)
                            pos += len(block)
                        w.flush()
                        os.fsync(w.fileno())
                    count += 1
        self.stage.emit(f'Backed up {count} boundary fragments to {root}')
        return root

    def run(self):
        try:
            if not find_tool('curl'):
                raise RuntimeError('curl is missing. Install curl or place curl in the application bin directory.')
            if not self.url.startswith(('https://', 'http://')):
                raise RuntimeError('Provide an original HTTP/HTTPS direct file URL.')
            if not self.path.is_file():
                raise RuntimeError('The selected file no longer exists.')
            with tempfile.TemporaryDirectory(prefix='micro-downloader-range-') as tmp:
                self._temp = Path(tmp)
                with self.path.open('r+b' if self.repair else 'rb', buffering=0) as file:
                    fd = file.fileno()
                    size = os.fstat(fd).st_size
                    holes = holes_of_fd(fd, size)
                    if not holes:
                        raise RuntimeError('No detectable sparse regions. Cannot safely reconstruct missing bytes from allocation information.')
                    planned = planned_repair(holes, size, self.margin)
                    safe = complement(planned, size)
                    total = sum(b-a for a, b in planned)
                    self.stage.emit(f'Found {len(holes)} holes ({sum(b-a for a,b in holes)/MIB:.2f} MiB); planned recovery {total/MIB:.2f} MiB')
                    self._verify(fd, safe, size)
                    if not self.repair:
                        self.finished_result.emit(True, 'Verification passed. File unchanged. Use Repair to fill the missing regions.')
                        return
                    # Require free space for filling holes, temporary curl chunk and edge backups.
                    # Filling holes, backing up allocated edge overlaps, plus temporary chunks.
                    needed = total + self.chunk + 32*MIB
                    free = shutil.disk_usage(self.path.parent).free
                    if free < needed:
                        raise RuntimeError(f'Not enough free space: need ~{needed/MIB:.0f} MiB; have {free/MIB:.0f} MiB')
                    self._backup_edges(fd, holes, planned, size)
                    self.stage.emit('Repairing missing ranges and refreshing their allocated boundaries…')
                    done = 0
                    started = time.monotonic()
                    for i, (start, end) in enumerate(planned, 1):
                        at = start
                        while at < end:
                            self._checkpoint()
                            nxt = min(end, at + self.chunk)
                            received = self._fetch(at, nxt, size)
                            with received.open('rb') as f:
                                written = 0
                                while written < nxt - at:
                                    data = f.read(min(MIB, nxt-at-written))
                                    if not data:
                                        raise RuntimeError('Truncated downloaded chunk.')
                                    n = write_at(fd, data, at+written)
                                    if n != len(data):
                                        raise RuntimeError('Short write to destination disk.')
                                    written += n
                            os.fsync(fd)
                            done += nxt - at
                            at = nxt
                            self.progress.emit(done, total, done/max(.1, time.monotonic()-started))
                        self.stage.emit(f'Completed region {i}/{len(planned)}')
                        self.map_update.emit()
                    remaining = holes_of_fd(fd, size)
                    self.map_update.emit()
                    if remaining:
                        raise RuntimeError(f'{len(remaining)} holes remain; saved completed data. Inspect and retry.')
                    self.finished_result.emit(True, 'Recovery finished. Run a full archive integrity test; sparse recovery alone cannot guarantee correctness.')
        except Interrupted as exc:
            self.finished_result.emit(False, str(exc))
        except Exception as exc:
            self.finished_result.emit(False, str(exc))
