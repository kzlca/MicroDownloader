# Micro Downloader architecture

**Qt UI**: `micro_downloader/ui.py` builds the responsive main window and manages the transfer queue. `widgets.py` contains dialogs and the allocated/missing block map. `speed_chart.py` paints the rolling speed trace using Qt, without a charting dependency.

**Download backend**: `engine.py` manages aria2 and communicates over JSON-RPC. The application stores URLs, status, settings and activity logs in `store.py` (SQLite). Download files live wherever users put them, outside the application data store.

**Recovery backend**: `sparse.py` inspects allocated extents on supported filesystems. `recovery.py` plans missing HTTP-range downloads, checks that the server returns the correct Content-Range and validates remote samples against previously allocated data before modifying the target. Recovery writes planned chunks only after validating their replies. The existing user data must never be truncated just to make a conventional downloader 'resume'.

**Archive verification**: `archive_check.py` parses 7-Zip's output and compares the reported volume count against local `partNN.rar` files. It distinguishes missing volumes, truncated archives, incorrect passwords (when indicated), and data/header errors. A green allocation map does *not* mean a complete archive; the full multipart test is the next required validation step.

**Internationalization**: `i18n.py` has English, Persian, Turkish, an RTL flag and optional JSON language packs. `translate_tree` retranslates static widget labels without rewriting URLs and filenames typed by the user.

**Packaging**: `scripts/build_release.py` uses PyInstaller and includes the icon assets; `.github/workflows/release.yml` builds both Linux and Windows artifacts. `upgrade_existing.sh` can merge source updates into a working installation while keeping `.venv`, downloads, and the stored SQLite history.

## Threat model and limits

- The remote URL must identify the exact same file (not merely the same name). The worker verifies multiple samples and HTTP ranges, but an end-to-end cryptographic digest is still the strongest integrity check.
- Filesystem sparse information is only an allocation map, not verification of all bytes. Non-sparse preallocated files may not be recoverable without external metadata.
- Original URLs might contain expiring tokens and are persisted in SQLite. Do not publish them or share your data directory.
- Archive passwords are never persisted, but the 7-Zip CLI process may briefly expose a passed `-pPASSWORD` argument to local process viewers. Avoid reused sensitive passwords.
- Multi-part RAR sets must include every numbered volume; a missing last part causes failures even if earlier volumes were repaired correctly.
