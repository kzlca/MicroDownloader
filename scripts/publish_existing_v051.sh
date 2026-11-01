#!/usr/bin/env bash
# Publish already successfully built installers from the v0.5.1 tag workflow.
# Does NOT rebuild binaries, re-tag commits, or alter downloaded user files.
set -Eeuo pipefail
REPO='kzlca/MicroDownloader'
TAG='v0.5.1'
RUN='41360538557'
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

for cmd in git gh python3; do command -v "$cmd" >/dev/null || { echo "Missing: $cmd" >&2; exit 1; }; done
gh auth status >/dev/null
if [[ "$(git branch --show-current)" != main ]]; then
  echo 'Switch to the main branch before running.' >&2; exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Commit/push any changes before publishing.' >&2; exit 1
fi
if [[ "$(git rev-parse HEAD)" != "$(git ls-remote origin refs/heads/main | cut -f1)" ]]; then
  echo 'Your local main and remote main differ; sync first.' >&2; exit 1
fi
if ! gh api "repos/$REPO/git/ref/tags/$TAG" --jq .ref >/dev/null 2>&1; then
  echo "Remote tag $TAG not found; refusing to publish." >&2; exit 1
fi
if gh release view "$TAG" -R "$REPO" >/dev/null 2>&1; then
  echo "GitHub Release $TAG already exists. Refusing to overwrite it." >&2
  echo "Review https://github.com/$REPO/releases/tag/$TAG" >&2
  exit 1
fi

# The run failed only AFTER both build jobs succeeded, at release asset validation.
mapfile -t RESULTS < <(gh run view "$RUN" -R "$REPO" --json jobs \
  --jq '.jobs[] | select(.name | startswith("build (")) | .conclusion')
if [[ "${#RESULTS[@]}" != 2 || "${RESULTS[0]}" != success || "${RESULTS[1]}" != success ]]; then
  echo "The tagged CI run does not show two successful platform builds: ${RESULTS[*]}" >&2
  exit 1
fi

WORK="$(mktemp -d -t micro-release-XXXXXXXX)"
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/artifacts/windows" "$WORK/artifacts/linux" "$WORK/out"
printf '\n[1/4] Downloading already-built Windows installer ...\n'
gh run download "$RUN" -R "$REPO" -n micro-downloader-windows -D "$WORK/artifacts/windows"
printf '\n[2/4] Downloading already-built Linux installers ...\n'
gh run download "$RUN" -R "$REPO" -n micro-downloader-linux -D "$WORK/artifacts/linux"
printf '\n[3/4] Checking real installers and preparing release assets ...\n'
python3 scripts/prepare_release_assets.py --artifacts "$WORK/artifacts" --out "$WORK/out" --version 0.5.1

BASE="https://github.com/$REPO/releases/download/$TAG"
cat > "$WORK/out/RELEASE_NOTES.md" <<EOF
# Micro Downloader v0.5.1

Desktop download manager with verified recovery for missing or incomplete files.

| Platform | Installer |
|---|---|
| Windows 10/11 (x64) | [Download Setup EXE]($BASE/MicroDownloader-0.5.1-windows-x64-Setup.exe) |
| Manjaro / Arch Linux (x64) | [Download Pacman package]($BASE/MicroDownloader-0.5.1-linux-x64.pkg.tar.zst) |
| Ubuntu / Debian (x64) | [Download DEB]($BASE/MicroDownloader-0.5.1-linux-x64.deb) |
| Fedora / RPM Linux (x64) | [Download RPM]($BASE/MicroDownloader-0.5.1-linux-x64.rpm) |

[SHA256 checksums]($BASE/SHA256SUMS.txt)

The installers were produced by successful Windows/Linux build jobs in workflow run $RUN. Linux uses system aria2 and curl. Windows installer is unsigned; some machines may show SmartScreen warnings.
EOF

printf '\n[4/4] Publishing public GitHub Release ...\n'
gh release create "$TAG" \
  "$WORK/out/MicroDownloader-0.5.1-windows-x64-Setup.exe" \
  "$WORK/out/MicroDownloader-0.5.1-linux-x64.pkg.tar.zst" \
  "$WORK/out/MicroDownloader-0.5.1-linux-x64.deb" \
  "$WORK/out/MicroDownloader-0.5.1-linux-x64.rpm" \
  "$WORK/out/SHA256SUMS.txt" \
  -R "$REPO" --verify-tag --title 'Micro Downloader v0.5.1' \
  --notes-file "$WORK/out/RELEASE_NOTES.md" --latest

mapfile -t PUBLISHED < <(gh release view "$TAG" -R "$REPO" --json assets --jq '.assets[].name')
for NAME in \
  MicroDownloader-0.5.1-windows-x64-Setup.exe \
  MicroDownloader-0.5.1-linux-x64.pkg.tar.zst \
  MicroDownloader-0.5.1-linux-x64.deb \
  MicroDownloader-0.5.1-linux-x64.rpm SHA256SUMS.txt; do
  if ! printf '%s\n' "${PUBLISHED[@]}" | grep -Fxq -- "$NAME"; then
    echo "Missing published GitHub asset: $NAME" >&2
    exit 1
  fi
  echo "VERIFIED: $BASE/$NAME"
done

# Only after confirming the actual public release, update the project homepage.
python3 - "$BASE" <<'PY'
from pathlib import Path
import sys
base = sys.argv[1]
p = Path('README.md')
s = p.read_text(encoding='utf-8')
start = s.find('## Downloads\n')
end = s.find('\n## Features', start)
if start == -1 or end == -1:
    raise SystemExit('README section not found; release is published, update links manually.')
replacement = f'''## Downloads

**Install Micro Downloader directly from GitHub Releases:**

| Operating system | Direct installer |
|---|---|
| Windows 10/11 (x64) | [Download Windows Setup (.exe)]({base}/MicroDownloader-0.5.1-windows-x64-Setup.exe) |
| Manjaro / Arch (x64) | [Download Pacman package]({base}/MicroDownloader-0.5.1-linux-x64.pkg.tar.zst) |
| Ubuntu / Debian (x64) | [Download Debian package]({base}/MicroDownloader-0.5.1-linux-x64.deb) |
| Fedora / RPM (x64) | [Download RPM package]({base}/MicroDownloader-0.5.1-linux-x64.rpm) |

[All releases](https://github.com/kzlca/MicroDownloader/releases) · [SHA-256 checksums]({base}/SHA256SUMS.txt)

Packaged installers include Python and Qt. Linux requires system aria2/curl. Windows Setup is unsigned.
'''
p.write_text(s[:start] + replacement + s[end:], encoding='utf-8')
PY
if ! git diff --quiet -- README.md; then
  git add README.md
  git commit -m 'Add verified direct installer download links to README'
  if ! git push origin main; then
    echo 'WARNING: Release published, but README push failed. Push your README update manually.' >&2
  fi
fi
printf '\nSUCCESS: https://github.com/%s/releases/tag/%s\n' "$REPO" "$TAG"
