"""Durable SQLite jobs, settings and URL history. All access from the GUI thread."""
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path

if os.environ.get('MICRO_DOWNLOADER_DATA_DIR'):
    BASE = Path(os.environ['MICRO_DOWNLOADER_DATA_DIR']).expanduser()
elif os.name == 'nt':
    BASE = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'MicroDownloader'
else:
    BASE = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))) / 'micro-downloader'

if os.name == 'nt':
    LEGACY_BASE = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'VeloraDownload'
else:
    LEGACY_BASE = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))) / 'velora-download'


def migrate_old_db(destination, sources):
    """Keep old Velora data intact; SQLite backup includes uncheckpointed WAL."""
    destination = Path(destination)
    if destination.exists():
        return False
    for source in sources:
        source = Path(source)
        if not source.is_file():
            continue
        target_tmp = destination.with_name(destination.name + '.migrating')
        try:
            if target_tmp.exists():
                target_tmp.unlink()
            with sqlite3.connect(str(source)) as old:
                with sqlite3.connect(str(target_tmp)) as new:
                    old.backup(new)
            os.replace(target_tmp, destination)
        except Exception:
            if target_tmp.exists():
                target_tmp.unlink()
            raise
        return True
    return False


class Store:
    def __init__(self, home=None, legacy_home=None):
        self.home = Path(home) if home is not None else BASE
        self.home.mkdir(parents=True, exist_ok=True)
        old_paths = []
        if legacy_home is not None:
            old_paths.append(Path(legacy_home) / 'velora.db')
        if home is None:
            if os.environ.get('VELORA_DATA_DIR'):
                old_paths.append(Path(os.environ['VELORA_DATA_DIR']).expanduser() / 'velora.db')
            old_paths.append(LEGACY_BASE / 'velora.db')
        old_paths.append(self.home / 'velora.db')
        self.migrated = migrate_old_db(self.home / 'micro-downloader.db', old_paths)
        self.db = sqlite3.connect(str(self.home / "micro-downloader.db"))
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK(kind IN ('download','recovery')),
                url TEXT NOT NULL DEFAULT '',
                path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                done INTEGER NOT NULL DEFAULT 0,
                total INTEGER NOT NULL DEFAULT 0,
                speed INTEGER NOT NULL DEFAULT 0,
                gid TEXT NOT NULL DEFAULT '',
                error TEXT NOT NULL DEFAULT '',
                added INTEGER NOT NULL,
                updated INTEGER NOT NULL,
                meta TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs(status);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS url_history (
                path TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                updated INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                stamp INTEGER NOT NULL,
                severity TEXT NOT NULL,
                detail TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_events_job ON events(job_id,id);
        """)
        self.db.commit()

    def settings(self, key, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row[0])
        except (ValueError, TypeError):
            return default

    def set_setting(self, key, value):
        self.db.execute("INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))
        self.db.commit()

    def add_job(self, kind, path, url="", status="queued", **kwargs):
        now = int(time.time())
        jid = uuid.uuid4().hex[:16]
        self.db.execute("""INSERT INTO jobs
             (id,kind,url,path,status,done,total,speed,gid,error,added,updated,meta)
             VALUES (?,?,?,?,?,0,0,0,'','',?,?,'{}')""",
             (jid, kind, url.strip(), str(Path(path).expanduser().absolute()), status, now, now))
        if url:
            self.remember_url(path, url, commit=False)
        self.db.commit()
        return jid

    def remember_url(self, path, url, commit=True):
        self.db.execute("""INSERT INTO url_history VALUES (?,?,?)
                ON CONFLICT(path) DO UPDATE SET url=excluded.url,updated=excluded.updated""",
                (str(Path(path).expanduser().absolute()), url.strip(), int(time.time())))
        if commit:
            self.db.commit()

    def resolve_url(self, path):
        key = str(Path(path).expanduser().absolute())
        row = self.db.execute("SELECT url FROM url_history WHERE path=?", (key,)).fetchone()
        if row:
            return row[0]
        # A file could have been moved after downloading.
        basename = Path(path).name
        rows = self.db.execute("SELECT path,url FROM url_history ORDER BY updated DESC").fetchall()
        matches = [r["url"] for r in rows if Path(r["path"]).name == basename]
        return matches[0] if len(set(matches)) == 1 and matches else ""

    def update(self, jid, **fields):
        allowed = {"url", "path", "status", "done", "total", "speed", "gid", "error", "meta"}
        values = {k: v for k, v in fields.items() if k in allowed}
        if not values:
            return
        values["updated"] = int(time.time())
        self.db.execute("UPDATE jobs SET " + ",".join(f"{k}=?" for k in values) + " WHERE id=?",
                        list(values.values()) + [jid])
        if values.get("url"):
            row = self.get(jid)
            if row:
                self.remember_url(row["path"], values["url"], False)
        self.db.commit()

    def get(self, jid):
        row = self.db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        return dict(row) if row else None

    def all_jobs(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM jobs ORDER BY added DESC,id DESC")]

    def log(self, jid, detail, severity="info"):
        self.db.execute("INSERT INTO events(job_id,stamp,severity,detail) VALUES(?,?,?,?)",
                        (jid, int(time.time()), severity, str(detail)[:6000]))
        self.db.commit()

    def events(self, jid, limit=80):
        return [dict(r) for r in self.db.execute("SELECT * FROM events WHERE job_id=? ORDER BY id DESC LIMIT ?", (jid, limit))][::-1]

    def delete(self, jid):
        # Never delete downloaded files or saved URL associations here.
        self.db.execute("DELETE FROM jobs WHERE id=?", (jid,))
        self.db.execute("DELETE FROM events WHERE job_id=?", (jid,))
        self.db.commit()

    def close(self):
        self.db.close()
