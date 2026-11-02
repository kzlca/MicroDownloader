"""Non-blocking, conservative aria2 lifecycle supervision (no Qt dependency).

Never kill a live aria2 process just because RPC is temporarily unresponsive:
doing so can invalidate in-flight writes and transfer control files.
"""
import time

from .engine import AriaError


class BackendSupervisor:
    """One short step per GUI timer tick. Events: starting, ready, reconnected,
    lost, retry, or None. No sleeping or long blocking loops.
    """

    def __init__(self, controller, parallel=3, speed_kib=0, clock=None):
        self.controller = controller
        self.parallel = parallel
        self.speed_kib = speed_kib
        self.clock = clock or time.monotonic
        self.state = 'retrying'
        self.error = ''
        self.attempts = 0
        self.next_retry = 0.0
        self.started_at = 0.0
        self.last_probe = 0.0
        self._reported_slow = False

    @property
    def ready(self):
        return self.state == 'ready'

    def reset(self):
        """Only call after deliberate shutdown of the owned process."""
        self.state = 'retrying'
        self.error = ''
        self.attempts = 0
        self.next_retry = 0.0
        self._reported_slow = False

    def _retry(self, now, reason):
        self.error = str(reason)
        self.attempts += 1
        delay = min(30, 2 ** min(self.attempts, 5))
        self.next_retry = now + delay
        self.state = 'retrying'

    def note_rpc_failure(self, reason):
        """Do not destroy a still-running process due to a single RPC error."""
        if self.state == 'ready':
            self.state = 'degraded'
            self.error = str(reason)
            self.last_probe = 0.0

    def step(self):
        now = self.clock()
        if self.state == 'retrying':
            if now < self.next_retry:
                return None
            try:
                self.controller.launch(self.parallel, self.speed_kib)
            except (OSError, AriaError) as exc:
                self._retry(now, exc)
                return 'retry'
            self.state = 'starting'
            self.error = ''
            self.last_probe = 0.0
            self.started_at = now
            self._reported_slow = False
            return 'starting'

        if not self.controller.running:
            was_connected = self.state in ('ready', 'degraded')
            code = getattr(self.controller, 'exit_code', None)
            self._retry(now, f'aria2 exited (code {code})' if code is not None else 'aria2 stopped')
            return 'lost' if was_connected else 'retry'

        # Do not hammer RPC during healthy transfers. During startup, allow
        # the Windows scanner / antivirus time to finish its first-run work.
        interval = 5 if self.state == 'ready' else 1
        if now - self.last_probe < interval:
            return None
        self.last_probe = now
        try:
            self.controller.probe_ready()
        except (OSError, AriaError) as exc:
            if self.state == 'ready':
                self.state = 'degraded'
                self.error = str(exc)
                return 'disconnected'
            self.error = str(exc)
            if (self.state == 'starting' and now - self.started_at >= 20
                    and not self._reported_slow):
                self._reported_slow = True
                return 'slow'
            # Intentionally keep checking a live process; don't kill it.
            return None
        was = self.state
        self.state = 'ready'
        self.error = ''
        self.attempts = 0
        self._reported_slow = False
        return 'reconnected' if was == 'degraded' else ('ready' if was != 'ready' else None)
