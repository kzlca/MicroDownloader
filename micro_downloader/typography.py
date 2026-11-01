"""Select installed fonts. No third-party font files are redistributed.

Amiri has crisp Arabic/Persian calligraphic forms, with Naskh/Sans fallbacks
when it isn't installed (especially on Windows). UI language switching keeps
user-entered URLs and paths left-to-right; typography never alters their text.
"""
from PySide6.QtGui import QFont, QFontDatabase

RTL_FAMILIES = (
    'Amiri', 'Amiri Quran', 'Noto Naskh Arabic', 'Vazirmatn',
    'Noto Sans Arabic', 'Segoe UI', 'DejaVu Sans',
)
LTR_FAMILIES = ('Inter', 'Noto Sans', 'Segoe UI', 'DejaVu Sans')


def preferred_font(families, available):
    names = {name.casefold(): name for name in available}
    for wanted in families:
        if wanted.casefold() in names:
            return names[wanted.casefold()]
    return ''


def apply_ui_font(app, language):
    available = QFontDatabase.families()
    family = preferred_font(RTL_FAMILIES if language == 'fa' else LTR_FAMILIES, available)
    font = QFont(family) if family else QFont()
    font.setPointSize(12 if language == 'fa' else 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    return family
