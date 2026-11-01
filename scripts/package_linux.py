#!/usr/bin/env python3
"""Build Linux native packages from a PyInstaller ONEDIR distribution.

No Python or Qt installation is required on end-user machines. However,
Linux distro binary compatibility depends on the build runner/glibc version.
Creates .deb, .rpm (when rpmbuild exists), and Arch .pkg.tar.zst.
"""
import argparse
import io
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = """[Desktop Entry]
Type=Application
Version=1.0
Name=Micro Downloader
Name[fa]=میکرو دانلودر
Name[tr]=Micro Downloader
Comment=Download and recover incomplete files
Comment[fa]=مدیریت دانلود و بازیابی فایل‌های ناقص
Comment[tr]=İndirilen dosyaları yönet ve eksik verileri kurtar
Exec=/opt/micro-downloader/MicroDownloader
TryExec=/opt/micro-downloader/MicroDownloader
Icon=micro-downloader
Terminal=false
Categories=Network;FileTransfer;Utility;
StartupNotify=true
StartupWMClass=MicroDownloader
"""


def stage_payload(stage, dist):
    stage = Path(stage)
    dist = Path(dist)
    if not (dist/'MicroDownloader').is_file():
        raise FileNotFoundError(f'No frozen binary at {dist}/MicroDownloader')
    target = stage/'opt/micro-downloader'
    shutil.copytree(dist, target, symlinks=True)
    (target/'MicroDownloader').chmod(0o755)
    desk = stage/'usr/share/applications/micro-downloader.desktop'
    desk.parent.mkdir(parents=True,exist_ok=True)
    desk.write_text(DESKTOP,encoding='utf-8')
    icon = stage/'usr/share/icons/hicolor/256x256/apps/micro-downloader.png'
    icon.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'micro_downloader/assets/logo.png', icon)
    return stage


def total_bytes(stage):
    return sum(p.stat().st_size for p in Path(stage).rglob('*') if p.is_file())


def make_deb(stage, out, version):
    if not shutil.which('dpkg-deb'):
        print('Skipping .deb: dpkg-deb unavailable')
        return
    control = stage/'DEBIAN'
    control.mkdir(exist_ok=True)
    (control/'control').write_text(f'''Package: micro-downloader
Version: {version}
Section: net
Priority: optional
Architecture: amd64
Maintainer: kzlca (Micro Downloader project) <noreply@users.noreply.github.com>
Depends: aria2, curl
Description: Qt download manager with safe sparse-file recovery
 Micro Downloader stores original URLs, supports bandwidth management,
 and verifies missing byte ranges before repairing partial downloads.
''')
    subprocess.run(['dpkg-deb','--build','--root-owner-group','-Zxz',str(stage),str(out)],check=True)
    shutil.rmtree(control)
    print('Created',out)


def make_arch(stage, out, version):
    if not shutil.which('zstd'):
        print('Skipping Arch package: zstd unavailable')
        return
    text = f'''pkgname = micro-downloader
pkgbase = micro-downloader
pkgver = {version}-1
pkgdesc = Qt download manager with safe sparse-file recovery
url = https://github.com/kzlca/MicroDownloader
builddate = {int(time.time())}
packager = Micro Downloader Contributors
size = {total_bytes(stage)}
arch = x86_64
license = MIT
depend = aria2
depend = curl
optdepend = 7zip: test RAR and other archives
'''.encode('utf-8')
    proc = subprocess.Popen(['zstd','-q','-18','-T2','-o',str(out)],stdin=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=proc.stdin,mode='w|') as tar:
            meta = tarfile.TarInfo('.PKGINFO')
            meta.size = len(text)
            meta.mode = 0o644
            tar.addfile(meta, io.BytesIO(text))
            for relative in ('opt','usr'):
                tar.add(stage/relative,arcname=relative)
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError('zstd packaging failed')
    print('Created',out)


def make_rpm(stage, release, version):
    if not shutil.which('rpmbuild'):
        print('Skipping .rpm: rpmbuild unavailable')
        return
    with tempfile.TemporaryDirectory(prefix='micro-rpmbuild-') as tmp:
        top = Path(tmp)
        for folder in ('BUILD','BUILDROOT','RPMS','SOURCES','SPECS','SRPMS'):
            (top/folder).mkdir()
        spec = top/'SPECS/micro-downloader.spec'
        # Package from the staged (not installed) image and preserve symlinks.
        spec.write_text(f'''Name: micro-downloader
Version: {version}
Release: 1
Summary: Download manager with verified sparse-file recovery
License: MIT
URL: https://github.com/kzlca/MicroDownloader
BuildArch: x86_64
AutoReqProv: no
Requires: aria2
Requires: curl

%description
Micro Downloader stores original download URLs, manages downloads, and
repairs missing byte ranges after verifying existing data.

%prep

%build

%install
mkdir -p %{{buildroot}}
cp -a "{stage / 'opt'}" %{{buildroot}}/
cp -a "{stage / 'usr'}" %{{buildroot}}/

%files
/opt/micro-downloader
/usr/share/applications/micro-downloader.desktop
/usr/share/icons/hicolor/256x256/apps/micro-downloader.png
''',encoding='utf-8')
        subprocess.run(['rpmbuild','-bb','--define',f'_topdir {top}',str(spec)],check=True)
        rpms=list((top/'RPMS').rglob('*.rpm'))
        if len(rpms)!=1:
            raise RuntimeError(f'Expected 1 RPM, got {rpms}')
        out=release/f'MicroDownloader-{version}-linux-x64.rpm'
        shutil.copy2(rpms[0],out)
        print('Created',out)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--version',default='0.5.0')
    parser.add_argument('--dist',type=Path,default=ROOT/'dist/MicroDownloader')
    args=parser.parse_args()
    version=args.version.lstrip('v')
    if platform.system()!='Linux' or platform.machine().lower() not in ('x86_64','amd64'):
        raise SystemExit('Linux x86_64 native package builder only')
    release=ROOT/'release'
    release.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='micro-package-') as temp:
        stage=stage_payload(Path(temp)/'root',args.dist)
        make_deb(stage,release/f'MicroDownloader-{version}-linux-x64.deb',version)
        make_arch(stage,release/f'MicroDownloader-{version}-linux-x64.pkg.tar.zst',version)
        make_rpm(stage,release,version)


if __name__=='__main__':
    main()
