"""Prevent another public release with missing Windows/Linux installer assets."""
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_release_assets import prepare


class ReleaseArtifactTest(unittest.TestCase):
    def test_prepare_four_assets_from_separate_artifact_folders(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'artifacts'
            out = Path(d)/'release'
            mockfiles = [
                ('windows', '-Setup.exe', b'MZ'),
                ('linux', '.deb', b'!<arch>\n'),
                ('linux', '.rpm', bytes.fromhex('ed ab ee db')),
                ('linux', '.pkg.tar.zst', bytes.fromhex('28 b5 2f fd')),
            ]
            for platform, suffix, magic in mockfiles:
                p = root/platform/('MicroDownloader-0.5.2-' + platform + suffix)
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open('wb') as f:
                    f.write(magic)
                    f.truncate(1_100_000)
            assets = prepare(root, out, '0.5.2')
            self.assertEqual(len(assets), 4)
            self.assertTrue((out/'SHA256SUMS.txt').is_file())
            self.assertEqual(len((out/'SHA256SUMS.txt').read_text().splitlines()), 4)
            self.assertTrue((out/'MicroDownloader-0.5.2-windows-x64-Setup.exe').exists())
            self.assertTrue((out/'MicroDownloader-0.5.2-linux-x64.pkg.tar.zst').exists())

    def test_checkout_before_artifact_download(self):
        workflow = (Path(__file__).resolve().parent.parent/'.github/workflows/release.yml').read_text()
        self.assertLess(workflow.index('Checkout source to validate release assets'),
                        workflow.index('Download Windows setup artifact'))
        self.assertIn('Verify bundled Windows aria2 RPC and transfer', workflow)


if __name__ == '__main__':
    unittest.main()
