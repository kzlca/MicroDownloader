# Publishing Micro Downloader v0.5.2

Micro Downloader 0.5.2 adds non-blocking aria2 initialization and automatic backend reconnection. **Do not overwrite the existing `v0.5.1` Git tag or release.** The project is published from `kzlca/MicroDownloader`.

## 1. Review and test the update

Apply the `v0.5.2` patch to an existing clone of the Git repository. It does not include `.git`, user data, databases, downloaded files, `.aria2` control files, or your `.venv`.

```bash
python -m compileall -q micro_downloader scripts run.py
python -m unittest discover -s tests -v
# If PySide6 is installed:
QT_QPA_PLATFORM=offscreen python -m scripts.smoke_ui
QT_QPA_PLATFORM=offscreen python -m scripts.smoke_backend_ui
```

Commit and push the source:

```bash
git diff --check
git add -A
git commit -m "Make aria2 startup and reconnection resilient (v0.5.2)"
git push origin main
```

## 2. Test the build workflow on main first

```bash
gh workflow run release.yml --ref main -R kzlca/MicroDownloader
gh run list --workflow release.yml -R kzlca/MicroDownloader --limit 3
```

Watch the new run ID with `gh run watch RUN_ID -R kzlca/MicroDownloader --exit-status`. A manual run on `main` builds and tests Windows and Linux, but does not publish a GitHub Release.

The Windows job now checks the **bundled** aria2 executable via an actual loopback HTTP download and JSON-RPC, not just the GUI. Linux runs the equivalent test using system aria2. The release job checks out source before downloading build artifacts and normalizes their packaging paths before publishing.

## 3. Publish only after the manual build succeeds

```bash
git tag -a v0.5.2 -m "Micro Downloader v0.5.2"
git push origin v0.5.2
```

This triggers a fresh build. After its release job succeeds:

```bash
gh release view v0.5.2 -R kzlca/MicroDownloader \
  --json isDraft,assets --jq '{draft:.isDraft,files:[.assets[].name]}'
```

Expected assets:

- `MicroDownloader-0.5.2-windows-x64-Setup.exe`
- `MicroDownloader-0.5.2-linux-x64.pkg.tar.zst`
- `MicroDownloader-0.5.2-linux-x64.deb`
- `MicroDownloader-0.5.2-linux-x64.rpm`
- `SHA256SUMS.txt`

Release page: https://github.com/kzlca/MicroDownloader/releases/tag/v0.5.2

If one job fails, **do not recreate or force-push the tag**. Fix the issue on `main`, re-test, and use a subsequent patch version if a tag is already published. Keep existing downloads and databases outside the source/release build directory.

## Compatibility and safety

- CI smoke tests are not a substitute for real Windows first-launch tests, especially with antivirus scanning.
- The supervisor does not kill an aria2 process while it is still alive just because its RPC is temporarily unavailable; use the Engine menu for a manual restart.
- A process exit can invalidate aria2 GIDs. Interrupted transfers are requeued, but reuse of downloaded bytes still requires correct `.aria2` state files. Files lacking metadata are left untouched.
- Do not commit download archives, user databases, proxy credentials or private URLs.
