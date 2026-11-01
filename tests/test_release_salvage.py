import tempfile
import unittest
from pathlib import Path
from scripts.prepare_release_assets import prepare


class TestSalvageRelease(unittest.TestCase):
    def make_dirs(self, root):
        for platform in ('windows', 'linux'):
            (root / platform).mkdir(parents=True, exist_ok=True)
        files = {
            'windows/strange-windows-setup.exe': b'MZ',
            'linux/ubuntu-foo.deb': b'!<arch>\n',
            'linux/arch-foo.pkg.tar.zst': bytes.fromhex('28 b5 2f fd'),
            'linux/fedora-foo.rpm': bytes.fromhex('ed ab ee db'),
        }
        for name, magic in files.items():
            (root / name).write_bytes(magic + b'0' * 1_000_010)

    def test_renames_and_checks_all_four(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'artifacts'
            out = Path(tmp) / 'out'
            self.make_dirs(root)
            res = prepare(root, out, '0.5.1')
            self.assertEqual(len(res), 4)
            self.assertEqual(len(list(out.glob('MicroDownloader*'))), 4)
            self.assertEqual(len((out / 'SHA256SUMS.txt').read_text().splitlines()), 4)

    def test_wrong_signature_refuses_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'artifacts'
            self.make_dirs(root)
            (root / 'linux/fedora-foo.rpm').write_bytes(b'X' * 1_000_010)
            with self.assertRaisesRegex(ValueError, 'unexpected file format'):
                prepare(root, Path(tmp) / 'out', '0.5.1')

    def test_missing_installer_refuses_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'artifacts'
            self.make_dirs(root)
            (root / 'windows/strange-windows-setup.exe').unlink()
            with self.assertRaisesRegex(ValueError, 'expected 1'):
                prepare(root, Path(tmp) / 'out', '0.5.1')
