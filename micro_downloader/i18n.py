"""Small, offline translation catalog and live Qt widget retranslation.

Community language packs: assets/i18n/<locale>.json
{"name": "Español", "rtl": false, "strings": {"Settings": "Configuración"}}
Untranslated messages deliberately fall back to English. No network requests.
"""
import json
from pathlib import Path

LANGUAGES = {
    'en': {'name': 'English', 'rtl': False, 'strings': {}},
    'fa': {'name': 'فارسی', 'rtl': True, 'strings': {
        'Engine':'موتور دانلود', 'Restart download engine':'راه‌اندازی دوباره موتور دانلود',
        'All transfers':'همه انتقال‌ها', 'Downloading':'در حال دانلود',
        'Paused & queued':'متوقف‌شده و در صف', 'Completed':'تکمیل‌شده',
        'Recovery lab':'بازیابی فایل', 'Failed':'ناموفق',
        'Export URL library':'خروجی پیوندها', 'Settings':'تنظیمات',
        'Language':'زبان', 'English':'انگلیسی',
        'Transfer workspace':'مدیریت دانلودها',
        'Download, organize, and recover interrupted files without losing progress.':'دانلود، مدیریت و بازیابی فایل‌های ناقص بدون از دست دادن پیشرفت',
        'New download':'دانلود جدید', 'Recover file':'بازیابی فایل',
        'Saved transfers':'انتقال‌های ذخیره‌شده', 'Active tasks':'کارهای فعال',
        'Download speed':'سرعت دانلود', 'Recoverable':'قابل بازیابی',
        'URLs kept locally':'پیوندهای ذخیره‌شده', 'Current session':'نشست کنونی',
        'Live transfer total':'سرعت لحظه‌ای', 'Sparse-file tasks':'بازیابی فایل‌های ناقص',
        'Search filenames, URLs, or paths…':'جستجوی فایل، پیوند یا مسیر…',
        'Speed cap':'محدودیت سرعت', 'Unlimited':'نامحدود',
        'Transfers are restored from your local database when Micro Downloader starts.':'دانلودها پس از راه‌اندازی دوباره از پایگاه داده بازیابی می‌شوند.',
        'Pause all':'توقف همه', 'Resume all':'ادامه همه',
        'TRANSFER DETAILS':'جزئیات انتقال', 'Select a transfer':'یک انتقال انتخاب کنید',
        'Your download details will appear here.':'جزئیات دانلود اینجا نمایش داده می‌شود.',
        'Source URL':'پیوند منبع', 'Paste an original URL here…':'پیوند اصلی را اینجا قرار دهید…',
        'Save URL':'ذخیره پیوند', 'Copy URL':'کپی پیوند', 'No selection':'انتخاب نشده',
        'Allocated':'اختصاص‌یافته', 'Missing':'داده‌های ناقص',
        'Start / Resume':'شروع / ادامه', 'Pause':'توقف', 'Stop recovery':'توقف بازیابی',
        'Verify ranges':'بررسی محدوده‌ها', 'Test archive':'آزمایش آرشیو',
        'Open folder':'باز کردن پوشه', 'Remove task':'حذف وظیفه',
        'ACTIVITY LOG':'گزارش فعالیت', 'Download history':'تاریخچه دانلود',
        'Download preferences':'تنظیمات دانلود',
        'Micro Downloader settings':'تنظیمات Micro Downloader',
        'Default directory':'پوشه پیش‌فرض', 'Simultaneous downloads':'دانلودهای هم‌زمان',
        'Connections per file':'اتصال‌های هر فایل', 'Total speed limit':'محدودیت کلی سرعت',
        'Network proxy':'پروکسی شبکه', 'Recovery retries per chunk':'تلاش مجدد برای هر بخش',
        'Recovery chunk size':'اندازه بخش بازیابی', 'Recovery edge overlap':'هم‌پوشانی لبه‌های بازیابی',
        'Browse':'انتخاب پوشه', 'Browse…':'انتخاب…', 'Choose file…':'انتخاب فایل…',
        'Add downloads':'افزودن دانلودها', 'Paste direct links — one URL per line':'پیوندهای مستقیم را هرکدام در یک سطر وارد کنید',
        'Download directory':'پوشه دانلود', 'Add to queue':'افزودن به صف',
        'Recover an existing download':'بازیابی دانلود قبلی',
        'Attach an interrupted file':'انتخاب فایل دانلود ناقص',
        'Existing partial file':'فایل ناقص موجود',
        'Original direct HTTP/HTTPS URL (can be added later)':'پیوند اصلی HTTP/HTTPS (قابل افزودن در آینده)',
        'Choose folder':'انتخاب پوشه', 'Cancel':'لغو', 'OK':'تأیید',
        'Add to Recovery':'افزودن به بازیابی', 'Export transfer library':'خروجی لیست انتقال‌ها',
        'Save':'ذخیره', 'Ready':'آماده', 'Speed history':'نمودار سرعت دانلود',
        'No active transfers':'انتقال فعالی وجود ندارد', 'Archive password (optional)':'رمز آرشیو (اختیاری)',
        'Leave empty if the archive is not password-protected.':'اگر آرشیو رمز ندارد، خالی بگذارید.',
        'Verify archive':'بررسی آرشیو', 'Archive test started. Results will appear in the Activity Log.':'آزمایش آرشیو آغاز شد؛ نتیجه در گزارش فعالیت نمایش داده می‌شود.',
        'PARTIAL':'ناقص', 'PASS':'موفق', 'FAIL':'ناموفق',
        'Local-first  ·  Private storage\nQt / aria2 / curl / SQLite':'ذخیره‌سازی محلی و خصوصی\nQt / aria2 / curl / SQLite',
        'Repair missing bytes':'بازیابی بخش\u200cهای ناقص',
        'Add original URL':'افزودن پیوند اصلی',
        'BLOCK ALLOCATION MAP  ·  GREEN = ALLOCATED, YELLOW = MISSING':'نقشه بخش\u200cهای فایل · سبز: موجود، زرد: ناقص',
        'Cannot inspect this path or filesystem.':'بررسی این مسیر یا سیستم فایل ممکن نیست.',
        'Sparse extent information unavailable':'اطلاعات بخش\u200cهای فایل موجود نیست',
        'Download or recover your files from the workspace.':'دانلود یا بازیابی فایل\u200cها از پنل مدیریت',
        'Total transfer speed cap. 0 means unlimited.':'حداکثر سرعت انتقال؛ صفر یعنی نامحدود',
        'Sparse recovery':'بازیابی فایل ناقص',
        'Active':'فعال',
        'PAUSED':'متوقف\u200cشده',
        'ACTIVE':'فعال',
        'FAILED':'ناموفق',
        'QUEUED':'در صف',
        'COMPLETE':'تکمیل\u200cشده',
        'RECOVERED':'بازیابی شد',
        'VERIFYING':'در حال بررسی',
        'Checking':'در حال بررسی',
        'RECOVERING':'در حال بازیابی',
        'WAITING':'در انتظار',
        'The speed cap applies to all aria2 downloads together. The recovery curl worker has its own cap.\nRecovery checks current settings when a new operation begins.':'محدودیت سرعت روی همه دانلودهای aria2 اعمال می\u200cشود؛ بازیابی curl محدودیت جدا دارد.\nبازیابی در هر اجرا تنظیمات کنونی را می\u200cخواند.',
        'Micro Downloader will map allocated (green) and missing (yellow) blocks.\nIt never writes during the initial analysis.':'بخش\u200cهای موجود (سبز) و ناقص (زرد) نمایش داده می\u200cشوند.\nتحلیل اولیه هیچ تغییری در فایل نمی\u200cدهد.',
        'For recovery, the URL must return the exact original file and support HTTP byte ranges.\nA sparse file can contain corrupted allocated bytes; verify the final archive/checksum.':'برای بازیابی، پیوند باید فایل اصلی یکسان را برگرداند و از درخواست محدوده\u200cهای بایتی پشتیبانی کند.\nپس از بازیابی، صحت آرشیو یا هش فایل را بررسی کنید.',
        'Start / repair':'شروع / تعمیر',
        'Pause / stop':'توقف',
        'Remove from list':'حذف از فهرست',
        'Not a supported URL':'پیوند پشتیبانی نمی\u200cشود',
        'Network':'شبکه',
        'Downloading speed history':'تاریخچه سرعت دانلود',
        'URL copied':'پیوند کپی شد',
        'Start':'شروع',
    }},
    'tr': {'name': 'Türkçe', 'rtl': False, 'strings': {
        'Engine':'İndirme motoru', 'Restart download engine':'İndirme motorunu yeniden başlat',
        'All transfers':'Tüm aktarımlar', 'Downloading':'İndiriliyor',
        'Paused & queued':'Duraklatıldı / Sırada', 'Completed':'Tamamlandı',
        'Recovery lab':'Dosya kurtarma', 'Failed':'Başarısız',
        'Export URL library':'Bağlantıları dışa aktar', 'Settings':'Ayarlar',
        'Language':'Dil', 'Transfer workspace':'İndirme merkezi',
        'Download, organize, and recover interrupted files without losing progress.':'İndirmeleri yönetin ve eksik dosyaları ilerlemenizi kaybetmeden kurtarın.',
        'New download':'Yeni indirme', 'Recover file':'Dosyayı kurtar',
        'Saved transfers':'Kayıtlı aktarımlar', 'Active tasks':'Etkin görevler',
        'Download speed':'İndirme hızı', 'Recoverable':'Kurtarılabilir',
        'URLs kept locally':'Bağlantılar yerel saklanır', 'Current session':'Geçerli oturum',
        'Live transfer total':'Anlık toplam hız', 'Sparse-file tasks':'Eksik dosya görevleri',
        'Search filenames, URLs, or paths…':'Dosya, bağlantı veya yol ara…',
        'Speed cap':'Hız sınırı', 'Unlimited':'Sınırsız',
        'Transfers are restored from your local database when Micro Downloader starts.':'Uygulama açıldığında aktarımlar yerel veritabanından yüklenir.',
        'Pause all':'Tümünü duraklat', 'Resume all':'Tümünü sürdür',
        'TRANSFER DETAILS':'AKTARIM AYRINTILARI', 'Select a transfer':'Bir aktarım seçin',
        'Your download details will appear here.':'İndirme ayrıntıları burada görünür.',
        'Source URL':'Kaynak URL', 'Paste an original URL here…':'Orijinal URL’yi buraya yapıştırın…',
        'Save URL':'URL kaydet', 'Copy URL':'URL kopyala', 'No selection':'Seçim yok',
        'Allocated':'Ayrılmış', 'Missing':'Eksik',
        'Start / Resume':'Başlat / Sürdür', 'Pause':'Duraklat', 'Stop recovery':'Kurtarmayı durdur',
        'Verify ranges':'Aralıkları doğrula', 'Test archive':'Arşivi test et',
        'Open folder':'Klasörü aç', 'Remove task':'Görevi kaldır',
        'ACTIVITY LOG':'ETKİNLİK GÜNLÜĞÜ', 'Download preferences':'İndirme tercihleri',
        'Micro Downloader settings':'Micro Downloader ayarları',
        'Default directory':'Varsayılan klasör', 'Simultaneous downloads':'Eşzamanlı indirmeler',
        'Connections per file':'Dosya başına bağlantı', 'Total speed limit':'Toplam hız sınırı',
        'Network proxy':'Ağ proxy’si', 'Recovery retries per chunk':'Parça başına yeniden deneme',
        'Recovery chunk size':'Kurtarma parça boyutu', 'Recovery edge overlap':'Kenar örtüşme payı',
        'Browse':'Gözat', 'Browse…':'Gözat…', 'Choose file…':'Dosya seç…',
        'Add downloads':'İndirme ekle', 'Paste direct links — one URL per line':'Doğrudan bağlantıları satır satır yapıştırın',
        'Download directory':'İndirme klasörü', 'Add to queue':'Sıraya ekle',
        'Recover an existing download':'Mevcut indirmeyi kurtar',
        'Attach an interrupted file':'Yarım kalan dosyayı seçin',
        'Existing partial file':'Mevcut eksik dosya',
        'Original direct HTTP/HTTPS URL (can be added later)':'Orijinal HTTP/HTTPS URL (sonradan eklenebilir)',
        'Choose folder':'Klasör seç', 'Cancel':'İptal', 'OK':'Tamam',
        'Add to Recovery':'Kurtarmaya ekle', 'Export transfer library':'Aktarım listesini dışa aktar',
        'Save':'Kaydet', 'Ready':'Hazır', 'Speed history':'İndirme hızı geçmişi',
        'No active transfers':'Etkin aktarım yok', 'Archive password (optional)':'Arşiv parolası (isteğe bağlı)',
        'Leave empty if the archive is not password-protected.':'Arşiv parola korumalı değilse boş bırakın.',
        'Verify archive':'Arşivi doğrula', 'Archive test started. Results will appear in the Activity Log.':'Arşiv testi başladı; sonuçlar etkinlik günlüğünde görünecek.',
        'PARTIAL':'EKSİK', 'PASS':'BAŞARILI', 'FAIL':'BAŞARISIZ',
        'Local-first  ·  Private storage\nQt / aria2 / curl / SQLite':'Özel, yerel veri saklama\nQt / aria2 / curl / SQLite',
        'Repair missing bytes':'Eksik baytları kurtar',
        'Add original URL':'Orijinal URL ekle',
        'BLOCK ALLOCATION MAP  ·  GREEN = ALLOCATED, YELLOW = MISSING':'BLOK HARİTASI · YEŞİL: MEVCUT, SARI: EKSİK',
        'Cannot inspect this path or filesystem.':'Bu yol ya da dosya sistemi incelenemiyor.',
        'Sparse extent information unavailable':'Blok bilgisi kullanılamıyor',
        'Download or recover your files from the workspace.':'Dosyalarınızı panelden indirin veya kurtarın.',
        'Total transfer speed cap. 0 means unlimited.':'Toplam hız sınırı; 0 sınırsız demektir.',
        'Sparse recovery':'Eksik dosya kurtarma',
        'PAUSED':'DURAKLATILDI',
        'ACTIVE':'ETKİN',
        'FAILED':'BAŞARISIZ',
        'QUEUED':'SIRADA',
        'COMPLETE':'TAMAMLANDI',
        'RECOVERED':'KURTARILDI',
        'VERIFYING':'DOĞRULANIYOR',
        'Checking':'Kontrol ediliyor',
        'RECOVERING':'KURTARILIYOR',
        'WAITING':'BEKLENİYOR',
        'The speed cap applies to all aria2 downloads together. The recovery curl worker has its own cap.\nRecovery checks current settings when a new operation begins.':'Hız sınırı tüm aria2 indirmelerine birlikte uygulanır. curl kurtarma ayrı sınır kullanır.\nKurtarma, ayarları yeni işlemin başlangıcında okur.',
        'Micro Downloader will map allocated (green) and missing (yellow) blocks.\nIt never writes during the initial analysis.':'Mevcut (yeşil) ve eksik (sarı) bloklar gösterilir.\nİlk analiz dosyayı değiştirmez.',
        'For recovery, the URL must return the exact original file and support HTTP byte ranges.\nA sparse file can contain corrupted allocated bytes; verify the final archive/checksum.':'Kurtarma URL’si orijinal dosyayla aynı olmalı ve HTTP bayt aralıklarını desteklemelidir.\nSonunda arşiv veya dosya sağlama toplamını doğrulayın.',
        'Start / repair':'Başlat / onar',
        'Pause / stop':'Duraklat',
        'Remove from list':'Listeden kaldır',
        'Downloading speed history':'İndirme hızı geçmişi',
        'URL copied':'URL kopyalandı',
        'Start':'Başlat',
    }},
}


def load_languages():
    found = {k: dict(v) for k, v in LANGUAGES.items()}
    folder = Path(__file__).resolve().parent / 'assets' / 'i18n'
    for path in sorted(folder.glob('*.json')):
        if not path.stem.isidentifier():
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data.get('strings'), dict) and isinstance(data.get('name'), str):
                found[path.stem] = {'name': data['name'], 'rtl': bool(data.get('rtl')), 'strings': data['strings']}
        except (OSError, ValueError, TypeError):
            pass
    return found


CATALOG = load_languages()


def translate(source, lang):
    return CATALOG.get(lang, CATALOG['en'])['strings'].get(source, source)


def is_rtl(lang):
    return bool(CATALOG.get(lang, CATALOG['en'])['rtl'])


def translate_tree(root, lang):
    """Translate static Qt widget text in place without overwriting user-entered values.

    Remembers English source string per property, so switching back to English
    works. Dynamic values not in catalog are intentionally left alone.
    """
    from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit, QComboBox, QGroupBox
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    QApplication.instance().setLayoutDirection(Qt.RightToLeft if is_rtl(lang) else Qt.LeftToRight)
    root.setLayoutDirection(Qt.RightToLeft if is_rtl(lang) else Qt.LeftToRight)
    widgets = [root] + root.findChildren(QWidget)
    for widget in widgets:
        for prop, getter, setter in (
            ('text', getattr(widget, 'text', None), getattr(widget, 'setText', None)),
            ('placeholder', getattr(widget, 'placeholderText', None), getattr(widget, 'setPlaceholderText', None)),
            ('title', getattr(widget, 'title', None), getattr(widget, 'setTitle', None)),
            ('window_title', getattr(widget, 'windowTitle', None), getattr(widget, 'setWindowTitle', None)),
            ('tooltip', getattr(widget, 'toolTip', None), getattr(widget, 'setToolTip', None)),
        ):
            if not callable(getter) or not callable(setter):
                continue
            try:
                current = getter()
            except TypeError:
                continue
            if not isinstance(current, str) or not current:
                continue
            source_prop = '_md_src_' + prop
            last_prop = '_md_last_' + prop
            base = widget.property(source_prop)
            previous = widget.property(last_prop)
            if base is None or current != previous:
                base = current
                widget.setProperty(source_prop, base)
            translated = translate(base, lang)
            if translated != current:
                setter(translated)
            widget.setProperty(last_prop, translated)
        if isinstance(widget, QLineEdit):
            # Keep user-entered URLs, file paths, and passwords LTR even in Persian UI.
            widget.setLayoutDirection(Qt.LeftToRight)
    return root
