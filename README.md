<div align="center">
  <img src="micro_downloader/assets/logo.png" width="128" alt="Micro Downloader logo" />

  # Micro Downloader

  **A desktop download manager built to recover interrupted and incomplete files — not just restart them.**

  [![CI](https://github.com/kzlca/MicroDownloader/actions/workflows/ci.yml/badge.svg)](https://github.com/kzlca/MicroDownloader/actions/workflows/ci.yml)
  [![Releases](https://img.shields.io/github/v/release/kzlca/MicroDownloader?label=release)](https://github.com/kzlca/MicroDownloader/releases)
  [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

  **Windows · Linux · English · فارسی · Türkçe**

  [Download](#downloads) · [Features](#features) · [How recovery works](#how-recovery-works) · [Build](BUILDING.md) · [Contribute](CONTRIBUTING.md)
</div>

---

## Why Micro Downloader?

A download interrupted during multi-connection transfer can have a **full-sized file on disk** with **missing, unallocated byte ranges inside it**. Simply resuming from the end may fail, and starting over wastes the bytes you already downloaded.

Micro Downloader can identify sparse gaps, visualize them in **green (allocated)** and **yellow (unallocated)**, verify the existing file against the original server and request only the missing byte ranges with overlap around damaged boundaries. It also functions as a general-purpose download manager.

> **Recovery is conditional, not magical.** The source URL must still serve the *same file* and correctly support HTTP byte-range requests. Allocated bytes are **not** proof of integrity. Always validate the completed file using a trusted checksum or archive test. If the file is not sparse, the app cannot deduce missing data from allocation alone.

## Downloads

[**Browse releases and download installers**](https://github.com/kzlca/MicroDownloader/releases)

The release pipeline publishes separate, native installer assets for each platform:

| Platform | File in release assets |
|---|---|
| Windows 10/11 · x64 | `MicroDownloader-0.5.1-windows-x64-Setup.exe` |
| Arch Linux / Manjaro · x64 | `MicroDownloader-0.5.1-linux-x64.pkg.tar.zst` |
| Ubuntu / Debian · x64 | `MicroDownloader-0.5.1-linux-x64.deb` |
| Fedora / RPM · x64 | `MicroDownloader-0.5.1-linux-x64.rpm` |

**The release page is the working entry point until v0.5.1 is actually published.** GitHub will only serve direct asset links once the Windows and Linux CI jobs succeed and upload the corresponding files. Each published GitHub Release contains direct per-platform links and SHA-256 checksums.

No Python/PySide6 installation is needed for packaged installers; Linux requires system `aria2` and `curl`. Windows Setup is an unsigned binary until code signing is configured, so Windows may display a security prompt.

## Features

| Download manager | Sparse recovery | Desktop experience |
|---|---|---|
| aria2-based queue and concurrent downloads | Sparse allocation inspection (Linux ext4; NTFS support requires Windows testing) | Responsive Qt interface |
| Pause/resume, speed caps, proxy options | Exact HTTP range requests with server validation | Direct actions on every transfer card |
| Saved URLs and history in local SQLite | Read-only sample verification before repair | English, Persian RTL and Turkish |
| Live speed graph | Green/yellow block map; protected edge overlap | Native Windows and Linux installers |
| 7-Zip archive checks | Backup of replaced boundary data | Logo and desktop integration |

## How recovery works

1. Choose **Recover file** and select an existing incomplete download.
2. Enter its original **direct HTTP(S) URL**. URLs are saved to the local database.
3. Inspect the **allocation map** and run **Verify ranges** first; this compares existing local samples with the server.
4. If the verification passes, select **Repair missing bytes** to download the missing extents and refresh surrounding boundary bytes.
5. Verify the final result with an official checksum or **Test archive**. Multipart RAR archives require *every* volume, including the final smaller part.

**Safety:** Existing downloaded files are never intentionally removed by upgrading the application. Never test recovery on your only copy of irreplaceable data. Repair is implemented with bounded writes and can modify the chosen file after verification. URL history is stored locally, not encrypted; avoid credential-bearing URLs. See [SECURITY.md](SECURITY.md).

## Run from source

On Arch Linux / Manjaro:

```bash
sudo pacman -S --needed python aria2 curl 7zip
./install.sh
./start.sh
```

The installer uses **PySide6-Essentials**, not the larger full PySide6 distribution. Existing virtual environments can be reused. On other systems, see [BUILDING.md](BUILDING.md).

## Development and releases

The repository uses Python 3, **PySide6 Qt Widgets**, aria2's local JSON-RPC API, curl for verified HTTP byte ranges, and SQLite for persistent download metadata.

```bash
python3 -m compileall -q micro_downloader run.py scripts
python3 -m unittest discover -s tests -v
# With PySide6 installed:
QT_QPA_PLATFORM=offscreen python3 -m scripts.smoke_ui
```

On a push to `main`, GitHub Actions checks the project. On the `v0.5.1` tag, the release workflow builds the Windows Setup EXE and native Linux packages and attaches them to a GitHub Release. **The build workflow is provided, but published installers still need successful CI runs and real-system verification.** See [PUBLISHING.md](PUBLISHING.md).

## Help and contributing

Issues and feature requests: [GitHub Issues](https://github.com/kzlca/MicroDownloader/issues). Please include operating system, version, reproduction steps, and sanitized logs. Pull requests, localization contributions, security reviews, Windows NTFS verification and accessibility improvements are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

Created and maintained as a portfolio project by [@kzlca](https://github.com/kzlca). Licensed under the [MIT License](LICENSE).
