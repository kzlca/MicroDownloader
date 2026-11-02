"""Backend startup tests: do not require Qt or network connectivity."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from micro_downloader.engine import AriaController, AriaError
from micro_downloader.backend_supervisor import BackendSupervisor


class Clock:
    now = 100.0
    def __call__(self):
        return self.now
    def move(self, seconds):
        self.now += seconds


class FakeController:
    def __init__(self):
        self.running = False
        self.exit_code = None
        self.fail_launch = 0
        self.fail_probe = 0
        self.launches = 0
        self.stops = 0

    def launch(self, parallel, speed_kib):
        self.launches += 1
        if self.fail_launch:
            self.fail_launch -= 1
            raise AriaError('Windows delayed backend launch')
        self.running = True

    def probe_ready(self):
        if self.fail_probe:
            self.fail_probe -= 1
            raise AriaError('RPC not listening yet')
        return {'version':'1.37'}

    def stop(self):
        self.stops += 1
        self.running = False


class LifecycleTest(unittest.TestCase):
    def test_delayed_startup_is_non_blocking_and_recovers(self):
        clock = Clock()
        engine = FakeController()
        engine.fail_probe = 4
        ctl = BackendSupervisor(engine, clock=clock)
        self.assertEqual(ctl.step(), 'starting')
        self.assertEqual(engine.launches, 1)
        for i in range(4):
            clock.move(1.1)
            self.assertIsNone(ctl.step())
            self.assertFalse(ctl.ready)
        clock.move(1.1)
        self.assertEqual(ctl.step(), 'ready')
        self.assertTrue(ctl.ready)
        self.assertEqual(engine.stops, 0)

    def test_retry_failed_first_launch_without_gui_restart(self):
        clock = Clock()
        engine = FakeController()
        engine.fail_launch = 2
        ctl = BackendSupervisor(engine, clock=clock)
        self.assertEqual(ctl.step(), 'retry')
        self.assertEqual(engine.launches, 1)
        clock.move(1)
        self.assertIsNone(ctl.step())
        clock.move(1)
        self.assertEqual(ctl.step(), 'retry')
        clock.move(4)
        self.assertEqual(ctl.step(), 'starting')
        clock.move(1.1)
        self.assertEqual(ctl.step(), 'ready')
        self.assertEqual(engine.launches, 3)

    def test_crashed_engine_restarts_without_reusing_dead_process(self):
        clock = Clock()
        engine = FakeController()
        ctl = BackendSupervisor(engine, clock=clock)
        self.assertEqual(ctl.step(), 'starting')
        clock.move(1)
        self.assertEqual(ctl.step(), 'ready')
        engine.running = False
        engine.exit_code = 23
        clock.move(1)
        self.assertEqual(ctl.step(), 'lost')
        self.assertIn('23', ctl.error)
        clock.move(2)
        self.assertEqual(ctl.step(), 'starting')
        clock.move(1)
        self.assertEqual(ctl.step(), 'ready')
        self.assertEqual(engine.launches, 2)

    def test_never_kill_live_aria_for_temporary_rpc_failure(self):
        clock = Clock()
        engine = FakeController()
        ctl = BackendSupervisor(engine, clock=clock)
        self.assertEqual(ctl.step(), 'starting')
        clock.move(1)
        self.assertEqual(ctl.step(), 'ready')
        engine.fail_probe = 3
        clock.move(6)
        self.assertEqual(ctl.step(), 'disconnected')
        self.assertFalse(ctl.ready)
        for i in range(2):
            clock.move(1.5)
            self.assertIsNone(ctl.step())
        clock.move(1.5)
        self.assertEqual(ctl.step(), 'reconnected')
        self.assertEqual(engine.stops, 0)
        self.assertEqual(engine.launches, 1)

    def test_20_second_slow_start_keeps_process_untouched(self):
        clock = Clock()
        engine = FakeController()
        engine.fail_probe = 500
        ctl = BackendSupervisor(engine, clock=clock)
        ctl.step()
        clock.move(21)
        self.assertEqual(ctl.step(), 'slow')
        self.assertEqual(engine.stops, 0)
        self.assertTrue(engine.running)
        clock.move(1)
        self.assertIsNone(ctl.step())  # warning is not repeated

    def test_controller_releases_previous_log_on_failed_spawn(self):
        class DeadProcess:
            def poll(self): return 1
        with tempfile.TemporaryDirectory() as d:
            controller = AriaController(d)
            controller.proc = DeadProcess()
            controller.stderr = (Path(d)/'aria2.log').open('w')
            controller.stop()
            self.assertIsNone(controller.stderr)
            self.assertIsNone(controller.port)


if __name__ == '__main__':
    unittest.main()
