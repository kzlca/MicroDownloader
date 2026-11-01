#!/usr/bin/env python3
"""Real Qt regression checks: recover button, shortcut, resizing and migration UI."""
import os
import sys
import tempfile
from pathlib import Path

# Running by filename (`python scripts/smoke_ui.py`) otherwise places
# scripts/ rather than the repository root on sys.path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if os.name != 'nt':
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QContextMenuEvent
from micro_downloader import ui


def main():
    with tempfile.TemporaryDirectory(prefix='micro-downloader-ui-') as temp:
        os.environ['MICRO_DOWNLOADER_DATA_DIR'] = temp
        # Store.BASE is resolved on import: force a fresh dedicated store for this test.
        ui.Store = lambda: __import__('micro_downloader.store', fromlist=['Store']).Store(temp)
        app = QApplication([])
        window = ui.MainWindow()
        window.show()
        app.processEvents()

        seen = []
        original_dialog = ui.RecoveryDialog

        class InterceptDialog(QDialog):
            """Use an actual Qt widget so translate_tree tests the real dialog contract.

            A plain Python mock lacks QWidget methods like setLayoutDirection,
            which caused CI to fail before checking the Recover button.
            """
            def __init__(self, path='', url='', parent=None):
                super().__init__(parent)
                assert isinstance(path, str), f'Recovery path must be str, not {type(path).__name__}'
                seen.append((path, url))

            def exec(self):
                return QDialog.Rejected

        try:
            ui.RecoveryDialog = InterceptDialog
            window.recover_btn.click()
            assert seen == [('', '')], seen
            actions = [a for a in window.actions() if a.text() == 'Recover file']
            assert len(actions) == 1
            actions[0].trigger()
            assert len(seen) == 2 and seen[1] == ('', ''), seen
            window.resize(850, 640)
            app.processEvents()
            assert window.transfer_splitter.orientation() == Qt.Vertical
            assert window.sidebar.width() == 62
            assert window.language_button.isVisible() and not window.language_combo.isVisible()
            window.resize(1250, 650)
            app.processEvents()
            assert window.speed_chart.isVisible(), 'Speed history must remain visible at 650px'
            window.resize(1250, 480)
            app.processEvents()
            assert not window.speed_chart.isVisible(), 'Speed history must hide at 480px'
            assert window.sidebar_scroll.verticalScrollBar().maximum() > 0, 'Short sidebar must scroll instead of clipping'
            window.resize(1250, 800)
            app.processEvents()
            assert window.transfer_splitter.orientation() == Qt.Horizontal
            assert window.sidebar.width() == 205
            idx = window.language_combo.findData('fa')
            window.language_combo.setCurrentIndex(idx)
            app.processEvents()
            assert window.layoutDirection() == Qt.RightToLeft
            assert window.nav['all'].text() == 'همه انتقال‌ها'
            assert window.detail_url.layoutDirection() == Qt.LeftToRight
            assert window.sidebar.width() == 240
            assert window.detail_path.layoutDirection() == Qt.LeftToRight
            window.language_combo.setCurrentIndex(window.language_combo.findData('tr'))
            app.processEvents()
            assert window.layoutDirection() == Qt.LeftToRight
            assert window.nav['all'].text() == 'Tüm aktarımlar'
            window.language_combo.setCurrentIndex(window.language_combo.findData('en'))
            app.processEvents()
            assert window.nav['all'].text() == 'All transfers'
            assert window.sidebar.width() == 205

            # Actual transfer-card regression: visible actions and consistent
            # context menus on the selectable-looking filename label.
            testfile = Path(temp) / 'existing-part.rar'
            testfile.write_bytes(b'demo' * 1024)
            testurl = 'https://example.org/existing-part.rar'
            jid = window.store.add_job('download', testfile, testurl, status='paused')
            window.refresh()
            card = window._row_widgets[jid]
            assert set(card.buttons) == {'start','pause','verify','test','folder','copy','remove'}
            assert card.name.textInteractionFlags() == Qt.NoTextInteraction
            assert card.buttons['start'].isEnabled()
            assert not card.buttons['pause'].isEnabled()
            assert not card.buttons['verify'].isEnabled()
            card.buttons['copy'].click()
            assert QApplication.clipboard().text() == testurl
            seen_context = []
            original_menu = window.task_menu
            window.task_menu = lambda task, point: seen_context.append(task)
            try:
                QEventContext = QContextMenuEvent(
                    QContextMenuEvent.Mouse, QPoint(2, 2), QPoint(2, 2))
                QApplication.sendEvent(card.name, QEventContext)
                assert seen_context == [jid], seen_context
            finally:
                window.task_menu = original_menu
            # Standalone transfer card tests height-driven wrapping at narrow widths.
            wrapped = ui.TransferRow(window.store.get(jid))
            # Start wide and shrink after the layout has been constructed.
            # This catches minimum-size feedback that previously prevented a
            # card from shrinking and reflowing its action buttons.
            wrapped.resize(820, 400)
            wrapped.show()
            app.processEvents()
            assert wrapped._columns == 4, (wrapped.width(), wrapped._columns)
            wrapped.resize(300, 400)
            app.processEvents()
            assert wrapped.width() < 330, (wrapped.width(), wrapped.minimumSizeHint().width())
            assert wrapped._columns == 1, (wrapped.width(), wrapped._columns)
            assert wrapped._height >= 300
            wrapped.close()
        finally:
            ui.RecoveryDialog = original_dialog
            window.close()
            app.processEvents()
    print('PASS: Recover button, shortcuts, task-card actions/context, adaptive wrapping, RTL and compact navigation')


if __name__ == '__main__':
    main()
