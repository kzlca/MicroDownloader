"""Safe archive diagnostics. Never extracts or changes archive contents."""
import re
from pathlib import Path


def volume_info(file_path, output=''):
    """Return present/missing volume numbers and a human-readable diagnosis."""
    path = Path(file_path)
    m = re.fullmatch(r'(?P<prefix>.+)\.part(?P<num>\d+)\.rar', path.name, re.IGNORECASE)
    if not m:
        return {'root': path, 'present': [], 'missing': [], 'expected': None, 'summary': ''}
    prefix, width = m.group('prefix'), len(m.group('num'))
    found = []
    for match in path.parent.iterdir():
        f = re.fullmatch(re.escape(prefix) + r'\.part(\d+)\.rar', match.name, flags=re.IGNORECASE)
        if f and match.is_file():
            found.append(int(f.group(1)))
    present = sorted(set(found))
    reported = re.search(r'^Volumes\s*=\s*(\d+)', output, flags=re.MULTILINE)
    expected = int(reported.group(1)) if reported else (max(present) if present else None)
    missing = [n for n in range(1, (expected or 0)+1) if n not in present]
    root = path.with_name(prefix + '.part' + str(1).zfill(width) + '.rar')
    notes = []
    if reported:
        notes.append(f'7-Zip reports {expected} volume(s); found {len(present)} locally.')
    else:
        notes.append(f'Found {len(present)} volume(s) locally; total expected count not yet confirmed.')
    if missing:
        names = ', '.join(prefix + '.part' + str(n).zfill(width) + '.rar' for n in missing)
        notes.append('MISSING VOLUME(S): ' + names)
        # Only if a reported total physical size exists, and all but last are full-sized.
        phys = re.search(r'^Total Physical Size\s*=\s*(\d+)', output, flags=re.MULTILINE)
        if phys and expected == max(missing) and len(missing) == 1 and len(present) == expected-1:
            sizes = [path.with_name(prefix + '.part' + str(n).zfill(width) + '.rar').stat().st_size for n in present]
            remaining = int(phys.group(1)) - sum(sizes)
            if remaining > 0:
                notes.append(f'Estimated missing last volume size: {remaining/1048576:.1f} MiB (based on 7-Zip reported total).')
    return {'root': root, 'present': present, 'missing': missing, 'expected': expected, 'summary': '\n'.join(notes)}


def summarize_7z(file_path, stdout, stderr, exit_code):
    combined = stdout + '\n' + stderr
    vol = volume_info(file_path, combined)
    low = combined.lower()
    hints = []
    if vol['summary']:
        hints.append(vol['summary'])
    if 'wrong password' in low or 'can not open encrypted archive' in low:
        hints.append('PASSWORD: Archive may require a different password.')
    elif 'encrypted = +' in low and exit_code:
        hints.append('ENCRYPTED: If you entered no password, retry with the correct archive password.')
    if 'headers error' in low:
        hints.append('HEADERS ERROR: At least one archive header is missing or unreadable. Incomplete volumes can cause this.')
    if 'data error' in low or 'crc failed' in low:
        hints.append('DATA ERROR: Some archive data failed integrity checking. This is not necessarily a password issue; check all volumes and previously allocated bytes.')
    if 'unexpected end of archive' in low:
        hints.append('INCOMPLETE: Archive appears truncated.')
    if not hints and exit_code != 0:
        hints.append('7-Zip encountered an error. Review its output below.')
    success = exit_code == 0 and not vol['missing'] and 'Everything is Ok' in combined
    if success:
        hints.insert(0, 'PASS: Archive integrity test completed.')
    elif vol['missing']:
        hints.insert(0, 'INCOMPLETE ARCHIVE: Add the missing volume(s) before concluding recovered data is corrupted.')
    return success, '\n\n'.join(hints) + f'\n\n7-Zip exit code {exit_code}\n\n' + combined[-8000:]
