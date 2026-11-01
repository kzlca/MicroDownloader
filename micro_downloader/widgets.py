"""Reusable Qt widgets and dialogs."""
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PySide6.QtCore import Qt, QSize, Signal, QEvent, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QSpinBox, QPlainTextEdit, QProgressBar, QComboBox, QCheckBox, QSizePolicy, QGridLayout, QLayout,
)
from .sparse import format_bytes
from .i18n import translate

GREEN = QColor('#25be90')
YELLOW = QColor('#f5b93b')


def friendly_name(url):
    path = unquote(urlsplit(url).path)
    return Path(path).name or 'download.bin'


def color_status(status):
    return {
        'active':'#56a9ff','waiting':'#e8bb62','queued':'#9aacc0',
        'paused':'#f5b93b','complete':'#26ce99','recovered':'#26ce99',
        'verified':'#64c8a7','failed':'#f07878','checking':'#69b3fb',
        'recovering':'#56a9ff','cancelled':'#8391a3'
    }.get(status, '#9aacc0')


class AllocationBar(QWidget):
    """Explicit logical byte map, green allocated and yellow sparse gaps."""
    def __init__(self, parent=None, height=19):
        super().__init__(parent)
        self.total = 0
        self.holes = []
        self.setFixedHeight(height)
        self.setMinimumWidth(50)

    def set_data(self, size, holes):
        self.total, self.holes = size, holes
        missing = sum(b-a for a,b in holes)
        self.setToolTip(f'Allocated: {format_bytes(size-missing)} | Sparse / missing: {format_bytes(missing)}\n'
                        'A filesystem hole does not guarantee nearby data is valid.')
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(0,2,-1,-2)
        outline = QPainterPath()
        outline.addRoundedRect(rect, 7, 7)
        p.setClipPath(outline)
        p.fillRect(rect, QColor('#253348'))
        if not self.total:
            return
        p.fillRect(rect, GREEN)
        for a,b in self.holes:
            x = rect.x() + rect.width()*a/self.total
            w = rect.width()*(b-a)/self.total
            p.fillRect(int(x),rect.y(),max(1,int(w+0.5)),rect.height(),YELLOW)
        p.end()


class TransferRow(QFrame):
    """A full-width interactive transfer card with always-visible actions.

    All surfaces, including the filename, send context menus to the parent
    transfer view; user-selectable QLabel text would otherwise show Copy / Select All.
    """
    clicked = Signal()
    context_requested = Signal(object)  # global QPoint
    action_requested = Signal(str)
    height_changed = Signal(int)

    ACTIONS = ('start', 'pause', 'verify', 'test', 'folder', 'copy', 'remove')
    LABELS = {
        'start': 'Start / Resume', 'pause': 'Pause', 'verify': 'Verify ranges',
        'test': 'Test archive', 'folder': 'Open folder',
        'copy': 'Copy URL', 'remove': 'Remove task',
    }

    def __init__(self, job, parent=None):
        super().__init__(parent)
        self.job_id = job['id']
        self._full_name = ''
        self._columns = 0
        self._height = 0
        self.setObjectName('transferRow')
        self.setStyleSheet('''QFrame#transferRow {background:#151f2c; border:1px solid #2a384a; border-radius:12px;}
             QFrame#transferRow:hover {background:#1d2b3b; border:1px solid #3b526c;}
             QFrame#transferRow QPushButton { padding: 6px 6px; border-radius:7px; }
             QFrame#transferRow QPushButton#danger:hover { background:#62303a; border-color:#ba5f6a; }''')
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(7)
        top = QHBoxLayout()
        self.name = QLabel()
        self.name.setStyleSheet('font-weight:700;font-size:13px;border:0;background:transparent;')
        self.name.setTextInteractionFlags(Qt.NoTextInteraction)
        self.name.setLayoutDirection(Qt.LeftToRight)
        self.name.setMinimumWidth(0)
        self.name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        top.addWidget(self.name, 1)
        self.state = QLabel()
        self.state.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.state.setStyleSheet('font-size:11px;font-weight:700;border:0;background:transparent;')
        top.addWidget(self.state)
        v.addLayout(top)
        self.bar = QProgressBar()
        self.bar.setFixedHeight(8)
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        v.addWidget(self.bar)
        self.map = AllocationBar(height=10)
        v.addWidget(self.map)
        self.info = QLabel()
        self.info.setStyleSheet('color:#8799b0;font-size:11px;border:0;background:transparent;')
        self.info.setTextInteractionFlags(Qt.NoTextInteraction)
        v.addWidget(self.info)
        self.action_grid = QGridLayout()
        self.action_grid.setHorizontalSpacing(6)
        self.action_grid.setVerticalSpacing(5)
        self.buttons = {}
        for key in self.ACTIONS:
            btn = QPushButton(self.LABELS[key])
            btn.setCursor(Qt.PointingHandCursor)
            btn.setObjectName('danger' if key == 'remove' else 'cardAction')
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setFixedHeight(31)
            btn.clicked.connect(lambda checked=False, action=key: self.action_requested.emit(action))
            self.buttons[key] = btn
        v.addLayout(self.action_grid)
        self.setMinimumWidth(0)
        self.set_job(job)
        # Qt child widgets consume ContextMenu events. Install one handler on
        # the entire card tree to ensure the task menu wins everywhere.
        for child in [self, self.name, self.state, self.bar, self.map, self.info, *self.buttons.values()]:
            child.installEventFilter(self)
        self._reflow_actions(3)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.ContextMenu:
            self.context_requested.emit(event.globalPos())
            return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = max(self.width(), 260)
        cols = 4 if width >= 770 else 3 if width >= 560 else 2 if width >= 330 else 1
        self._reflow_actions(cols)
        self._update_name()

    def _reflow_actions(self, cols):
        if cols == self._columns:
            return
        self._columns = cols
        for button in self.buttons.values():
            self.action_grid.removeWidget(button)
        for index, key in enumerate(self.ACTIONS):
            self.action_grid.addWidget(self.buttons[key], index // cols, index % cols)
        rows = (len(self.ACTIONS) + cols - 1) // cols
        # Explicit card height prevents QListWidget from clipping wrapped actions.
        new_height = 87 + rows * 31 + (rows - 1) * 5 + 22
        if new_height != self._height:
            self._height = new_height
            self.setMinimumHeight(new_height)
            self.height_changed.emit(new_height)

    def _update_name(self):
        if self._full_name:
            available = max(70, self.width() - 172)
            self.name.setText(self.name.fontMetrics().elidedText(self._full_name, Qt.ElideMiddle, available))

    def set_job(self, job, extents=None, lang='en'):
        self._full_name = Path(job['path']).name
        self._update_name()
        self.name.setToolTip(job['path'])
        self.name.setStyleSheet(f"font-weight:700;font-size:{15 if lang == 'fa' else 13}px;border:0;background:transparent;")
        state = job['status']
        self.state.setText(translate(state.upper(), lang))
        self.state.setStyleSheet(f'font-size:10px;font-weight:700;color:{color_status(state)};border:0;background:transparent;')
        done, total = int(job['done']), int(job['total'])
        self.bar.setValue(min(1000, int(done*1000/total)) if total else 0)
        if job['kind'] == 'recovery':
            self.bar.hide()
            self.map.show()
            if extents:
                self.map.set_data(extents['size'], extents['holes'])
                self.info.setText(f"{translate('Allocated',lang)} {format_bytes(extents['allocated'])}  ·  {translate('Missing',lang)} {format_bytes(extents['missing'])}")
            else:
                self.map.set_data(0, [])
                self.info.setText(f"{translate('Sparse recovery',lang)}  ·  {state}")
        else:
            self.bar.show()
            self.map.hide()
            label = f"{format_bytes(done)} / {format_bytes(total) if total else 'unknown'}"
            if state == 'active':
                label += f"   ·   {format_bytes(job['speed'])}/s"
                if total and job['speed'] and total > done:
                    eta = int((total-done)/job['speed'])
                    label += f"   ·   ETA {eta//3600:d}h {(eta%3600)//60:02d}m"
            self.info.setText(label)
        for key, btn in self.buttons.items():
            label = ('Repair missing bytes' if job['url'] else 'Add original URL') if key == 'start' and job['kind'] == 'recovery' else ('Stop recovery' if key == 'pause' and job['kind'] == 'recovery' else self.LABELS[key])
            full_label = translate(label, lang)
            btn.setText(full_label)
            btn.setToolTip(full_label)
            if key == 'start':
                enable = state not in ('active','waiting','complete','recovering','checking','recovered')
            elif key == 'pause':
                enable = state in ('active','waiting','recovering','checking')
            elif key == 'verify':
                enable = job['kind'] == 'recovery' and bool(job['url']) and state not in ('checking','recovering')
            elif key == 'test':
                enable = state not in ('active','waiting','recovering','checking')
            elif key == 'copy':
                enable = bool(job['url'])
            else:
                enable = True
            btn.setEnabled(enable)


class DownloadDialog(QDialog):
    def __init__(self, directory, connections, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add downloads')
        self.resize(600, 370)
        outer = QVBoxLayout(self)
        outer.setSpacing(12)
        intro = QLabel('Paste direct links — one URL per line')
        intro.setObjectName('heading')
        outer.addWidget(intro)
        self.urls = QPlainTextEdit()
        self.urls.setLayoutDirection(Qt.LeftToRight)
        self.urls.setPlaceholderText('https://example.org/archive.part01.rar\nhttps://example.org/archive.part02.rar')
        outer.addWidget(self.urls)
        line = QHBoxLayout()
        self.folder = QLineEdit(str(directory))
        browse = QPushButton('Browse…')
        browse.clicked.connect(self.choose_folder)
        line.addWidget(self.folder, 1)
        line.addWidget(browse)
        outer.addWidget(QLabel('Download directory'))
        outer.addLayout(line)
        row = QHBoxLayout()
        row.addWidget(QLabel('Connections per file'))
        self.connections = QSpinBox()
        self.connections.setRange(1, 16)
        self.connections.setValue(connections)
        row.addWidget(self.connections)
        row.addStretch()
        outer.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText('Add to queue')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Choose download directory', self.folder.text())
        if path:
            self.folder.setText(path)


class RecoveryDialog(QDialog):
    def __init__(self, path='', url='', parent=None):
        super().__init__(parent)
        self.setWindowTitle('Recover an existing download')
        self.setMinimumWidth(380)
        self.resize(620, 420)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        title = QLabel('Attach an interrupted file')
        title.setObjectName('heading')
        layout.addWidget(title)
        subtitle = QLabel('Micro Downloader will map allocated (green) and missing (yellow) blocks.\n'
                          'It never writes during the initial analysis.')
        subtitle.setObjectName('dim')
        layout.addWidget(subtitle)
        file_row = QHBoxLayout()
        self.filepath = QLineEdit(str(path) if path and not isinstance(path, bool) else "")
        file_row.addWidget(self.filepath, 1)
        select = QPushButton('Choose file…')
        select.clicked.connect(self.pick)
        file_row.addWidget(select)
        layout.addWidget(QLabel('Existing partial file'))
        layout.addLayout(file_row)
        layout.addWidget(QLabel('Original direct HTTP/HTTPS URL (can be added later)'))
        self.url = QLineEdit(str(url) if url else "")
        self.url.setPlaceholderText('https://server.example/large-file.part12.rar')
        layout.addWidget(self.url)
        hint = QLabel('For recovery, the URL must return the exact original file and support HTTP byte ranges.\n'
                      'A sparse file can contain corrupted allocated bytes; verify the final archive/checksum.')
        hint.setWordWrap(True)
        hint.setObjectName('dim')
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText('Add to Recovery')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def pick(self):
        selected,_ = QFileDialog.getOpenFileName(self, 'Select partial file',
                                               str(Path(self.filepath.text() or str(Path.home())).parent))
        if selected:
            self.filepath.setText(selected)


class SettingsDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Micro Downloader settings')
        self.setMinimumWidth(550)
        layout = QVBoxLayout(self)
        title = QLabel('Download preferences')
        title.setObjectName('heading')
        layout.addWidget(title)
        form = QFormLayout()
        self.folder = QLineEdit(store.settings('directory', str(Path.home()/'Downloads')))
        line = QHBoxLayout()
        line.addWidget(self.folder, 1)
        choose = QPushButton('Browse')
        choose.clicked.connect(self.pick)
        line.addWidget(choose)
        form.addRow('Default directory', line)
        self.parallel = QSpinBox()
        self.parallel.setRange(1, 12)
        self.parallel.setValue(store.settings('parallel', 3))
        form.addRow('Simultaneous downloads', self.parallel)
        self.connections = QSpinBox()
        self.connections.setRange(1, 16)
        self.connections.setValue(store.settings('connections', 8))
        form.addRow('Connections per file', self.connections)
        self.speed = QSpinBox()
        self.speed.setRange(0, 1024000)
        self.speed.setSuffix(' KiB/s (0 = unlimited)')
        self.speed.setValue(store.settings('speed_kib', 0))
        form.addRow('Total speed limit', self.speed)
        self.proxy = QLineEdit(store.settings('proxy', ''))
        self.proxy.setPlaceholderText('Optional: http://127.0.0.1:10809')
        form.addRow('Network proxy', self.proxy)
        self.retries = QSpinBox()
        self.retries.setRange(1, 10)
        self.retries.setValue(store.settings('retries', 4))
        form.addRow('Recovery retries per chunk', self.retries)
        self.chunk = QSpinBox()
        self.chunk.setRange(1, 32)
        self.chunk.setValue(store.settings('chunk_mib', 8))
        self.chunk.setSuffix(' MiB')
        form.addRow('Recovery chunk size', self.chunk)
        self.margin = QSpinBox()
        self.margin.setRange(1, 8)
        self.margin.setValue(store.settings('margin_mib', 1))
        self.margin.setSuffix(' MiB')
        form.addRow('Recovery edge overlap', self.margin)
        layout.addLayout(form)
        info = QLabel('The speed cap applies to all aria2 downloads together. The recovery curl worker has its own cap.\n'
                      'Recovery checks current settings when a new operation begins.')
        info.setObjectName('dim')
        info.setWordWrap(True)
        layout.addWidget(info)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def pick(self):
        directory = QFileDialog.getExistingDirectory(self, 'Choose folder', self.folder.text())
        if directory:
            self.folder.setText(directory)

    def persist(self, store):
        for key, value in {
                'directory': self.folder.text(), 'parallel': self.parallel.value(),
                'connections': self.connections.value(), 'speed_kib': self.speed.value(),
                'proxy': self.proxy.text().strip(), 'retries': self.retries.value(),
                'chunk_mib': self.chunk.value(), 'margin_mib': self.margin.value()}.items():
            store.set_setting(key, value)
