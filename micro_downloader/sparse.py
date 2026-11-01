"""Read-only sparse extent inspection using SEEK_DATA/SEEK_HOLE on Linux.

A hole means no allocated data blocks, NOT cryptographic proof that all
allocated blocks are valid. Filesystems can conservatively report no holes.
"""
import errno
import os
from pathlib import Path

MIB = 1024 * 1024


def format_bytes(n):
    n = max(0, float(n))
    for suffix in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if n < 1024 or suffix == "PiB":
            return f"{n:.0f} {suffix}" if suffix == "B" else f"{n:.2f} {suffix}"
        n /= 1024


def read_at(fd, length, offset):
    """Positioned read; Windows Python does not export os.pread."""
    if hasattr(os, 'pread'):
        return os.pread(fd, length, offset)
    os.lseek(fd, offset, os.SEEK_SET)
    return os.read(fd, length)


def write_at(fd, data, offset):
    """Positioned write; only called from one recovery worker per file."""
    if hasattr(os, 'pwrite'):
        return os.pwrite(fd, data, offset)
    os.lseek(fd, offset, os.SEEK_SET)
    return os.write(fd, data)


def _holes_windows(fd, size):
    """Query NTFS allocated extents through FSCTL_QUERY_ALLOCATED_RANGES.

    Non-sparse files normally report all bytes allocated and thus cannot be
    recovered by allocation scanning. Zeroed allocated data is not a hole.
    """
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class AllocRange(ctypes.Structure):
        _fields_ = [('offset', ctypes.c_longlong), ('length', ctypes.c_longlong)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    ctl = kernel.DeviceIoControl
    ctl.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                    ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    ctl.restype = wintypes.BOOL
    handle = wintypes.HANDLE(msvcrt.get_osfhandle(fd))
    FSCTL_QUERY_ALLOCATED_RANGES = 0x000940CF
    ERROR_MORE_DATA = 234
    output_type = AllocRange * 4096
    allocated = []
    pos = 0
    while pos < size:
        query = AllocRange(pos, size-pos)
        output = output_type()
        count = wintypes.DWORD(0)
        success = ctl(handle, FSCTL_QUERY_ALLOCATED_RANGES,
                      ctypes.byref(query), ctypes.sizeof(query),
                      ctypes.byref(output), ctypes.sizeof(output),
                      ctypes.byref(count), None)
        err = ctypes.get_last_error() if not success else 0
        if not success and err != ERROR_MORE_DATA:
            raise OSError(err, 'Cannot query allocated file ranges on this Windows filesystem')
        n = count.value // ctypes.sizeof(AllocRange)
        if not n:
            if err == ERROR_MORE_DATA:
                raise RuntimeError('Windows returned no extents but reported MORE_DATA')
            break
        last = pos
        for record in output[:n]:
            a = max(pos, int(record.offset))
            b = min(size, int(record.offset+record.length))
            if a < b:
                allocated.append((a,b))
                last = max(last,b)
        if last <= pos:
            raise RuntimeError('Windows returned nonadvancing allocated ranges')
        pos = last
        if success:  # Entire requested interval was returned.
            break
    return complement(merge(allocated), size)


def holes_of_fd(fd, size):
    if os.name == 'nt':
        return _holes_windows(fd, size)
    if not hasattr(os, 'SEEK_DATA') or not hasattr(os, 'SEEK_HOLE'):
        raise RuntimeError('Sparse file inspection is unsupported on this platform')
    holes = []
    pos = 0
    while pos < size:
        try:
            at_data = os.lseek(fd, pos, os.SEEK_DATA)
        except OSError as exc:
            if exc.errno == errno.ENXIO:
                holes.append((pos, size))
                break
            if exc.errno in (errno.EINVAL, errno.ENOTSUP):
                raise RuntimeError('Filesystem does not support SEEK_DATA / SEEK_HOLE') from exc
            raise
        if at_data > pos:
            holes.append((pos, min(at_data, size)))
        at_hole = os.lseek(fd, at_data, os.SEEK_HOLE)
        if at_hole <= at_data:
            raise RuntimeError('Invalid filesystem extent information')
        pos = at_hole
    return holes


def inspect(path):
    path = Path(path)
    with path.open('rb', buffering=0) as f:
        stats = os.fstat(f.fileno())
        size = stats.st_size
        holes = holes_of_fd(f.fileno(), size)
        missing = sum(b-a for a,b in holes)
        disk_usage = getattr(stats, 'st_blocks', None)
        disk_usage = disk_usage * 512 if disk_usage is not None else size - missing
    return {'size': size, 'holes': holes, 'missing': missing,
            'allocated': size-missing, 'disk_usage': disk_usage}


def merge(spans):
    result = []
    for a, b in sorted(spans):
        if result and a <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], b))
        else:
            result.append((a, b))
    return result


def complement(spans, size):
    result = []
    at = 0
    for a, b in spans:
        if a > at:
            result.append((at, a))
        at = b
    if at < size:
        result.append((at, size))
    return result


def planned_repair(holes, size, margin=MIB):
    return merge([(max(0, a-margin), min(size, b+margin)) for a, b in holes])


def sample_spans(safe_spans, n_per_region=5, size=4096):
    samples = set()
    for a, b in safe_spans:
        if b <= a:
            continue
        for numerator, denominator in ((0, 1), (1, 4), (1, 2), (3, 4), (1, 1)):
            p = a + (b-a)*numerator//denominator
            p = min(max(a, p), max(a, b-size))
            samples.add((p, min(b, p+size)))
    return sorted(samples)
