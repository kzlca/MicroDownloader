DARK = """
QWidget { background: #0d121b; color: #eaf0f8; }
QMainWindow, QDialog { background: #0d121b; }
QLabel#brand { color: #f1f7ff; font-size: 23px; font-weight: 800; }
QLabel#overline { color: #74879f; font-size: 10px; font-weight: 700; }
QLabel#heading { font-size: 20px; font-weight: 750; }
QLabel#dim { color: #8293a9; }
QLabel#value { font-size: 22px; font-weight: 800; }
QFrame#sidebar { background: #101823; border-right: 1px solid #263143; }
QFrame#panel, QFrame#stat { background: #151e2b; border: 1px solid #273346; border-radius: 14px; }
QFrame#detail { background: #101823; border-left: 1px solid #263143; }
QPushButton { background: #202d3d; border: 1px solid #324357; border-radius: 9px; padding: 8px 13px; color: #e8eff9; font-weight: 600; }
QPushButton:hover { background: #2d4055; border-color: #4d6781; }
QPushButton:pressed { background: #283746; }
QPushButton:disabled { color: #556777; background: #17212d; border-color: #253344; }
QPushButton#primary { background: #328def; border: 1px solid #409dff; color: white; }
QPushButton#primary:hover { background: #52a7ff; }
QPushButton#nav { text-align: left; background: transparent; border: 0; padding: 13px 14px; color: #a3b4c9; }
QPushButton#nav:hover { background: #202d3f; }
QPushButton#nav:checked { background: #223e5d; color: #eff7ff; border-left: 3px solid #55aaff; }
QLineEdit,QPlainTextEdit,QTextEdit,QComboBox,QSpinBox,QDoubleSpinBox { background: #121c29; border: 1px solid #2b3b4f; border-radius: 8px; padding: 8px; selection-background-color: #2677c7; }
QLineEdit:focus,QPlainTextEdit:focus,QComboBox:focus,QSpinBox:focus { border-color: #4b97f2; }
QListWidget { background: #0d121b; border: 0; outline: none; }
QListWidget::item { background: transparent; border: none; }
QListWidget::item:selected { background: transparent; }
QScrollBar:vertical { background: #0d121b; width: 10px; }
QScrollBar::handle:vertical { background: #33475b; border-radius: 5px; min-height: 35px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height: 0px; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QToolTip { background: #1d2a3b; color: white; padding: 7px; border: 1px solid #41546d; }
QMenu { background: #182333; border: 1px solid #34465b; }
QMenu::item:selected { background: #2a4460; }
QSplitter::handle { background: #263143; width: 1px; }
QWidget#sidebarContent, QScrollArea { background: #101823; border: 0; }
QScrollArea > QWidget > QWidget { background: transparent; }
QProgressBar { background: #253142; border: 0; border-radius: 5px; text-align: center; color: white; height: 9px; }
QProgressBar::chunk { background: #469ffc; border-radius: 5px; }
"""
