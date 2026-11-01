# Publish Micro Downloader from Manjaro

This repository is prepared for **kzlca/MicroDownloader**. These instructions use the [GitHub CLI](https://cli.github.com/); you should already be authenticated with `gh auth status`. The local `.venv`, downloaded archives, and your existing installed application do **not** need to be copied or uploaded.

## 1. Create the repository and upload source

Run from this extracted **source project directory** (the folder containing `run.py`, `README.md`, and `.github/`), **not** from your active downloads directory:

```bash
gh auth status
git init -b main
git config user.name "kzlca"
# Use your GitHub noreply address if you do not want to disclose your email:
git config user.email "$(gh api user --jq .id)+kzlca@users.noreply.github.com"
git add .
git status --short
git commit -m "Initial public release: Micro Downloader v0.5.0"
gh repo create kzlca/MicroDownloader --public --source=. --remote=origin --push \
  --description "Qt download manager with verified recovery of incomplete sparse files"
gh repo edit kzlca/MicroDownloader --add-topic download-manager,python,qt,linux,windows,download-recovery
```

If Git asks for your email, set one with `git config user.email "your-GitHub-noreply-address"` and repeat the commit. If `gh repo create` says the repository exists, do **not** overwrite it; inspect it with `gh repo view kzlca/MicroDownloader --web` and reconcile the existing remote/history.

`git status --short` before committing is an important safety check: it should not contain any RAR archives, real user databases, passwords, access tokens or `.venv` binaries. `.gitignore` excludes the common forms of these files, but inspect all staged files anyway.

## 2. Confirm GitHub Actions checks

On `main` the **Quality checks** workflow compiles the sources and runs the Linux unit, recovery and Qt smoke tests. The Windows job checks Python source compatibility. Open:

https://github.com/kzlca/MicroDownloader/actions

Before publishing the first stable release, optionally test native package compilation **without publishing a release**:

```bash
gh workflow run release.yml --ref main -R kzlca/MicroDownloader
gh run list --workflow release.yml -R kzlca/MicroDownloader --limit 3
```

A manually dispatched workflow stores installers under its workflow-run **Artifacts**, but does **not** create a public GitHub Release.

## 3. Create the real release

After the checks pass:

```bash
git tag -a v0.5.0 -m "Micro Downloader v0.5.0"
git push origin v0.5.0
```

That tag triggers the Windows Inno Setup `.exe` and Linux `.deb`, `.rpm`, and `.pkg.tar.zst` builders. When both builder jobs succeed, the release job attaches the four installers and `SHA256SUMS.txt` to the public release.

See the build and release jobs using:

```bash
gh run list --workflow release.yml -R kzlca/MicroDownloader --limit 5
gh release view v0.5.0 -R kzlca/MicroDownloader --web
```

### Direct installer links (valid after a successful release)

- Windows: https://github.com/kzlca/MicroDownloader/releases/download/v0.5.0/MicroDownloader-0.5.0-windows-x64-Setup.exe
- Manjaro/Arch: https://github.com/kzlca/MicroDownloader/releases/download/v0.5.0/MicroDownloader-0.5.0-linux-x64.pkg.tar.zst
- Ubuntu/Debian: https://github.com/kzlca/MicroDownloader/releases/download/v0.5.0/MicroDownloader-0.5.0-linux-x64.deb
- Fedora: https://github.com/kzlca/MicroDownloader/releases/download/v0.5.0/MicroDownloader-0.5.0-linux-x64.rpm

**Checksums:** https://github.com/kzlca/MicroDownloader/releases/download/v0.5.0/SHA256SUMS.txt

Do not announce these installer links until the release workflow has completed successfully and the assets are visible.

## 4. Fix a failed build

Inspect the failure in **Actions**, repair the code, and push a normal commit to `main`. Prefer creating a new version/tag (e.g., `v0.5.1`) instead of moving a published tag. Avoid replacing published binaries silently.

```bash
git add .
git commit -m "Fix release build"
git push origin main
git tag -a v0.5.1 -m "Micro Downloader v0.5.1"
git push origin v0.5.1
```

Update `micro_downloader/__init__.py`, the UI version label, and README filename links when changing application versions.

## Release authenticity and compatibility

- CI-built binaries are not digitally signed by default. Windows may display SmartScreen warnings.
- GitHub-hosted Ubuntu-built binaries use glibc from the runner; test `.deb`, `.rpm`, and Arch packages on the target distributions.
- Windows NTFS recovery needs a real NTFS test, not just a successful build.
- The first release is x64 only; ARM and macOS are not included.
- End users do not need PySide6 or pip, but Linux packages depend on the system `aria2` and `curl` executables.
