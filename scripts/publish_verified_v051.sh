#!/usr/bin/env bash
# Run from any directory after committing/pushing Hotfix 03 to main.
# Builds main, publishes v0.5.1 ONLY if both Windows and Linux pass, then
# verifies that all four public installer assets really exist.
set -Eeuo pipefail
REPO='kzlca/MicroDownloader'
TAG='v0.5.1'
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [[ "$(git branch --show-current)" != 'main' ]]; then
  echo 'ERROR: switch to the main branch before releasing.' >&2; exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'ERROR: uncommitted changes. Commit and push the fix first.' >&2; exit 1
fi
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git ls-remote origin refs/heads/main | cut -f1)"
if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  echo 'ERROR: local HEAD differs from origin/main. Push first.' >&2; exit 1
fi
if [[ -n "$(git ls-remote --tags origin "refs/tags/$TAG")" ]]; then
  echo "ERROR: $TAG already exists remotely; won't replace a tag." >&2; exit 1
fi

printf '\n[1/3] Building both platforms from %s ...\n' "$LOCAL_SHA"
OUTPUT="$(gh workflow run release.yml --ref main -R "$REPO" 2>&1)"
printf '%s\n' "$OUTPUT"
RUN_ID="$(printf '%s\n' "$OUTPUT" | sed -nE 's@.*actions/runs/([0-9]+).*@\1@p' | head -n 1)"
if [[ -z "$RUN_ID" ]]; then
  echo 'ERROR: Could not extract run ID. Inspect Actions manually; no tag created.' >&2; exit 1
fi
if ! gh run watch "$RUN_ID" -R "$REPO" --interval 5 --exit-status; then
  echo 'ERROR: build failed. Release tag has NOT been created.' >&2; exit 1
fi
BUILT_SHA="$(gh run view "$RUN_ID" -R "$REPO" --json headSha --jq .headSha)"
if [[ "$BUILT_SHA" != "$LOCAL_SHA" ]]; then
  echo 'ERROR: build ran against a different commit; refusing to tag.' >&2; exit 1
fi

printf '\n[2/3] Both platforms passed. Creating the release tag %s ...\n' "$TAG"
git tag -a "$TAG" -m 'Micro Downloader v0.5.1 - verified installer release'
git push origin "$TAG"

# Github tag workflows start asynchronously. Find the fresh release run.
RELEASE_RUN=''
for attempt in {1..40}; do
  RELEASE_RUN="$(gh run list -R "$REPO" --workflow release.yml --limit 20 --json databaseId,headBranch,event,headSha --jq ".[] | select(.headBranch == \"$TAG\" and .headSha == \"$LOCAL_SHA\") | .databaseId" | head -n 1)"
  if [[ -n "$RELEASE_RUN" ]]; then break; fi
  sleep 3
done
if [[ -z "$RELEASE_RUN" ]]; then
  echo "ERROR: tag pushed but no tagged workflow found yet. Check GitHub Actions." >&2; exit 1
fi
if ! gh run watch "$RELEASE_RUN" -R "$REPO" --interval 5 --exit-status; then
  echo "ERROR: tag exists, but release workflow failed. No public links guaranteed." >&2; exit 1
fi

printf '\n[3/3] Verifying actual public release files ...\n'
mapfile -t ASSETS < <(gh release view "$TAG" -R "$REPO" --json assets --jq '.assets[].name')
for filename in \
    'MicroDownloader-0.5.1-windows-x64-Setup.exe' \
    'MicroDownloader-0.5.1-linux-x64.pkg.tar.zst' \
    'MicroDownloader-0.5.1-linux-x64.deb' \
    'MicroDownloader-0.5.1-linux-x64.rpm'; do
  if ! printf '%s\n' "${ASSETS[@]}" | grep -Fxq -- "$filename"; then
    echo "ERROR: missing GitHub asset $filename" >&2; exit 1
  fi
  echo "https://github.com/$REPO/releases/download/$TAG/$filename"
done
printf '\nAll four installer assets are published.\n'
