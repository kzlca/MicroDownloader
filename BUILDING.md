# Native installer builds — v0.5.0

Release default is **installable software**, not portable ZIP/single-ELF downloads.

## Build Windows setup

On Windows x64 install Python 3.11, Inno Setup 6.6+, and a real `aria2c.exe` (required). Optionally locate `7z.exe` + `7z.dll` for archive tests. In a PowerShell terminal:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
$env:MICRO_DOWNLOADER_ARIA2_BIN = 'C:\path\to\aria2c.exe'
$env:MICRO_DOWNLOADER_7ZIP_DIR = 'C:\Program Files\7-Zip'
.\.venv\Scripts\python.exe scripts\build_release.py --mode installer --version 0.5.0
```

The Inno Setup compiler (`ISCC.exe`) must be installed. The Setup executable appears in `release/`. The wizard uses a user-level install folder and preserves `%LOCALAPPDATA%\MicroDownloader` on uninstall. A Windows release from CI bundles `aria2c.exe` and `7z.exe` / `7z.dll`, when provided by the setup workflow.

## Build Linux packages

Use Ubuntu 22.04 x64 for compatibility with older glibc (other distributions require native testing). Install `dpkg-deb`, `rpmbuild` (rpm package), and `zstd` in addition to Python 3.11 and dependencies.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python scripts/build_release.py --mode installer --version 0.5.0
```

`release/` contains `.deb`, `.rpm`, and `.pkg.tar.zst` when their packaging utilities are available. All install to `/opt/micro-downloader` and register `/usr/share/applications/micro-downloader.desktop` plus an icon in hicolor. System `aria2` and `curl` are package dependencies. Archive checking additionally requires 7-Zip. Linux packages should be tested on real distributions before publication; a Qt ELF built on one distro can still have incompatible native libraries elsewhere.

### Upgrade and safe storage

Installers replace **application binaries only**. User files, original download URLs, SQLite history and recovery state are stored outside the app folder. Avoid downloading into the app install folder. An installer does not migrate users' *portable binary files*, but the existing stored transfer history remains.

To update an existing source checkout without reinstalling Qt or deleting `.venv`, run:

```bash
./upgrade_existing.sh "$HOME/Desktop/Micro Downloader/MicroDownloader"
```

For small Persian text, Amiri is preferred if already installed. This distribution intentionally does not ship font files. The interface falls back to installed Arabic-script fonts otherwise.

---

## Publish all packages and link directly from GitHub

See **[PUBLISHING.md](PUBLISHING.md)** for current, tested-command instructions for tagging v0.5.0, automatic release uploads, and the correct installer names. Do not use old v0.4.1 tags: a Release is published only after a successful tag-triggered workflow.

## Existing installations

Updating an extracted source tree in place with `cp -a` does not delete the user's `.venv` or downloads, but *always close the app first*. Do not use `rm -rf` or `rsync --delete` against an existing user install.

The database remains in the user's OS-specific application data directory, not in the source tree. Even so, back it up before a major release if it contains important URLs.

## Limitations and safety

- The recovery engine requires byte-range support (`206 Partial Content` with an exact `Content-Range`) and a matching remote file. Existing samples are checked before writes.
- Sparse gaps are not the same as a cryptographic digest. Corrupted allocated bytes can remain, and multi-volume archives may lack subsequent parts.
- 7-Zip passwords are entered ephemerally and not stored; its CLI `-pPASSWORD` parameter may briefly appear in the operating system process list. Do not test sensitive passwords on a shared machine.
- If third-party tools are unavailable, the GUI remains usable, but some features cannot run.
