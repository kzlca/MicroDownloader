"""Static and lightweight real-package checks without Qt or actual PyInstaller."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.package_linux import stage_payload, make_deb, make_arch, DESKTOP

ROOT = Path(__file__).resolve().parent.parent


class NativeInstallerTests(unittest.TestCase):
    def test_installer_sources_and_desktop_metadata(self):
        iss = (ROOT/'installer/MicroDownloader.iss').read_text(encoding='utf-8')
        self.assertIn('WizardStyle=modern dynamic',iss)
        self.assertIn('SetupIconFile=',iss)
        self.assertIn('PrivilegesRequired=lowest',iss)
        self.assertIn('CloseApplications=yes',iss)
        self.assertIn('Name: "desktopicon"',iss)
        self.assertIn('Icon=micro-downloader',DESKTOP)
        self.assertIn('Exec=/opt/micro-downloader/MicroDownloader',DESKTOP)

    def test_stage_does_not_include_user_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            dist=base/'dist'
            dist.mkdir()
            binary=dist/'MicroDownloader'
            binary.write_bytes(b'fake-app-executable')
            staged=stage_payload(base/'package',dist)
            self.assertTrue((staged/'opt/micro-downloader/MicroDownloader').is_file())
            self.assertTrue((staged/'usr/share/applications/micro-downloader.desktop').is_file())
            self.assertTrue((staged/'usr/share/icons/hicolor/256x256/apps/micro-downloader.png').is_file())
            self.assertFalse((staged/'opt/micro-downloader/.venv').exists())
            self.assertFalse((staged/'opt/micro-downloader/micro-downloader.db').exists())
            deb=base/'test.deb'
            make_deb(staged,deb,'0.5.0')
            if deb.exists():
                info=subprocess.check_output(['dpkg-deb','--field',str(deb),'Package'],text=True).strip()
                self.assertEqual(info,'micro-downloader')
            arch=base/'test.pkg.tar.zst'
            make_arch(staged,arch,'0.5.0')
            if arch.exists():
                output=subprocess.check_output(['zstd','-dc',str(arch)])
                self.assertIn(b'.PKGINFO',output[:1024])
                self.assertIn(b'pkgname = micro-downloader',output[:2048])


if __name__=='__main__':
    unittest.main()
