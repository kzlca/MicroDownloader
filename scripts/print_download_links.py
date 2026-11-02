#!/usr/bin/env python3
"""Print Markdown direct-download links for a published GitHub release.

Example: python scripts/print_download_links.py YOUR_USERNAME/MicroDownloader 0.5.2
"""
import argparse


def markdown(repo: str, version: str) -> str:
    repo = repo.strip().strip('/')
    version = version.removeprefix('v')
    if not repo or repo.count('/') != 1 or not version or '/' in version:
        raise ValueError('Use OWNER/REPOSITORY and a numeric version such as 0.5.2')
    base = f'https://github.com/{repo}/releases/latest/download'
    names = [
        ('Windows 10/11 (x64)', f'MicroDownloader-{version}-windows-x64-Setup.exe'),
        ('Manjaro / Arch (x64)', f'MicroDownloader-{version}-linux-x64.pkg.tar.zst'),
        ('Ubuntu / Debian (x64)', f'MicroDownloader-{version}-linux-x64.deb'),
        ('Fedora / RPM-based (x64)', f'MicroDownloader-{version}-linux-x64.rpm'),
    ]
    lines = [f'## Download Micro Downloader v{version}', '',
             f'[View all releases](https://github.com/{repo}/releases/latest)', '',
             '| Platform | Direct download |', '|---|---|']
    lines += [f'| {platform} | [Download {name}]({base}/{name}) |' for platform, name in names]
    lines += ['', 'These links work after GitHub Actions builds and publishes the release assets.']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', help='OWNER/REPOSITORY, e.g. myname/MicroDownloader')
    parser.add_argument('version', nargs='?', default='0.5.2', help='Release version')
    a = parser.parse_args()
    print(markdown(a.repo, a.version))
