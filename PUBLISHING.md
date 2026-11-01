# Publishing a fixed release on kzlca/MicroDownloader

## 1. Apply the fix to the existing checked-out Git repository

Do **not** create another Git repository and do **not** delete your `.venv`, database, or downloaded files. From the extracted v0.5.1 source, copy the updated files to your Git checkout (see the instructions provided with this patch).

Use `git status --short` and `git diff` to inspect all changes, then:

```bash
git add -A
git commit -m "Fix GUI CI import and Windows startup diagnostics"
git push origin main
```

## 2. Test on main, without creating a release

```bash
gh workflow run release.yml --ref main -R kzlca/MicroDownloader
gh run list -R kzlca/MicroDownloader --workflow release.yml --limit 3
```

Wait for the latest manual build to complete and inspect both Linux and Windows jobs. If Windows fails, the `Windows frozen app launch smoke test` step now prints a self-test report. A Windows diagnostic artifact is also uploaded for failing jobs when available.

Inspect a failed build with:

```bash
gh run view RUN_ID -R kzlca/MicroDownloader --log-failed
```

A manual build on `main` generates temporary build artifacts, **not** a public Release.

## 3. Publish v0.5.1 only after both builds pass

```bash
git tag -a v0.5.1 -m "Micro Downloader v0.5.1"
git push origin v0.5.1
```

The `v0.5.0` tag already exists and failed. Do not rewrite it or retag it. The new tag triggers Windows Inno Setup, Linux Debian/RPM/Arch packaging, verification of all four assets, and publication to GitHub Releases.

```bash
gh release view v0.5.1 -R kzlca/MicroDownloader --json assets --jq '.assets[].name'
```

This is the only time the direct URLs below are guaranteed to exist: **after the release succeeds**.

- Windows: https://github.com/kzlca/MicroDownloader/releases/download/v0.5.1/MicroDownloader-0.5.1-windows-x64-Setup.exe
- Manjaro/Arch: https://github.com/kzlca/MicroDownloader/releases/download/v0.5.1/MicroDownloader-0.5.1-linux-x64.pkg.tar.zst
- Ubuntu/Debian: https://github.com/kzlca/MicroDownloader/releases/download/v0.5.1/MicroDownloader-0.5.1-linux-x64.deb
- Fedora: https://github.com/kzlca/MicroDownloader/releases/download/v0.5.1/MicroDownloader-0.5.1-linux-x64.rpm

## Compatibility notes

- GitHub Actions build success does not substitute for real Windows and Linux installer testing.
- Windows binaries are unsigned and may show SmartScreen warnings.
- Frozen Linux executables depend on the glibc compatibility of their build host.
- Never commit credentials, real user databases, or downloaded archives.

## Troubleshooting the previous Windows CI crash

The previous Windows self-test forced `QT_QPA_PLATFORM=offscreen`, then logged
`QFontDatabase: Cannot find font directory .../PySide6/lib/fonts` before exiting
unsuccessfully. v0.5.1 hotfix 03 uses `QT_QPA_PLATFORM=windows` on the Windows
runner so Qt uses Windows' installed fonts and the packaged Windows QPA plugin.
It also records a checkpoint for each startup stage in the diagnostic artifact.
This is a targeted change, not proof of a successful Windows run; the next
Windows Actions job must pass before tagging the release.

After a successful tagged build, verify all assets with:

```bash
gh release view v0.5.1 -R kzlca/MicroDownloader --json assets --jq '.assets[].name'
```

Do not make the README point directly to unverified release asset URLs. The
Releases index link itself remains usable before the first release.
