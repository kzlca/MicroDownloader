"""Regression tests that run without Qt or network access.

The previous release passed compileall but failed at runtime importing styles.py;
importing the module here catches exactly that category of error.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from micro_downloader.styles import DARK

ROOT = Path(__file__).resolve().parent.parent


class TestDistribution(unittest.TestCase):
    def test_styles_import_and_sidebar_rules(self):
        self.assertIn('QWidget#sidebarContent', DARK)
        self.assertIn('QScrollArea', DARK)
        self.assertIn('QPushButton#nav', DARK)
        self.assertIn('QProgressBar::chunk', DARK)
        self.assertNotIn('QWidget#sidebarContent, QScrollArea', (ROOT / 'micro_downloader/styles.py').read_text().split('"""')[-1])

    def test_build_assets_and_no_legacy_importer(self):
        self.assertTrue((ROOT/'micro_downloader/assets/logo.png').is_file())
        self.assertTrue((ROOT/'micro_downloader/assets/logo.ico').is_file())
        self.assertFalse((ROOT/'micro_downloader/kget.py').exists())
        self.assertNotIn('kget', (ROOT/'micro_downloader/ui.py').read_text().lower())

    def test_update_keeps_local_files_and_virtualenv(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root/'prior_version'
            target.mkdir()
            (target/'run.py').write_text('old launcher')
            (target/'.venv/bin').mkdir(parents=True)
            (target/'.venv/bin/python').write_text('virtual environment marker')
            (target/'download.rar').write_bytes(b'KEEP MY DOWNLOAD')
            (target/'micro_downloader').mkdir()
            (target/'micro_downloader/kget.py').write_text('old importer')
            p = subprocess.run(['bash', str(ROOT/'upgrade_existing.sh'), str(target)],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual((target/'download.rar').read_bytes(), b'KEEP MY DOWNLOAD')
            self.assertEqual((target/'.venv/bin/python').read_text(), 'virtual environment marker')
            self.assertFalse((target/'micro_downloader/kget.py').exists())
            self.assertIn('micro_downloader.ui', (target/'run.py').read_text())


if __name__ == '__main__':
    unittest.main()
