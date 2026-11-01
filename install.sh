#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v aria2c >/dev/null || ! command -v curl >/dev/null || ! command -v 7z >/dev/null; then
  echo 'Install system tools on Manjaro: sudo pacman -S --needed aria2 curl 7zip'
fi
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
# Do not update pip or re-download PySide6 when upgrading an existing install.
if .venv/bin/python -c 'import PySide6.QtCore, PySide6.QtGui, PySide6.QtWidgets; print("Qt dependencies already installed — skipping pip")' 2>/dev/null; then
  :
else
  .venv/bin/python -m pip install -r requirements.txt
fi
printf '\nSetup complete! Run: ./start.sh\n'
