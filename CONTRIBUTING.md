# Contributing to Micro Downloader

Thank you for helping improve download reliability and recovery safety.

## Getting started

1. Open an issue for a substantial feature or a breaking change before implementing it.
2. Fork this repository, branch from `main`, and keep changes focused.
3. Install the requirements from `requirements.txt` and run the tests.
4. Open a pull request with an explanation and test results.

```bash
python -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen python scripts/smoke_ui.py
```

The UI smoke test requires PySide6-Essentials; some filesystem-recovery tests only work on Linux. For Windows-related changes, include the Windows version and the filesystem (usually NTFS) used during testing.

## Recovery safety requirements

- Verification must never change the target file.
- Repair must validate HTTP `206 Partial Content`, `Content-Range`, and the expected response length before accepting data.
- Do not silently overwrite unknown allocated data or proceed after sample verification fails.
- Protect user files and stored transfer metadata across upgrades.
- Add a regression test for a bug fix when practical.

## Languages

Catalogs live in `micro_downloader/assets/i18n/`. Keep keys stable, validate right-to-left layouts, and preserve left-to-right direction for URLs and paths. Fonts are not bundled.

## Style and communications

Use clear, focused commits and describe observable behavior rather than unsupported performance or reliability claims. Never include private download URLs, access tokens, log files, downloaded archives, or customer data in an issue or pull request.
