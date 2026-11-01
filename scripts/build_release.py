#!/usr/bin/env python3
"""Build minimal native packages. Run on target OS; PyInstaller is not cross-platform.

Dependencies: requirements-build.txt (only PySide6-Essentials + PyInstaller).
Bundling aria2c.exe is supported on Windows with MICRO_DOWNLOADER_ARIA2_BIN=/path/aria2c.exe.
On Linux, use distribution-provided aria2 and curl instead of copying incompatible
shared-library executables from the build host. This keeps the release smaller.
"""
import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_pyinstaller(mode, package_tools=True):
    cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
           '--windowed', f'--{mode}', '--name', 'MicroDownloader',
           '--noupx',
           '--add-data', f'{ROOT / "micro_downloader" / "assets"}{os.pathsep}micro_downloader/assets',
           # Unused modules are not in PySide6-Essentials, but protect against
           # a polluted build environment accidentally collecting them.
           '--exclude-module', 'PySide6.QtWebEngineWidgets',
           '--exclude-module', 'PySide6.QtWebEngineCore',
           '--exclude-module', 'PySide6.QtPdf',
           '--exclude-module', 'PySide6.QtPdfWidgets',
           '--exclude-module', 'PySide6.QtQml',
           '--exclude-module', 'PySide6.QtQuick',
           '--exclude-module', 'PySide6.QtMultimedia',
           '--exclude-module', 'PySide6.Qt3DCore',
           '--exclude-module', 'tkinter',
           '--distpath', str(ROOT / 'dist'), '--workpath', str(ROOT / 'build'),
           '--specpath', str(ROOT / 'build')]
    if os.name == 'nt':
        cmd += ['--icon', str(ROOT / 'micro_downloader' / 'assets' / 'logo.ico')]
    if package_tools and os.name == 'nt':
        binary = os.environ.get('MICRO_DOWNLOADER_ARIA2_BIN', '').strip()
        if not binary or not Path(binary).is_file():
            raise SystemExit('Windows releases need a real aria2c.exe. Set MICRO_DOWNLOADER_ARIA2_BIN to its full path. '
                             'Do not use Chocolatey\\bin shim executables.')
        cmd += ['--add-binary', f'{Path(binary).resolve()}{os.pathsep}bin']
        # Optional. For leanest releases, keep 7z external; adding the 7-Zip
        # standalone .exe/.dll pair is supported via an opt-in environment var.
        seven = os.environ.get('MICRO_DOWNLOADER_7ZIP_DIR', '').strip()
        if seven:
            d = Path(seven)
            for name in ('7z.exe','7z.dll'):
                f = d / name
                if not f.is_file():
                    raise SystemExit(f'Cannot bundle 7-Zip: missing {f}')
                cmd += ['--add-binary', f'{f.resolve()}{os.pathsep}bin']
    cmd.append(str(ROOT / 'run.py'))
    print('Building',mode, 'for',sys.platform, flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def package_onedir(version, platform_name):
    dist = ROOT / 'dist' / 'MicroDownloader'
    if not dist.is_dir():
        raise FileNotFoundError(f'PyInstaller did not create {dist}')
    release = ROOT / 'release'
    release.mkdir(exist_ok=True)
    base = f'MicroDownloader-{version}-{platform_name}-portable'
    if os.name == 'nt':
        result = release / (base + '.zip')
        with zipfile.ZipFile(result, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for f in sorted(dist.rglob('*')):
                if f.is_file():
                    z.write(f, Path('MicroDownloader') / f.relative_to(dist))
    else:
        result = release / (base + '.tar.gz')
        with tarfile.open(result, 'w:gz', compresslevel=9) as tar:
            tar.add(dist, arcname='MicroDownloader')
    print('Portable release:',result, result.stat().st_size // (1024*1024),'MiB', flush=True)


def package_onefile(version, platform_name):
    suffix = '.exe' if os.name == 'nt' else ''
    binary = ROOT / 'dist' / ('MicroDownloader'+suffix)
    if not binary.is_file():
        raise FileNotFoundError(f'PyInstaller did not create {binary}')
    out = ROOT / 'release' / (f'MicroDownloader-{version}-{platform_name}'+suffix)
    out.parent.mkdir(exist_ok=True)
    shutil.copy2(binary, out)
    if os.name != 'nt':
        out.chmod(out.stat().st_mode | 0o111)
    print('Single-file release:',out, out.stat().st_size//(1024*1024),'MiB', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['installer','onedir','onefile','both'],default='installer')
    parser.add_argument('--version', default='0.5.0')
    parser.add_argument('--system-tools',action='store_true',
                        help='Do not bundle aria2c on Windows (requires aria2 to be installed there).')
    args = parser.parse_args()
    platform_name = ('windows' if os.name=='nt' else 'linux') + '-' + ('arm64' if platform.machine().lower() in ('arm64','aarch64') else 'x64')
    if args.mode == 'installer':
        run_pyinstaller('onedir', not args.system_tools)
        if os.name == 'nt':
            compiler = os.environ.get('MICRO_DOWNLOADER_ISCC', '') or shutil.which('ISCC.exe') or shutil.which('ISCC')
            if not compiler:
                candidates = [
                    Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Inno Setup 6' / 'ISCC.exe',
                    Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Inno Setup 6' / 'ISCC.exe',
                ]
                compiler = next((str(c) for c in candidates if c.is_file()), '')
            if not compiler:
                raise SystemExit('Inno Setup compiler ISCC.exe missing. Install Inno Setup 6.6 or newer.')
            version = args.version.lstrip('v')
            if not re.fullmatch(r'\d+\.\d+\.\d+', version):
                raise SystemExit('Windows installer needs a numeric version such as 0.5.0')
            (ROOT / 'installer' / 'version.iss').write_text(
                f'#define AppVersion "{version}"\n', encoding='utf-8')
            subprocess.run([str(compiler), str(ROOT / 'installer' / 'MicroDownloader.iss')], cwd=ROOT, check=True)
        else:
            subprocess.run([sys.executable, str(ROOT / 'scripts' / 'package_linux.py'),
                            '--version', args.version], cwd=ROOT, check=True)
        return
    # onedir archive is more convenient for immediate start, and usually
    # compressed smaller than shipping an uncompressed distribution folder.
    if args.mode in ('onedir','both'):
        run_pyinstaller('onedir', not args.system_tools)
        package_onedir(args.version,platform_name)
    if args.mode in ('onefile','both'):
        run_pyinstaller('onefile', not args.system_tools)
        package_onefile(args.version,platform_name)


if __name__ == '__main__':
    main()
