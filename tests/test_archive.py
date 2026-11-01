"""Regression tests for missing multipart RAR volumes and i18n catalogs."""
import tempfile
import unittest
from pathlib import Path
from micro_downloader.archive_check import volume_info, summarize_7z
from micro_downloader.i18n import CATALOG, is_rtl, translate


class TestArchive(unittest.TestCase):
    def test_missing_last_part_is_explicitly_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(1, 13):
                with (root / f'Example.part{i:02}.rar').open('wb') as f:
                    f.truncate(3 * 1024**3)
            sample = '''Type = Rar5\nPhysical Size = 3221225472\nTotal Physical Size = 39027363653\nVolumes = 13\nHeaders Error\nERROR: Data Error : file.pak\n'''
            ok, detail = summarize_7z(root/'Example.part12.rar', sample, '', 2)
            self.assertFalse(ok)
            self.assertIn('Example.part13.rar',detail)
            self.assertIn('355.4 MiB',detail)
            self.assertIn('DATA ERROR',detail)
            self.assertIn('HEADERS ERROR',detail)
            self.assertEqual(volume_info(root/'Example.part11.rar', sample)['expected'],13)

    def test_no_false_missing_volumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'a.part01.rar'
            p.write_bytes(b'fake')
            info = volume_info(p)
            self.assertEqual(info['missing'],[])
            self.assertEqual(info['expected'], 1)

    def test_language_fallback(self):
        self.assertEqual(translate('Settings','fa'),'تنظیمات')
        self.assertEqual(translate('Settings','tr'),'Ayarlar')
        self.assertEqual(translate('Unknown literal','fa'),'Unknown literal')
        self.assertTrue(is_rtl('fa'))
        self.assertFalse(is_rtl('tr'))
        self.assertIn('en',CATALOG)

if __name__ == '__main__':
    unittest.main()
