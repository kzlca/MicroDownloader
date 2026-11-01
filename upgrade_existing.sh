#!/usr/bin/env bash
# Merge new source into an existing install without removing downloads or .venv.
set -euo pipefail
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:?Usage: ./upgrade_existing.sh '/path/to/existing/VeloraDownload'}"
if [[ ! -d "$DEST" || ! -f "$DEST/run.py" ]]; then
  echo 'ERROR: existing installation folder must exist and contain run.py' >&2
  exit 1
fi
DEST="$(cd "$DEST" && pwd)"
if [[ "$SOURCE" == "$DEST" ]]; then
  echo 'Source and destination are identical; already updated.'
  exit 0
fi
if [[ "$DEST" == "$SOURCE"/* ]]; then
  echo 'ERROR: destination must not be inside the extracted update source.' >&2
  exit 1
fi
if pgrep -f "${DEST}/run.py" >/dev/null 2>&1; then
  echo 'NOTICE: An existing run.py process may be running; close the downloader before updating.'
fi
echo "Updating $DEST from $SOURCE"
cp -a "$SOURCE/." "$DEST/"
# Remove only the one confirmed obsolete importer module from old installations.
rm -f "$DEST/micro_downloader/kget.py"
echo 'Updated application source. Existing downloads, .venv, and SQLite data were not deleted.'
echo "Run: cd \"$DEST\" && ./start.sh"
