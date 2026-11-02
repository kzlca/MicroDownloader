# Apply v0.5.2 to your existing GitHub repository

Use the **patch ZIP** (not the full source archive) on top of your existing checkout. **Do not delete your repository or `.git` folder.** Neither the patch nor the release process touches downloaded archives, per-user SQLite data or `.aria2` resume metadata.

From Manjaro:

```bash
cd "$HOME/Desktop/Micro Downloader/Gihhub/MicroDownloader-git"
unzip -oq "$HOME/Downloads/MicroDownloader_v0.5.2_Backend_Recovery_Patch.zip" -d .
python3 -m unittest discover -s tests -v
git diff --check
git status --short
git add -A
git commit -m "Improve aria2 startup and reconnect reliability (v0.5.2)"
git push origin main
```

Before publishing, start a **manual test build** (does not create a GitHub release):

```bash
gh workflow run release.yml --ref main -R kzlca/MicroDownloader
gh run list --workflow release.yml -R kzlca/MicroDownloader --limit 3
```

Watch the newly created run with `gh run watch RUN_ID -R kzlca/MicroDownloader --exit-status`. Only if Windows and Linux pass:

```bash
git tag -a v0.5.2 -m "Micro Downloader v0.5.2"
git push origin v0.5.2
```

Verify publication:

```bash
gh release view v0.5.2 -R kzlca/MicroDownloader --json isDraft,assets \
 --jq '{published:(.isDraft|not),files:[.assets[].name]}'
```

The existing v0.5.1 release must remain available to users until v0.5.2 is validated on actual Windows computers.

## Windows first-launch verification

After installing the v0.5.2 Setup on an affected Windows PC, restart the computer and open Micro Downloader. Add a small publicly available download and verify it starts without closing the application. Repeat after another Windows restart. The app will keep downloads queued until the download engine is connected. The **Engine → Restart download engine** command provides a manual fallback. If the problem persists, attach `%LOCALAPPDATA%\MicroDownloader\backend.log` and `aria2.log` to a bug report after removing any sensitive URLs or tokens.

Tests bundled: 29 local non-Qt tests plus GitHub Actions Qt smoke tests and a bundled aria2 localhost JSON-RPC/download smoke test. Actual CI outcomes are not yet known.
