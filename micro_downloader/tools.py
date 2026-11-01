"""Find optional external transfer tools, including frozen Windows binaries."""
import os
import shutil
import sys
from pathlib import Path


def find_tool(name):
    suffix = '.exe' if os.name == 'nt' and not name.lower().endswith('.exe') else ''
    binary = name + suffix
    paths = []
    frozen = getattr(sys, '_MEIPASS', None)
    if frozen:
        paths.append(Path(frozen) / 'bin' / binary)
    if getattr(sys, 'frozen', False):
        paths.append(Path(sys.executable).resolve().parent / 'bin' / binary)
    if os.name == 'nt' and binary.lower() in ('7z.exe', '7zz.exe'):
        for env in ('ProgramFiles', 'ProgramFiles(x86)'):
            if os.environ.get(env):
                paths.append(Path(os.environ[env]) / '7-Zip' / binary)
    for path in paths:
        if path.is_file():
            return str(path)
    return shutil.which(binary) or shutil.which(name)
