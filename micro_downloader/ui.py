"""Micro Downloader Qt desktop UI: persistent queue, controls, sparse map and recovery."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import Qt, QTimer, QUrl, QSize, QThread, Signal, QEvent
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence, QIcon, QPixmap, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QListWidget, QListWidgetItem,
    QSplitter, QScrollArea, QPlainTextEdit, QMessageBox, QFileDialog,
    QProgressBar, QMenu, QDialog, QBoxLayout, QGridLayout, QSizePolicy, QComboBox, QInputDialog, QLayout,
)

from .engine import AriaController, AriaError
from .store import Store
from .sparse import inspect, format_bytes
from .recovery import RecoveryWorker
from .widgets import (AllocationBar, TransferRow, DownloadDialog, RecoveryDialog,
                      SettingsDialog, friendly_name, color_status)
from .styles import DARK
from .tools import find_tool
from .archive_check import volume_info, summarize_7z
from .speed_chart import SpeedChart
from .i18n import CATALOG, translate, is_rtl, translate_tree
from .typography import apply_ui_font


class ArchiveTest(QThread):
    result = Signal(bool, str)

    def __init__(self, filepath, password=''):
        super().__init__()
        self.filepath = filepath
        self.password = password

    def run(self):
        exe = find_tool('7z') or find_tool('7zz')
        if not exe:
            self.result.emit(False, '7-Zip CLI not installed. Install 7-Zip or select a release bundling it.')
            return
        path = volume_info(self.filepath)['root']
        if not path.is_file():
            self.result.emit(False, f'Missing first archive volume: {path.name}')
            return
        try:
            # Credentials are never logged or saved; note the 7z CLI -p form
            # can briefly expose a supplied password in the OS process list.
            cmd = [exe, 't', '-y', str(path)]
            if self.password:
                cmd.insert(2, '-p' + self.password)
            p = subprocess.run(cmd, capture_output=True, text=True, errors='replace',
                               timeout=36000, stdin=subprocess.DEVNULL)
            success, summary = summarize_7z(path, p.stdout, p.stderr, p.returncode)
            self.result.emit(success, summary)
        except Exception as exc:
            self.result.emit(False, str(exc))



def stat_card(label, value, note=''):
    panel = QFrame()
    panel.setObjectName('stat')
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(15, 11, 15, 11)
    layout.setSpacing(4)
    l = QLabel(label); l.setObjectName('overline')
    v = QLabel(value); v.setObjectName('value')
    s = QLabel(note); s.setObjectName('dim')
    layout.addWidget(l); layout.addWidget(v); layout.addWidget(s)
    return panel, v, s


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Micro Downloader v0.5.1 — Download & Recovery')
        self.setWindowIcon(QIcon(str(Path(__file__).parent / 'assets' / 'logo.png')))
        self.setMinimumSize(640, 480)
        self.resize(1250, 790)
        self.store = Store()
        self.language = self.store.settings('language', 'en')
        if self.language not in CATALOG: self.language = 'en'
        self.aria = AriaController(self.store.home)
        self.aria_error = ''
        self.recovery_worker = None
        self.recovery_id = None
        self.archive_worker = None
        self.selected_id = None
        self.filter = 'all'
        self.cache = {}
        self._rendered_ids = []
        self._row_widgets = {}
        self._ready = False
        self.setup_ui()
        self.setup_shortcuts()
        try:
            self.aria.start(self.store.settings('parallel',3), self.store.settings('speed_kib',0))
        except AriaError as exc:
            self.aria_error = str(exc)
        self.restore_queue()
        self.refresh()
        self._ready = True
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1400)
        if self.aria_error:
            QTimer.singleShot(250, lambda: self.statusBar().showMessage('aria2 unavailable: ' + self.aria_error, 15000))

    def setup_ui(self):
        self.setStyleSheet(DARK)
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame(); sidebar.setObjectName('sidebar'); sidebar.setFixedWidth(205)
        self.sidebar = sidebar
        so = QVBoxLayout(sidebar); so.setContentsMargins(0, 0, 0, 0)
        self.sidebar_scroll = QScrollArea(sidebar)
        self.sidebar_scroll.setFrameShape(QFrame.NoFrame)
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.sidebar_content = QWidget(); self.sidebar_content.setObjectName('sidebarContent')
        sv = QVBoxLayout(self.sidebar_content)
        sv.setContentsMargins(12, 14, 12, 12); sv.setSpacing(7)
        # Keep the sidebar's natural height so QScrollArea scrolls rather than squeezing labels.
        sv.setSizeConstraint(QLayout.SetMinimumSize)
        brand_row = QHBoxLayout()
        self.logo = QLabel()
        self.logo_pix = QPixmap(str(Path(__file__).parent / 'assets' / 'logo.png'))
        self.update_logo_size(compact=False)
        brand_row.addWidget(self.logo)
        self.brand = QLabel('MICRO'); self.brand.setObjectName('brand')
        brand_row.addWidget(self.brand); brand_row.addStretch()
        sv.addLayout(brand_row)
        self.brand_tag = QLabel('DOWNLOADER  /  RECOVER'); self.brand_tag.setObjectName('overline'); sv.addWidget(self.brand_tag)
        sv.addSpacing(9)
        self.nav = {}
        self.nav_names = {}
        self.nav_symbols = {"all":"◫", "active":"↓", "paused":"Ⅱ", "complete":"✓", "recovery":"▤", "failed":"!"}
        for name, key in [('All transfers', 'all'), ('Downloading', 'active'),
                          ('Paused & queued', 'paused'), ('Completed', 'complete'),
                          ('Recovery lab', 'recovery'), ('Failed', 'failed')]:
            btn = QPushButton(name); btn.setObjectName('nav'); btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=key: self.set_filter(k))
            btn.setToolTip(name)
            sv.addWidget(btn); self.nav[key] = btn; self.nav_names[key] = name
        self.nav['all'].setChecked(True)
        sv.addSpacing(12)
        line = QFrame(); line.setFrameShape(QFrame.HLine)
        line.setStyleSheet('color:#263143;'); sv.addWidget(line)
        exportbtn = QPushButton('⇧  Export URL library')
        self.exportbtn = exportbtn; exportbtn.setToolTip('Export URL library')
        exportbtn.clicked.connect(self.export_urls)
        sv.addWidget(exportbtn)
        sv.addSpacing(12)
        settings = QPushButton('⚙  Settings'); self.settingsbtn = settings
        settings.setToolTip('Settings'); settings.clicked.connect(self.open_settings)
        sv.addWidget(settings)
        self.language_label = QLabel('Language')
        self.language_label.setObjectName('dim')
        sv.addWidget(self.language_label)
        self.language_combo = QComboBox()
        for code, spec in CATALOG.items():
            self.language_combo.addItem(spec['name'], code)
        i = self.language_combo.findData(self.language)
        if i >= 0: self.language_combo.setCurrentIndex(i)
        self.language_combo.currentIndexChanged.connect(self.change_language)
        sv.addWidget(self.language_combo)
        self.language_button = QPushButton('🌐')
        self.language_button.setToolTip('Language')
        self.language_button.clicked.connect(self.show_language_menu)
        sv.addWidget(self.language_button)
        sv.addSpacing(8)
        about = QLabel('Local-first  ·  Private storage\nQt / aria2 / curl / SQLite')
        self.about_label = about
        about.setObjectName('dim'); about.setWordWrap(True)
        about.setStyleSheet('color:#758aa2;font-size:11px;')
        sv.addWidget(about)
        sv.addStretch(1)
        self.sidebar_scroll.setWidget(self.sidebar_content)
        so.addWidget(self.sidebar_scroll)
        root.addWidget(sidebar)

        main = QWidget()
        self.main_panel = main
        mv = QVBoxLayout(main)
        self.main_layout = mv
        mv.setContentsMargins(20, 17, 18, 16)
        mv.setSpacing(13)
        header = QBoxLayout(QBoxLayout.LeftToRight)
        self.header_layout = header
        heading = QVBoxLayout(); heading.setSpacing(3)
        big = QLabel('Transfer workspace'); big.setObjectName('heading')
        sub = QLabel('Download, organize, and recover interrupted files without losing progress.')
        sub.setObjectName('dim'); sub.setWordWrap(True)
        self.header_subtitle = sub
        heading.addWidget(big); heading.addWidget(sub)
        header.addLayout(heading); header.addStretch(1)
        plus = QPushButton('New download'); plus.setObjectName('primary'); plus.clicked.connect(self.add_download)
        rec = QPushButton('Recover file')
        # Qt clicked(bool) must not become the path argument of add_recovery.
        rec.clicked.connect(lambda _checked=False: self.add_recovery())
        self.new_btn, self.recover_btn = plus, rec
        self.header_actions = QHBoxLayout()
        self.header_actions.addWidget(rec); self.header_actions.addWidget(plus)
        header.addLayout(self.header_actions)
        mv.addLayout(header)
        self.stats_panel = QWidget()
        self.stats_grid = QGridLayout(self.stats_panel)
        self.stats_grid.setContentsMargins(0, 0, 0, 0)
        self.stats_grid.setSpacing(9)
        self.card_all, self.val_all, self.note_all = stat_card('Saved transfers', '0', 'URLs kept locally')
        self.card_active, self.val_active, self.note_active = stat_card('Active tasks', '0', 'Current session')
        self.card_speed, self.val_speed, self.note_speed = stat_card('Download speed', '0 B/s', 'Live transfer total')
        self.card_recovery, self.val_recovery, self.note_recovery = stat_card('Recoverable', '0', 'Sparse-file tasks')
        self.stat_cards = (self.card_all, self.card_active, self.card_speed, self.card_recovery)
        self.stat_notes = (self.note_all, self.note_active, self.note_speed, self.note_recovery)
        for index, item in enumerate(self.stat_cards):
            self.stats_grid.addWidget(item, 0, index)
        mv.addWidget(self.stats_panel)
        self.speed_chart_title = QLabel('Speed history')
        self.speed_chart_title.setObjectName('overline')
        self.speed_chart = SpeedChart()
        mv.addWidget(self.speed_chart_title)
        mv.addWidget(self.speed_chart)

        opts = QBoxLayout(QBoxLayout.LeftToRight); opts.setSpacing(9)
        self.options_layout = opts
        self.search = QLineEdit(); self.search.setPlaceholderText('Search filenames, URLs, or paths…')
        self.search.textChanged.connect(self.refresh)
        self.search.setClearButtonEnabled(True)
        opts.addWidget(self.search, 1)
        self.speed_group = QHBoxLayout()
        self.speed_group.addWidget(QLabel('Speed cap'))
        self.speed = QSpinBox(); self.speed.setRange(0, 1024000)
        self.speed.setValue(self.store.settings('speed_kib', 0))
        self.speed.setSuffix(' KiB/s'); self.speed.setSpecialValueText('Unlimited')
        self.speed.setToolTip('Total transfer speed cap. 0 means unlimited.')
        self.speed.valueChanged.connect(self.speed_changed)
        self.speed_group.addWidget(self.speed)
        opts.addLayout(self.speed_group)
        mv.addLayout(opts)
        batch = QBoxLayout(QBoxLayout.LeftToRight)
        self.batch_layout = batch
        batch.setSpacing(8)
        hint = QLabel('Transfers are restored from your local database when Micro Downloader starts.')
        hint.setObjectName('dim')
        hint.setStyleSheet('font-size:11px;color:#7c90a7;')
        self.batch_hint = hint
        batch.addWidget(hint, 1)
        pauseall = QPushButton('Pause all'); pauseall.clicked.connect(self.pause_all)
        resumeall = QPushButton('Resume all'); resumeall.clicked.connect(self.resume_all)
        self.batch_actions = QHBoxLayout()
        self.batch_actions.addWidget(pauseall); self.batch_actions.addWidget(resumeall)
        batch.addLayout(self.batch_actions)
        mv.addLayout(batch)
        splitter = QSplitter(Qt.Horizontal)
        self.transfer_splitter = splitter
        splitter.setChildrenCollapsible(False)
        self.queue = QListWidget()
        self.queue.setMinimumSize(260, 120)
        self.queue.setSpacing(7)
        self.queue.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue.customContextMenuRequested.connect(self.queue_menu)
        self.queue.currentItemChanged.connect(self.selected_changed)
        splitter.addWidget(self.queue)

        detail = QFrame(); detail.setObjectName('detail')
        self.detail_panel = detail
        dv = QVBoxLayout(detail)
        dv.setContentsMargins(18, 16, 14, 8)
        dv.setSpacing(10)
        head = QLabel('TRANSFER DETAILS'); head.setObjectName('overline'); dv.addWidget(head)
        self.detail_title = QLabel('Select a transfer')
        self.detail_title.setWordWrap(True)
        self.detail_title.setStyleSheet('font-size:15px;font-weight:800;')
        dv.addWidget(self.detail_title)
        self.detail_state = QLabel('Your download details will appear here.')
        self.detail_state.setObjectName('dim'); self.detail_state.setWordWrap(True)
        dv.addWidget(self.detail_state)
        dv.addSpacing(7)
        dv.addWidget(QLabel('Source URL'))
        self.detail_url = QLineEdit(); self.detail_url.setPlaceholderText('Paste an original URL here…')
        dv.addWidget(self.detail_url)
        urlbuttons = QBoxLayout(QBoxLayout.LeftToRight)
        saveurl = QPushButton('Save URL'); saveurl.clicked.connect(self.save_url)
        copyurl = QPushButton('Copy URL'); copyurl.clicked.connect(self.copy_url)
        urlbuttons.addWidget(saveurl); urlbuttons.addWidget(copyurl)
        dv.addLayout(urlbuttons)
        dv.addSpacing(9)
        self.detail_path = QLabel()
        self.detail_path.setWordWrap(True); self.detail_path.setObjectName('dim')
        dv.addWidget(self.detail_path)
        self.progress_text = QLabel('No selection')
        self.progress_text.setWordWrap(True)
        self.progress_text.setStyleSheet('font-size:12px;font-weight:700;')
        dv.addWidget(self.progress_text)
        self.detail_bar = QProgressBar(); self.detail_bar.setTextVisible(False)
        self.detail_bar.setFixedHeight(14)
        dv.addWidget(self.detail_bar)
        self.allocation = AllocationBar(height=23)
        dv.addWidget(self.allocation)
        legend = QHBoxLayout()
        legend_alloc = QLabel('Allocated'); legend_alloc.setStyleSheet('color:#25be90;font-weight:700;')
        legend_hole = QLabel('Missing'); legend_hole.setStyleSheet('color:#f5b93b;font-weight:700;')
        legend.addWidget(legend_alloc); legend.addWidget(legend_hole); legend.addStretch(1)
        self.legend_widget = QWidget(); self.legend_widget.setLayout(legend)
        dv.addWidget(self.legend_widget)
        self.alloc_stats = QLabel(''); self.alloc_stats.setObjectName('dim'); self.alloc_stats.setWordWrap(True)
        dv.addWidget(self.alloc_stats)
        actions = QBoxLayout(QBoxLayout.LeftToRight)
        self.run_btn = QPushButton('Start / Resume'); self.run_btn.setObjectName('primary')
        self.run_btn.clicked.connect(self.run_selected)
        self.pause_btn = QPushButton('Pause'); self.pause_btn.clicked.connect(self.pause_selected)
        actions.addWidget(self.run_btn, 1); actions.addWidget(self.pause_btn)
        dv.addLayout(actions)
        nextactions = QBoxLayout(QBoxLayout.LeftToRight)
        self.verify_btn = QPushButton('Verify ranges'); self.verify_btn.clicked.connect(self.verify_selected)
        self.test_btn = QPushButton('Test archive'); self.test_btn.clicked.connect(self.test_selected)
        nextactions.addWidget(self.verify_btn); nextactions.addWidget(self.test_btn)
        dv.addLayout(nextactions)
        otheractions = QBoxLayout(QBoxLayout.LeftToRight)
        folder = QPushButton('Open folder'); folder.clicked.connect(self.open_folder)
        delete = QPushButton('Remove task'); delete.clicked.connect(self.remove_selected)
        otheractions.addWidget(folder); otheractions.addWidget(delete)
        dv.addLayout(otheractions)
        dv.addSpacing(7)
        l = QLabel('ACTIVITY LOG'); l.setObjectName('overline'); dv.addWidget(l)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMinimumHeight(95)
        self.log.setMaximumHeight(220)
        self.log.setStyleSheet('font-family:monospace;font-size:11px;')
        dv.addWidget(self.log, 1)
        self.detail_action_layouts = (urlbuttons, actions, nextactions, otheractions)
        self._detail_stacked = None
        # A scrollable detail panel keeps all controls reachable at small heights.
        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.NoFrame)
        self.detail_scroll.setMinimumSize(270, 150)
        self.detail_scroll.setWidget(detail)
        self.detail_scroll.viewport().installEventFilter(self)
        splitter.addWidget(self.detail_scroll)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([610, 380])
        mv.addWidget(splitter, 1)
        root.addWidget(main, 1)
        self.statusBar().showMessage('Imported previous Velora transfers and URLs.' if self.store.migrated else 'Ready — locally stored transfer list')
        self._compact_layout = None
        self._narrow_layout = None
        self._short_layout = None
        self._tiny_layout = None
        self.update_responsive_layout()
        self.apply_language()

    def setup_shortcuts(self):
        for label, combo, slot in [
                ('New download', 'Ctrl+N', self.add_download),
                ('Recover file', 'Ctrl+R', self.add_recovery),
                ('Find', 'Ctrl+F', self.search.setFocus),
                ('Settings', 'Ctrl+,', self.open_settings)]:
            action = QAction(label, self); action.setShortcut(QKeySequence(combo))
            if label == 'Recover file':
                action.triggered.connect(lambda _checked=False: self.add_recovery())
            else:
                action.triggered.connect(slot)
            self.addAction(action)

    def eventFilter(self, watched, event):
        if (hasattr(self, 'detail_scroll') and watched is self.detail_scroll.viewport()
                and event.type() == QEvent.Resize):
            self.update_detail_actions()
        return super().eventFilter(watched, event)

    def update_detail_actions(self):
        if not hasattr(self, 'detail_action_layouts'):
            return
        stacked = self.detail_scroll.viewport().width() < 440
        if stacked != self._detail_stacked:
            for layout in self.detail_action_layouts:
                layout.setDirection(QBoxLayout.TopToBottom if stacked else QBoxLayout.LeftToRight)
            self._detail_stacked = stacked

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'sidebar') and hasattr(self, 'transfer_splitter'):
            self.update_responsive_layout()
            self.update_detail_actions()

    def update_responsive_layout(self):
        """Reflow navigation, cards, controls and panels; never clip action labels."""
        width, height = self.width(), self.height()
        compact = width < 1010
        narrow = width < 1160
        short = height < 690
        if compact != self._compact_layout:
            self.sidebar.setFixedWidth(62 if compact else (240 if self.language in ('tr','fa') else 205))
            self.brand.setVisible(not compact)
            self.logo.setAlignment(Qt.AlignCenter)
            self.update_logo_size(compact)
            self.brand.setAlignment(Qt.AlignCenter if compact else Qt.AlignLeft)
            self.brand_tag.setVisible(not compact)
            self.about_label.setVisible(not compact)
            self.exportbtn.setText('⇧' if compact else '⇧  ' + translate('Export URL library',self.language))
            self.settingsbtn.setText('⚙' if compact else '⚙  ' + translate('Settings',self.language))
            self.language_label.setVisible(not compact)
            self.language_combo.setVisible(not compact)
            self.language_button.setVisible(compact)
            for utility in (self.exportbtn, self.settingsbtn):
                utility.setStyleSheet('padding: 8px 0px;' if compact else '')
            for key, button in self.nav.items():
                button.setText(self.nav_symbols[key] if compact else translate(self.nav_names[key],self.language))
                button.setStyleSheet('text-align:center; padding: 10px 0px;' if compact else ('text-align:right; padding: 13px 14px;' if is_rtl(self.language) else ''))
            self._compact_layout = compact
        if narrow != self._narrow_layout:
            self.header_layout.setDirection(QBoxLayout.TopToBottom if narrow else QBoxLayout.LeftToRight)
            # The wide-mode stretch must not consume vertical space when the header stacks.
            self.header_layout.setStretch(1, 0 if narrow else 1)
            self.header_subtitle.setVisible(not narrow)
            self.transfer_splitter.setOrientation(Qt.Vertical if narrow else Qt.Horizontal)
            self.batch_hint.setVisible(not narrow)
            # Narrow windows use a 2x2 summary grid instead of squeezing four cards.
            for card in self.stat_cards:
                self.stats_grid.removeWidget(card)
            for i, card in enumerate(self.stat_cards):
                columns = 2 if narrow else 4
                self.stats_grid.addWidget(card, i // columns, i % columns)
            self.transfer_splitter.setSizes([300, 340] if narrow else [610, 380])
            for note in self.stat_notes:
                note.setVisible(not narrow)
            self._narrow_layout = narrow
        tiny = width < 800
        if tiny != self._tiny_layout:
            self.options_layout.setDirection(QBoxLayout.TopToBottom if tiny else QBoxLayout.LeftToRight)
            self._tiny_layout = tiny
        # Screen height is a separate constraint from screen width.
        if short != self._short_layout:
            self.stats_panel.setVisible(not short)
            self.main_layout.setSpacing(8 if short else 13)
            self._short_layout = short
        # Re-evaluate the graph for every height; both 650px and 500px are 'short'.
        graph_visible = height >= 560
        self.speed_chart_title.setVisible(graph_visible)
        self.speed_chart.setVisible(graph_visible)

    def update_logo_size(self, compact=False):
        pixels = 36 if compact else 58
        self.logo.setFixedSize(pixels, pixels)
        if not self.logo_pix.isNull():
            self.logo.setPixmap(self.logo_pix.scaled(pixels, pixels, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def show_language_menu(self):
        menu = QMenu(self)
        for code, spec in CATALOG.items():
            action = menu.addAction(spec['name'])
            action.setCheckable(True)
            action.setChecked(code == self.language)
            action.triggered.connect(lambda _checked=False, chosen=code: self.change_language_by_code(chosen))
        menu.exec(self.language_button.mapToGlobal(self.language_button.rect().bottomLeft()))

    def change_language_by_code(self, code):
        index = self.language_combo.findData(code)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)

    def change_language(self, index):
        if index < 0: return
        lang = self.language_combo.itemData(index)
        if lang not in CATALOG: return
        self.language = lang
        self.store.set_setting('language', lang)
        self.apply_language()

    def apply_language(self):
        self._compact_layout = None
        self.update_responsive_layout()
        translate_tree(self, self.language)
        apply_ui_font(QApplication.instance(), self.language)
        self.language_combo.setToolTip(translate('Language', self.language))
        self.language_button.setToolTip(translate('Language', self.language))
        self.language_label.setText(translate('Language', self.language))
        # Text entered by users (especially URLs) stays LTR.
        self.detail_url.setLayoutDirection(Qt.LeftToRight)
        self.detail_path.setLayoutDirection(Qt.LeftToRight)
        self.search.setLayoutDirection(Qt.LeftToRight)
        if self._ready:
            self.refresh()

    def set_filter(self, key):
        self.filter = key
        for k, button in self.nav.items():
            button.setChecked(k == key)
        self.refresh()

    def extents(self, path):
        try:
            st = Path(path).stat()
            key = (st.st_size, st.st_blocks, st.st_mtime_ns)
            old = self.cache.get(path)
            if old and old[0] == key:
                return old[1]
            data = inspect(path)
            self.cache[path] = (key, data)
            return data
        except (OSError, RuntimeError):
            return None

    def restore_queue(self):
        for job in self.store.all_jobs():
            if job['status'] in ('active','waiting','checking','recovering'):
                self.store.update(job['id'], status='paused' if job['kind'] == 'recovery' else 'queued', gid='')
        if not self.aria_error:
            for job in self.store.all_jobs():
                if job['kind'] == 'download' and job['status'] == 'queued':
                    self.launch_download(job['id'])

    def launch_download(self, jid):
        job = self.store.get(jid)
        if not job or job['kind'] != 'download':
            return
        if self.aria_error:
            self.store.update(jid, status='failed', error=self.aria_error)
            return
        if not job['url']:
            self.store.update(jid, status='paused', error='Missing URL')
            return
        path = Path(job['path'])
        # Protect preexisting downloads created by another tool without aria2 resume metadata.
        if path.exists() and path.stat().st_size > 0 and not Path(str(path)+'.aria2').exists():
            self.store.update(jid, status='paused', error='Existing file has no aria2 control data; use Recovery instead.')
            self.store.log(jid, 'Refused to overwrite a pre-existing file without aria2 resume metadata.', 'warning')
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            gid = self.aria.add(job['url'], path, self.store.settings('connections',8), self.store.settings('proxy',''))
            self.store.update(jid, gid=gid, status='waiting', error='')
            self.store.log(jid, 'Added to aria2 queue. Download URL safely saved.')
        except (OSError, AriaError) as exc:
            self.store.update(jid, status='failed', error=str(exc))
            self.store.log(jid, str(exc), 'error')

    def tick(self):
        any_changed = False
        download_speed = 0
        if not self.aria_error:
            for job in self.store.all_jobs():
                if job['kind'] != 'download' or not job['gid'] or job['status'] not in ('waiting','active','paused'):
                    continue
                try:
                    data = self.aria.status(job['gid'])
                except AriaError:
                    continue
                st = {'active':'active','waiting':'waiting','paused':'paused',
                      'complete':'complete','error':'failed','removed':'failed'}.get(data.get('status'),'failed')
                done = int(data.get('completedLength',0)); total = int(data.get('totalLength',0))
                speed = int(data.get('downloadSpeed',0))
                if st == 'active':
                    download_speed += speed
                if st != job['status'] or done != job['done'] or speed != job['speed'] or total != job['total']:
                    self.store.update(job['id'], status=st, done=done, total=total, speed=speed,
                                      error=data.get('errorMessage','') if st == 'failed' else '')
                    any_changed = True
                    if st in ('complete','failed') and st != job['status']:
                        self.store.log(job['id'], 'Download finished' if st=='complete' else
                                       ('Download failed: '+data.get('errorMessage','')), 'info' if st=='complete' else 'error')
        if self.recovery_worker is not None and self.recovery_worker.isRunning():
            if self.recovery_id:
                job = self.store.get(self.recovery_id)
                if job and job['status'] == 'recovering':
                    download_speed += int(job['speed'])
        self.val_speed.setText(f'{format_bytes(download_speed)}/s')
        self.speed_chart.push(download_speed)
        if any_changed:
            self.refresh()
        else:
            self.update_stats()

    def update_stats(self):
        jobs = self.store.all_jobs()
        self.val_all.setText(str(len(jobs)))
        self.val_active.setText(str(sum(j['status'] in ('active','recovering','checking') for j in jobs)))
        self.val_recovery.setText(str(sum(j['kind']=='recovery' and j['status'] not in ('recovered',) for j in jobs)))

    def visible(self, job):
        status = job['status']
        if self.filter == 'active' and status not in ('active','waiting','checking','recovering'):
            return False
        if self.filter == 'paused' and status not in ('queued','paused','verified'):
            return False
        if self.filter == 'complete' and status not in ('complete','recovered'):
            return False
        if self.filter == 'recovery' and job['kind'] != 'recovery':
            return False
        if self.filter == 'failed' and status != 'failed':
            return False
        search = self.search.text().casefold()
        return search in (job['path']+' '+job['url']+' '+job['status']).casefold()

    def refresh(self, *args):
        self.update_stats()
        visible = [j for j in self.store.all_jobs() if self.visible(j)]
        ids = [j['id'] for j in visible]
        if ids != self._rendered_ids:
            previous = self.selected_id
            self.queue.blockSignals(True)
            self.queue.clear()
            self._row_widgets.clear()
            for job in visible:
                item = QListWidgetItem()
                item.setData(Qt.UserRole, job['id'])
                item.setSizeHint(QSize(10, 210))
                self.queue.addItem(item)
                row = TransferRow(job)
                self.queue.setItemWidget(item, row)
                row.clicked.connect(lambda i=item: self.queue.setCurrentItem(i))
                row.context_requested.connect(lambda global_pos, jid=job['id']: self.task_menu(jid, global_pos))
                row.action_requested.connect(lambda action, jid=job['id']: self.card_action(jid, action))
                row.height_changed.connect(lambda height, i=item: self.resize_list_item(i, height))
                # First render must match the width, even before the row's resizeEvent.
                row.set_job(job, self.extents(job['path']) if job['kind']=='recovery' else None, self.language)
                self._row_widgets[job['id']] = row
                self.resize_list_item(item, row._height)
            self._rendered_ids = ids
            if previous in ids:
                self.queue.setCurrentRow(ids.index(previous))
            elif ids:
                self.queue.setCurrentRow(0)
            else:
                self.selected_id = None
            self.queue.blockSignals(False)
        for job in visible:
            row = self._row_widgets.get(job['id'])
            if row:
                row.set_job(job, self.extents(job['path']) if job['kind']=='recovery' else None, self.language)
        if self.queue.currentItem():
            selected = self.queue.currentItem().data(Qt.UserRole)
            if selected != self.selected_id:
                self.selected_id = selected
                self.update_details(new_selection=True)
            else:
                self.update_details(new_selection=False)
        elif not visible:
            self.selected_id = None
            self.update_details(new_selection=True)

    def resize_list_item(self, item, height):
        if self.queue.row(item) != -1 and item.sizeHint().height() != height:
            item.setSizeHint(QSize(10, height))

    def card_action(self, jid, action):
        """Use exactly the same handlers as the detail panel for a specific job."""
        if jid in self._rendered_ids:
            self.queue.setCurrentRow(self._rendered_ids.index(jid))
        self.selected_id = jid
        callbacks = {
            'start': self.run_selected, 'pause': self.pause_selected,
            'verify': self.verify_selected, 'test': self.test_selected,
            'folder': self.open_folder, 'copy': self.copy_saved_url,
            'remove': self.remove_selected,
        }
        if action in callbacks:
            callbacks[action]()

    def copy_saved_url(self):
        job = self.store.get(self.selected_id)
        if job and job['url']:
            QApplication.clipboard().setText(job['url'])
            self.statusBar().showMessage(translate('URL copied', self.language), 2000)

    def selected_changed(self, current, previous):
        self.selected_id = current.data(Qt.UserRole) if current else None
        self.update_details(new_selection=True)

    def update_details(self, new_selection=False):
        job = self.store.get(self.selected_id) if self.selected_id else None
        for w in (self.run_btn, self.pause_btn, self.verify_btn, self.test_btn):
            w.setEnabled(bool(job))
        if not job:
            self.detail_title.setText(translate('Select a transfer',self.language))
            self.detail_state.setText(translate('Download or recover your files from the workspace.',self.language))
            self.detail_url.setText(''); self.detail_path.setText('')
            self.allocation.hide(); self.legend_widget.hide(); self.alloc_stats.hide()
            self.detail_bar.hide(); self.progress_text.setText('')
            self.log.setPlainText('')
            return
        self.detail_title.setText(Path(job['path']).name)
        state_line = f"{job['kind'].upper()}   ·   {job['status'].upper()}"
        if job['error']:
            state_line += f"   ·   {job['error'][:150]}"
        self.detail_state.setText(state_line)
        self.detail_state.setToolTip(job['error'])
        self.detail_state.setStyleSheet(f'color:{color_status(job["status"])};font-size:12px;')
        self.detail_path.setText('SAVE TO  '+job['path'])
        if new_selection or not self.detail_url.hasFocus():
            if new_selection or self.detail_url.text() == '' or self.detail_url.text() == job['url']:
                self.detail_url.setText(job['url'])
        if job['kind'] == 'recovery':
            self.detail_bar.hide()
            self.allocation.show(); self.legend_widget.show(); self.alloc_stats.show()
            ext = self.extents(job['path'])
            if ext:
                self.allocation.set_data(ext['size'], ext['holes'])
                self.alloc_stats.setText(f"{translate('Allocated', self.language)} {format_bytes(ext['allocated'])}   ·   {translate('Missing', self.language)} {format_bytes(ext['missing'])}\n"
                                         f"Disk usage {format_bytes(ext['disk_usage'])}   ·   {len(ext['holes'])} sparse regions")
                if job['status'] in ('recovering','checking') and job['total']:
                    self.progress_text.setText(f"Operation: {format_bytes(job['done'])} / {format_bytes(job['total'])}")
                else:
                    self.progress_text.setText(translate('BLOCK ALLOCATION MAP  ·  GREEN = ALLOCATED, YELLOW = MISSING',self.language))
            else:
                self.alloc_stats.setText(translate('Cannot inspect this path or filesystem.',self.language))
                self.progress_text.setText(translate('Sparse extent information unavailable',self.language))
            self.run_btn.setText(translate('Repair missing bytes' if job['url'] else 'Add original URL', self.language))
            self.verify_btn.show()
            self.run_btn.setEnabled(job['status'] not in ('recovering','checking','recovered'))
            self.verify_btn.setEnabled(job['status'] not in ('recovering','checking'))
        else:
            self.detail_bar.show()
            self.allocation.hide(); self.legend_widget.hide(); self.alloc_stats.hide()
            total = int(job['total']); done = int(job['done'])
            self.detail_bar.setValue(min(100, round(done*100/total)) if total else 0)
            self.progress_text.setText(f"{format_bytes(done)} / {format_bytes(total) if total else 'unknown'}"
                                      + (f"    •   {format_bytes(job['speed'])}/s" if job['status']=='active' else ''))
            self.run_btn.setText('Start / Resume')
            self.run_btn.setEnabled(job['status'] not in ('active','waiting','complete'))
            self.verify_btn.hide()
        self.pause_btn.setText(translate('Stop recovery' if job['kind']=='recovery' else 'Pause', self.language))
        self.pause_btn.setEnabled(job['status'] in ('active','waiting','recovering','checking'))
        if new_selection:
            self.update_log()

    def update_log(self):
        if not self.selected_id:
            return
        events = self.store.events(self.selected_id)
        text = '\n'.join(time.strftime('%H:%M:%S',time.localtime(e['stamp'])) +
                         '  ' + e['detail'] for e in events)
        self.log.setPlainText(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def message(self, text, warning=False):
        self.statusBar().showMessage(text, 12000)
        if warning:
            QMessageBox.warning(self, 'Micro Downloader', text)

    def add_download(self):
        dlg = DownloadDialog(self.store.settings('directory', str(Path.home()/'Downloads')),
                             self.store.settings('connections',8), self)
        translate_tree(dlg, self.language)
        dlg.urls.setLayoutDirection(Qt.LeftToRight)
        if dlg.exec() != QDialog.Accepted:
            return
        urls = [s.strip() for s in dlg.urls.toPlainText().splitlines() if s.strip()]
        folder = Path(dlg.folder.text()).expanduser()
        if not folder.is_dir():
            self.message('Choose an existing destination folder.', True); return
        self.store.set_setting('directory', str(folder))
        self.store.set_setting('connections', dlg.connections.value())
        added = 0; errors = []
        for url in urls:
            if urlsplit(url).scheme not in ('http','https','ftp'):
                errors.append(f'Not a supported URL: {url[:75]}'); continue
            name = friendly_name(url)
            if name in ('.', '..', '') or '/' in name or '\\' in name:
                errors.append(f'Unsafe filename: {name}'); continue
            path = folder / name
            if any(existing['path'] == str(path) for existing in self.store.all_jobs()):
                errors.append(f'{name}: already present in the task list.'); continue
            if path.exists():
                errors.append(f'{name}: already exists. Use Recover file to attach the existing file.'); continue
            jid = self.store.add_job('download', path, url)
            self.launch_download(jid)
            added += 1
        self.refresh()
        self.message(f'Added {added} download(s).' + (f' Skipped {len(errors)}.' if errors else ''))
        if errors:
            QMessageBox.information(self, 'Skipped entries', '\n'.join(errors[:20]))

    def add_recovery(self, path='', url=''):
        # Defensive fallback for callers connected directly to Qt clicked(bool).
        if isinstance(path, bool):
            path = ''
        if not isinstance(path, (str, os.PathLike)):
            path = ''
        if not url and path:
            url = self.store.resolve_url(path)
        dlg = RecoveryDialog(path, url, self)
        translate_tree(dlg, self.language)
        if dlg.exec() != QDialog.Accepted:
            return
        path = Path(dlg.filepath.text()).expanduser().absolute()
        if not path.is_file():
            self.message('Select an existing local file before adding recovery.', True); return
        url = dlg.url.text().strip()
        if url and urlsplit(url).scheme not in ('https','http'):
            self.message('Recovery requires an HTTP or HTTPS original URL.', True); return
        ext = self.extents(str(path))
        if ext is None:
            self.message('Could not inspect sparse file extent map. You can add it, but automatic recovery may be unsupported.', False)
        if not any(j['path'] == str(path) and j['kind']=='recovery' for j in self.store.all_jobs()):
            jid = self.store.add_job('recovery', path, url, status='paused')
            self.store.log(jid, 'Existing file imported (read-only). Source URL saved.')
            self.set_filter('recovery')
            self.refresh()
            if jid in self._rendered_ids:
                self.queue.setCurrentRow(self._rendered_ids.index(jid))
        else:
            jid = next(j['id'] for j in self.store.all_jobs() if j['path']==str(path) and j['kind']=='recovery')
            self.store.update(jid, url=url)
            self.refresh()
            self.message('Existing recovery task selected; URL updated.')

    def save_url(self):
        job = self.store.get(self.selected_id)
        if not job:
            return
        url = self.detail_url.text().strip()
        if url and urlsplit(url).scheme not in ('http','https','ftp'):
            self.message('Enter a valid HTTP/HTTPS URL (FTP for regular downloads).', True); return
        if job['status'] in ('active','recovering','checking','waiting'):
            self.message('Pause the task before changing its original URL.', True); return
        self.store.update(job['id'], url=url)
        self.store.log(job['id'], 'Original download URL updated and saved.')
        self.update_log(); self.refresh()
        self.message('URL saved permanently in Micro Downloader’s database.')

    def copy_url(self):
        QApplication.clipboard().setText(self.detail_url.text())
        self.statusBar().showMessage('URL copied', 2000)

    def run_selected(self):
        job = self.store.get(self.selected_id)
        if not job:
            return
        if job['kind'] == 'recovery':
            if not job['url']:
                self.detail_url.setFocus(); self.message('Paste the original URL and select Save URL first.'); return
            if job['status'] == 'recovered':
                self.message('Already recovered. Run Test archive to check integrity.'); return
            self.start_recovery(job, repair=True)
        else:
            if job['status'] in ('active','waiting','complete'):
                return
            if job['gid']:
                try:
                    self.aria.unpause(job['gid'])
                    self.store.update(job['id'], status='waiting', error='')
                    self.refresh(); return
                except AriaError:
                    self.store.update(job['id'], gid='')
            self.launch_download(job['id'])
            self.refresh()

    def verify_selected(self):
        job = self.store.get(self.selected_id)
        if not job or job['kind'] != 'recovery':
            return
        if not job['url']:
            self.message('Save the original direct URL first.', True); return
        self.start_recovery(job, repair=False)

    def start_recovery(self, job, repair):
        if self.recovery_worker and self.recovery_worker.isRunning():
            self.message('Only one recovery or verification can run at a time.', True); return
        if not Path(job['path']).is_file():
            self.message('Selected file is missing.', True); return
        ext = self.extents(job['path'])
        if not ext or not ext['holes']:
            self.message('No sparse holes detected in this file. Recovery by missing block map is unavailable.', True); return
        self.recovery_worker = RecoveryWorker(job['path'], job['url'], repair,
                                             speed_kib=self.store.settings('speed_kib',0),
                                             proxy=self.store.settings('proxy',''),
                                             margin_mib=self.store.settings('margin_mib',1),
                                             chunk_mib=self.store.settings('chunk_mib',8),
                                             retries=self.store.settings('retries',4))
        self.recovery_id = job['id']
        self.store.update(job['id'], status='recovering' if repair else 'checking',
                          done=0,total=0,speed=0,error='')
        jid = job['id']
        self.recovery_worker.progress.connect(lambda done,total,speed, x=jid: self.recovery_progress(x,done,total,speed))
        self.recovery_worker.stage.connect(lambda message, x=jid: self.recovery_stage(x,message))
        self.recovery_worker.map_update.connect(lambda x=jid: self.update_recovery_map(x))
        self.recovery_worker.finished_result.connect(lambda success,message, x=jid, mode=repair:
                                                     self.recovery_finished(x,mode,success,message))
        self.recovery_worker.finished.connect(lambda: self.on_recovery_thread_finished())
        self.recovery_worker.start(); self.refresh()

    def recovery_progress(self, jid, done, total, speed):
        if self.store.get(jid):
            self.store.update(jid, done=done, total=total, speed=int(speed))
            if self.selected_id == jid:
                self.update_details()

    def recovery_stage(self, jid, message):
        self.store.log(jid, message)
        self.statusBar().showMessage(message[:180], 9000)
        if self.selected_id == jid:
            self.update_log()

    def update_recovery_map(self, jid):
        job = self.store.get(jid)
        if job:
            self.cache.pop(job['path'], None)
            self.refresh()

    def recovery_finished(self, jid, repair, success, message):
        job = self.store.get(jid)
        if job:
            new_status = ('recovered' if repair else 'verified') if success else ('paused' if 'cancel' in message.lower() or 'stopped at your request' in message.lower() else 'failed')
            self.store.update(jid, status=new_status, speed=0, error='' if success else message)
            self.store.log(jid, message, 'info' if success else 'error')
            self.update_recovery_map(jid)
            if self.selected_id == jid:
                self.update_log()
        self.statusBar().showMessage(message, 20000)
        if not success:
            QMessageBox.warning(self, 'Recovery check stopped', message)
        elif repair:
            QMessageBox.information(self, 'Recovery finished', message + '\n\nNow use Test archive to verify the entire multipart archive.')

    def on_recovery_thread_finished(self):
        self.recovery_worker = None
        self.recovery_id = None

    def pause_selected(self):
        job = self.store.get(self.selected_id)
        if not job:
            return
        if job['kind'] == 'recovery' and self.recovery_worker and self.recovery_id == job['id']:
            self.recovery_worker.cancel()
            self.message('Stopping safely after current request. Completed ranges remain on disk.')
        elif job['kind']=='download' and job['gid']:
            try:
                self.aria.pause(job['gid'])
                self.store.update(job['id'], status='paused', speed=0)
                self.refresh()
            except AriaError as exc:
                self.message(str(exc), True)

    def test_selected(self):
        job = self.store.get(self.selected_id)
        if not job:
            return
        if self.archive_worker and self.archive_worker.isRunning():
            self.message('An archive test is already running.', True); return
        if job['status'] in ('recovering','checking','active'):
            self.message('Stop writing to this file before running integrity verification.', True); return
        if not Path(job['path']).is_file():
            self.message('File not found.', True); return
        jid = job['id']
        preflight = volume_info(job['path'])
        if preflight['missing']:
            self.store.log(jid, preflight['summary'], 'error')
        password, accepted = QInputDialog.getText(
            self, translate('Archive password (optional)', self.language),
            translate('Leave empty if the archive is not password-protected.', self.language),
            QLineEdit.Password)
        if not accepted:
            return
        self.store.log(jid, 'Started 7-Zip archive integrity test. Password is never stored in the database.')
        self.archive_worker = ArchiveTest(job['path'], password)
        self.archive_worker.result.connect(lambda ok,msg, x=jid: self.archive_result(x,ok,msg))
        self.archive_worker.start()
        self.message('Archive test started. Results will appear in the Activity Log.')

    def archive_result(self, jid, ok, msg):
        self.store.log(jid, ('PASS: ' if ok else 'FAIL: ') + msg, 'info' if ok else 'error')
        if self.selected_id == jid:
            self.update_log()
        self.message('Archive integrity test passed.' if ok else 'Archive integrity test failed; check Activity Log.', not ok)

    def open_folder(self):
        job = self.store.get(self.selected_id)
        if job:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(job['path']).parent)))

    def remove_selected(self):
        job = self.store.get(self.selected_id)
        if not job:
            return
        if self.recovery_worker and self.recovery_id == job['id'] and self.recovery_worker.isRunning():
            self.message('Stop the recovery operation before removing its entry.', True); return
        if QMessageBox.question(self, 'Remove task', 'Remove this task from Micro Downloader?\nYour downloaded file and saved URL history will NOT be deleted.') != QMessageBox.Yes:
            return
        if job['kind']=='download' and job['gid']:
            try:
                self.aria.remove(job['gid'])
            except AriaError:
                pass
        self.store.delete(job['id'])
        self.selected_id = None
        self.refresh()

    def pause_all(self):
        count=0
        for job in self.store.all_jobs():
            if job['kind']=='download' and job['status'] in ('waiting','active') and job['gid']:
                try:
                    self.aria.pause(job['gid'])
                    self.store.update(job['id'], status='paused', speed=0)
                    count+=1
                except AriaError:
                    pass
        if self.recovery_worker and self.recovery_worker.isRunning():
            self.recovery_worker.cancel()
        self.refresh()
        self.message(f'Paused {count} regular downloads. An active recovery was asked to stop safely.')

    def resume_all(self):
        count=0
        for job in self.store.all_jobs():
            if job['kind']=='download' and job['status'] in ('queued','paused','failed'):
                if job['gid']:
                    try:
                        self.aria.unpause(job['gid'])
                        self.store.update(job['id'], status='waiting', error='')
                        count+=1
                        continue
                    except AriaError:
                        self.store.update(job['id'], gid='')
                self.launch_download(job['id'])
                count+=1
        self.refresh()
        self.message(f'Started or resumed {count} regular downloads. Recovery tasks require manual verification.')

    def speed_changed(self, value):
        self.store.set_setting('speed_kib', value)
        if self._ready and not self.aria_error:
            try:
                self.aria.set_limits(self.store.settings('parallel',3), value)
            except AriaError as exc:
                self.statusBar().showMessage(str(exc), 5000)
        if self._ready and self.recovery_worker and self.recovery_worker.isRunning():
            self.statusBar().showMessage('Speed limit updated for aria2. Recovery will use the new limit on its next run.', 9000)

    def open_settings(self):
        dlg = SettingsDialog(self.store, self)
        translate_tree(dlg, self.language)
        if dlg.exec() == QDialog.Accepted:
            dlg.persist(self.store)
            self.speed.blockSignals(True)
            self.speed.setValue(self.store.settings('speed_kib',0))
            self.speed.blockSignals(False)
            if not self.aria_error:
                try:
                    self.aria.set_limits(self.store.settings('parallel',3), self.store.settings('speed_kib',0))
                except AriaError as exc:
                    self.message(str(exc), True)
            self.message('Settings saved.')

    def export_urls(self):
        name,_ = QFileDialog.getSaveFileName(self, 'Export transfer library',
                                            str(Path.home()/'Downloads/micro-downloader-transfer-library.json'), 'JSON (*.json)')
        if not name:
            return
        payload = [{key: job[key] for key in ('kind','url','path','status','added')}
                   for job in self.store.all_jobs()]
        try:
            Path(name).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
            self.message(f'Exported {len(payload)} transfers.')
        except OSError as exc:
            self.message(str(exc), True)

    def queue_menu(self, point):
        item = self.queue.itemAt(point)
        if item:
            self.task_menu(item.data(Qt.UserRole), self.queue.viewport().mapToGlobal(point))

    def task_menu(self, jid, global_point):
        """Consistent context menu even over the filename or a card button."""
        job = self.store.get(jid)
        if not job:
            return
        if jid in self._rendered_ids:
            self.queue.setCurrentRow(self._rendered_ids.index(jid))
        self.selected_id = jid
        menu = QMenu(self)
        row = self._row_widgets.get(jid)
        for key in TransferRow.ACTIONS:
            label = row.buttons[key].text() if row else translate(TransferRow.LABELS[key], self.language)
            action = menu.addAction(label)
            if row:
                action.setEnabled(row.buttons[key].isEnabled())
            action.triggered.connect(lambda checked=False, k=key, job_id=jid: self.card_action(job_id, k))
        menu.exec(global_point)

    def closeEvent(self, event):
        if self.recovery_worker and self.recovery_worker.isRunning():
            QMessageBox.information(self, 'Recovery running',
                                    'Stop the recovery first, then close Micro Downloader. This protects the file during verified writes.')
            event.ignore(); return
        if self.archive_worker and self.archive_worker.isRunning():
            self.message('Please finish the running archive integrity test before exiting.')
            event.ignore(); return
        self.timer.stop()
        self.aria.stop()
        self.store.close()
        event.accept()


def launch(self_test=False):
    import sys
    app = QApplication(sys.argv[:1])
    app.setApplicationName('Micro Downloader')
    app.setOrganizationName('Micro Downloader')
    app.setWindowIcon(QIcon(str(Path(__file__).parent / 'assets' / 'logo.png')))
    window = MainWindow()
    if self_test:
        # Build smoke test: exercise actual Qt window construction then exit.
        window.show()
        def exit_test():
            window.close()
            app.quit()
        QTimer.singleShot(600, exit_test)
    else:
        window.show()
    return app.exec()
