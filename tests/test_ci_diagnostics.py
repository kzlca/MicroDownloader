"""Build/test safety checks that do not require downloading Qt."""
import io
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import run

ROOT = Path(__file__).resolve().parent.parent


class ReleaseDiagnosticsTests(unittest.TestCase):
    def test_gui_script_supports_python_filename_invocation(self):
        content = (ROOT/'scripts/smoke_ui.py').read_text()
        self.assertIn('sys.path.insert(0, str(PROJECT_ROOT))', content)

    def test_ci_runs_gui_smoke_as_module_and_logs_windows_exceptions(self):
        release = (ROOT/'.github/workflows/release.yml').read_text()
        ci = (ROOT/'.github/workflows/ci.yml').read_text()
        self.assertIn('python -m scripts.smoke_ui', ci)
        self.assertIn('python -m scripts.smoke_ui', release)
        self.assertIn('MICRO_DOWNLOADER_SELF_TEST_LOG', release)
        self.assertIn('QT_QPA_PLATFORM', release)
        self.assertIn('micro-downloader-windows-selftest-log', release)
        self.assertIn('Get-Content $env:MICRO_DOWNLOADER_SELF_TEST_LOG', release)
        # Windows must use its native Qt backend. PyInstaller's offscreen
        # plugin may lack a usable font database on Windows runners.
        self.assertIn("$env:QT_QPA_PLATFORM = 'windows'", release)
        self.assertIn('Windows native Qt/font availability probe', release)
        self.assertIn('Qt startup: ', (ROOT/'micro_downloader/ui.py').read_text())

    def _run_fake_selftest(self, launch):
        qtcore = types.ModuleType('PySide6.QtCore')
        qtcore.qInstallMessageHandler = lambda handler: None
        fake_qt = types.ModuleType('PySide6')
        fake_qt.__path__ = []
        fake_ui = types.ModuleType('micro_downloader.ui')
        fake_ui.launch = launch
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp)/'selftest.log'
            with patch.dict(sys.modules, {'PySide6':fake_qt, 'PySide6.QtCore':qtcore, 'micro_downloader.ui':fake_ui}), \
                 patch.dict(os.environ, {'MICRO_DOWNLOADER_SELF_TEST_LOG':str(report)}), \
                 patch.object(sys, 'argv', ['MicroDownloader.exe','--self-test']), \
                 patch.object(sys, 'excepthook', sys.excepthook), \
                 patch.object(sys, 'stderr', io.StringIO()):
                code = run.main()
            return code, report.read_text(encoding='utf-8')

    def test_windows_windowed_selftest_success_log(self):
        code, report = self._run_fake_selftest(lambda self_test: 0)
        self.assertEqual(code, 0)
        self.assertIn('START:', report)
        self.assertIn('UI import succeeded', report)
        self.assertIn('PASS:', report)

    def test_windows_windowed_selftest_exception_log(self):
        def faulty_launch(self_test):
            raise RuntimeError('example startup failure')
        code, report = self._run_fake_selftest(faulty_launch)
        self.assertEqual(code, 1)
        self.assertIn('RuntimeError: example startup failure', report)
        self.assertIn('FAIL:', report)


if __name__ == '__main__':
    unittest.main()
