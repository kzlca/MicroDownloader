#!/usr/bin/env python3
"""Verify all four platform installer names before publishing GitHub Releases."""
import argparse
from pathlib import Path


def expected(version):
    prefix = f"MicroDownloader-{version}"
    return [
        f"{prefix}-windows-x64-Setup.exe",
        f"{prefix}-linux-x64.deb",
        f"{prefix}-linux-x64.rpm",
        f"{prefix}-linux-x64.pkg.tar.zst",
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--dir', type=Path, default=Path('release'))
    args = parser.parse_args()
    issues = []
    for name in expected(args.version):
        p = args.dir / name
        if not p.is_file():
            issues.append(f"MISSING: {name}")
        elif p.stat().st_size == 0:
            issues.append(f"EMPTY: {name}")
        else:
            print(f"OK: {name} ({p.stat().st_size:,} bytes)")
    if issues:
        raise SystemExit('\n'.join(issues))
    print('All four required installer assets are present.')


if __name__ == '__main__':
    main()
