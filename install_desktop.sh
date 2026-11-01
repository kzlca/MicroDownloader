#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 - "$PWD" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
target = Path.home()/'.local/share/applications/micro-downloader.desktop'
target.parent.mkdir(parents=True, exist_ok=True)
# Desktop file double-quoted exec values permit spaces in unpack directory.
program = str(path/'start.sh').replace('\\', '\\\\').replace('"','\\"')
working = str(path).replace('\\', '\\\\')
target.write_text(f'''[Desktop Entry]\nType=Application\nVersion=1.0\nName=Micro Downloader\nComment=Download and recover interrupted files\nExec="{program}"\nPath={working}\nIcon={path / "micro_downloader" / "assets" / "logo.png"}\nTerminal=false\nCategories=Network;FileTransfer;Utility;\nStartupNotify=true\n''')
legacy = Path.home()/'.local/share/applications/velora-download.desktop'
if legacy.is_file() and 'Name=Velora Download Manager' in legacy.read_text(errors='replace'):
    legacy.unlink()
    print('Removed old Velora desktop shortcut (old application files preserved).')
print('Desktop shortcut installed at', target)
PY
