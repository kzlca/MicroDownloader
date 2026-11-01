# Changelog

## v0.5.0

- Transfer card per-item action grid with responsive wrapping; matching right-click action menu on all card surfaces.
- Filename labels no longer open an irrelevant native Copy/Select All menu.
- Larger sidebar logo. Optional system Amiri typography in Persian with sensible fallbacks.
- New Windows Inno Setup wizard, start-menu shortcuts and uninstaller.
- Linux-native Debian, RPM and Arch packages with icon/desktop entry.
- CI release workflow now publishes installers instead of single-file/portable builds.
- Download files and local databases are not included in or removed by installers.

## v0.4.1 — Startup and compact-layout stability fixes

- Fixed invalid standalone Qt stylesheet selector that crashed Python on startup (`NameError: QWidget`).
- Preserved the sidebar minimum content height so controls scroll at short window heights.
- Added a dedicated compact-language menu to avoid a clipped language selector in icon-mode navigation.
- Re-evaluate the speed chart at every window resize (including changes within the short-height range).
- Kept filenames, file paths and pasted URLs LTR in Persian RTL layouts.
- Localized stat-card headings using their source labels rather than English uppercased strings.
- Install script now reuses a working `.venv` without upgrading pip or downloading Qt again.
- Added regression checks for stylesheet import, package structure, and safe update behavior.
- Archive integrity still requires all RAR volumes; `part13` was missing in the reported test.

# Changelog

## v0.4.0 — Multilingual, accessible and release-focused

- New original Micro Downloader logo in application and packaged releases.
- Short-height sidebar now scrolls; compact navigation remains available when width is small.
- Removed the KGet importer UI, Python module, importer test, and documentation.
- English, Persian (RTL), Turkish, live language switching and expandable JSON localization packs.
- Left-to-right URL fields inside RTL pages.
- Real-time neon-green rolling download-speed graph.
- Archive tester prompts for an optional password, examines multipart RAR volume counts, and distinguishes missing volumes from data/header errors.
- Added archive/translation regression tests and enlarged Qt smoke test coverage.
- GitHub-ready README, updated automated release resources and desktop branding.

## v0.3.0

- Recover clicked(bool) crash fixed, responsive transfer-details panel, legacy data migration and portable Windows/Linux packaging support.
