import tempfile
import unittest
from pathlib import Path
from scripts.verify_release_assets import expected

class ReleaseAssetTests(unittest.TestCase):
    def test_expected_platform_assets(self):
        names=expected('0.5.0')
        self.assertEqual(len(names),4)
        self.assertEqual(len(set(names)),4)
        self.assertTrue(any(n.endswith('-Setup.exe') for n in names))
        self.assertTrue(any(n.endswith('.deb') for n in names))
        self.assertTrue(any(n.endswith('.rpm') for n in names))
        self.assertTrue(any(n.endswith('.pkg.tar.zst') for n in names))

if __name__ == '__main__':
    unittest.main()
