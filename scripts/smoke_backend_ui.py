"""Qt integration smoke: delayed aria2 initialization must preserve the queue.

No network or real aria2 process needed. This exercises MainWindow's connection
between the BackendSupervisor and persistent download jobs.
"""
import os
from pathlib import Path
import tempfile

if os.name != 'nt':
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from micro_downloader import ui
from micro_downloader.engine import AriaError
from micro_downloader.store import Store


class SimulatedAria:
    def __init__(self, home):
        self.running = False
        self.exit_code = None
        self.launches = 0
        self.fail_once = True
        self.ready = False
        self.added = []

    def launch(self, parallel, speed_kib):
        self.launches += 1
        if self.fail_once:
            self.fail_once = False
            raise AriaError('simulated first Windows startup error')
        self.running = True

    def probe_ready(self):
        if not self.ready:
            raise AriaError('simulated RPC not listening')
        return {'version':'test'}

    def add(self, url, path, connections, proxy):
        self.added.append((url, str(path)))
        return 'fake-gid-' + str(len(self.added))

    def stop(self):
        self.running = False


def main():
    with tempfile.TemporaryDirectory(prefix='micro-backend-ui-') as home:
        file = Path(home)/'test-download.bin'
        db = Store(home)
        jid = db.add_job('download', file, 'https://example.org/test-download.bin', status='queued')
        db.close()
        ui.Store = lambda: Store(home)
        ui.AriaController = SimulatedAria
        app = QApplication([])
        window = ui.MainWindow()
        window.timer.stop()
        try:
            assert window.store.get(jid)['status'] == 'queued'
            window._sync_engine()  # first launch fails
            assert window.store.get(jid)['status'] == 'queued'
            assert not window.supervisor.ready
            window.supervisor.next_retry = 0.0
            window._sync_engine()  # launches successfully
            assert not window.supervisor.ready
            window.aria.ready = True
            window._sync_engine()  # RPC ready -> queued transfer starts
            assert window.supervisor.ready
            assert window.store.get(jid)['status'] == 'waiting'
            assert len(window.aria.added) == 1

            # A process crash invalidates previous GIDs; don't lose URLs.
            window.aria.running = False
            window.aria.exit_code = 7
            window._sync_engine()
            saved = window.store.get(jid)
            assert saved['status'] == 'queued' and saved['gid'] == ''
            assert saved['url'] == 'https://example.org/test-download.bin'
            window.supervisor.next_retry = 0.0
            window._sync_engine()
            window._sync_engine()
            assert len(window.aria.added) == 2
            print('PASS: first-run retry, queued transfer, process-crash resume, saved URL')
        finally:
            window.close()
            app.quit()


if __name__ == '__main__':
    main()
