import os
import tempfile
import unittest
from pathlib import Path

from micro_downloader.store import Store
from micro_downloader.sparse import inspect, merge, complement, planned_repair, sample_spans


class TestStore(unittest.TestCase):
    def test_url_survives_restart(self):
        with tempfile.TemporaryDirectory() as home:
            db = Store(home)
            jid = db.add_job('recovery', Path(home)/'large.rar', 'https://example.net/a.rar')
            db.log(jid, 'Stored')
            db.close()
            db = Store(home)
            self.assertEqual(db.get(jid)['url'], 'https://example.net/a.rar')
            self.assertEqual(db.resolve_url(Path(home)/'large.rar'), 'https://example.net/a.rar')
            self.assertEqual(db.events(jid)[0]['detail'], 'Stored')
            db.delete(jid)
            self.assertEqual(db.resolve_url(Path(home)/'large.rar'), 'https://example.net/a.rar')
            db.close()

    def test_previous_brand_database_migration(self):
        """Upgrade preserves source URL, task and history without removing the old DB."""
        with tempfile.TemporaryDirectory() as td:
            old = Path(td) / 'old_velora'
            dest = Path(td) / 'new_micro_downloader'
            legacy = Store(old)
            jid = legacy.add_job('recovery', Path(td) / 'partial.rar', 'https://example.org/partial.rar')
            legacy.log(jid, 'Test history')
            legacy.close()
            # Emulate the previous version's database filename.
            (old / 'micro-downloader.db').rename(old / 'velora.db')
            upgraded = Store(dest, legacy_home=old)
            self.assertTrue(upgraded.migrated)
            self.assertEqual(upgraded.get(jid)['url'], 'https://example.org/partial.rar')
            self.assertEqual(upgraded.events(jid)[0]['detail'], 'Test history')
            self.assertTrue((old / 'velora.db').exists())
            upgraded.close()
            again = Store(dest, legacy_home=old)
            self.assertFalse(again.migrated)
            self.assertEqual(len(again.all_jobs()), 1)
            again.close()

    def test_sparse_regions(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'partial.bin'
            with p.open('wb') as f:
                f.truncate(16 * 1024 * 1024)
            with p.open('r+b', buffering=0) as f:
                os.pwrite(f.fileno(), b'HEADER', 0)
                os.pwrite(f.fileno(), b'TAIL', 15 * 1024 * 1024)
            info = inspect(p)
            self.assertEqual(info['size'], 16*1024*1024)
            self.assertTrue(info['holes'])
            self.assertTrue(info['allocated'] < info['size'])
            self.assertEqual(sum(b-a for a,b in info['holes']), info['missing'])

    def test_spans(self):
        self.assertEqual(merge([(0,10),(10,20),(30,40)]),[(0,20),(30,40)])
        self.assertEqual(complement([(5,10),(20,30)],40),[(0,5),(10,20),(30,40)])
        self.assertEqual(planned_repair([(5,10)],20,2),[(3,12)])
        self.assertTrue(sample_spans([(0,10000)]))



if __name__=='__main__':
    unittest.main()
