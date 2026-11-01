#!/usr/bin/env python3
"""Normalize and validate GitHub Actions installer artifacts for one release.

Only accepts exactly one Windows setup EXE and one each Linux Debian, RPM and
Arch package. Checks file magic and minimum size; never downloads or rebuilds.
"""
import argparse
import hashlib
from pathlib import Path
import shutil

KINDS = (
    ("Windows setup", "windows", "-Setup.exe", b"MZ", "windows-x64-Setup.exe"),
    ("Debian package", "linux", ".deb", b"!<arch>\n", "linux-x64.deb"),
    ("RPM package", "linux", ".rpm", bytes.fromhex("ed ab ee db"), "linux-x64.rpm"),
    ("Arch package", "linux", ".pkg.tar.zst", bytes.fromhex("28 b5 2f fd"), "linux-x64.pkg.tar.zst"),
)


def prepare(root: Path, out: Path, version: str) -> list[Path]:
    if not version or not all(c.isdigit() or c == '.' for c in version):
        raise ValueError('Expected numeric version like 0.5.1')
    if not (root / 'windows').is_dir() or not (root / 'linux').is_dir():
        raise FileNotFoundError('Download both Windows and Linux CI artifacts first')
    selections = []
    for label, platform, suffix, magic, target in KINDS:
        matches = sorted(p for p in (root / platform).rglob('*')
                         if p.is_file() and p.name.lower().endswith(suffix.lower()))
        if len(matches) != 1:
            listing = '\n'.join(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file())
            raise ValueError(f'{label}: expected 1 *{suffix} under {platform}, found {len(matches)}.\nFiles:\n{listing}')
        file = matches[0]
        if file.stat().st_size < 1_000_000:
            raise ValueError(f'{label} unexpectedly small: {file.stat().st_size:,} bytes ({file})')
        with file.open('rb') as f:
            signature = f.read(len(magic))
        if signature != magic:
            raise ValueError(f'{label} has unexpected file format: {file}')
        selections.append((label, file, f'MicroDownloader-{version}-{target}'))

    out.mkdir(parents=True, exist_ok=True)
    results = []
    for label, src, name in selections:
        dest = out / name
        shutil.copyfile(src, dest)
        print(f'PASS {label}: {src.name} -> {dest.name} ({dest.stat().st_size:,} bytes)', flush=True)
        results.append(dest)

    sums = []
    for dest in results:
        with dest.open('rb') as stream:
            sha = hashlib.file_digest(stream, 'sha256').hexdigest()
        sums.append(f'{sha}  {dest.name}')
    (out / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n', encoding='utf-8')
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--version', default='0.5.1')
    a = parser.parse_args()
    prepare(a.artifacts, a.out, a.version)


if __name__ == '__main__':
    main()
