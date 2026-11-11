#!/usr/bin/env python3
"""OpenCore's injection rule for a kext's segments (OcMachoLib InternalMachoExpandImage, size-only mode).

OpenCore expands the file so each segment sits at its VM address. Walking the segments in order with
delta = sum of (vmsize - filesize) of the segments before, it needs vmaddr == fileoff + delta + first vmaddr and
filesize <= vmsize; otherwise the expanded size is 0 and the kext is skipped at boot with
"Failed to fit 64-bit kext ... - Invalid Parameter" (1.1.54 on 2026-11-08: a page gap before __LINKEDIT).
Usage: oc_layout_check.py MACHO [MACHO...]; exit status 1 if any file breaks the rule.
"""
import struct, sys

LC_SEGMENT_64 = 0x19

def segments(path):
    data = open(path, 'rb').read()
    magic, _, _, _, ncmds, _, _, _ = struct.unpack_from('<IiiIIIII', data, 0)
    assert magic == 0xfeedfacf, f'{path}: not a 64-bit Mach-O'
    off, out = 32, []
    for _ in range(ncmds):
        cmd, size = struct.unpack_from('<II', data, off)
        if cmd == LC_SEGMENT_64:
            name = data[off + 8:off + 24].rstrip(b'\0').decode()
            vmaddr, vmsize, fileoff, filesize = struct.unpack_from('<QQQQ', data, off + 24)
            out.append((name, vmaddr, vmsize, fileoff, filesize))
        off += size
    return out

def problems(path):
    segs = segments(path)
    if not segs:
        return ['no segments']
    first, delta, bad = segs[0][1], 0, []
    for name, vmaddr, vmsize, fileoff, filesize in segs:
        if filesize > vmsize:
            bad.append(f'{name}: filesize {filesize:#x} > vmsize {vmsize:#x}')
        if vmaddr - (fileoff + delta) != first:
            bad.append(f'{name}: vmaddr {vmaddr:#x} != fileoff {fileoff:#x} + delta {delta:#x}')
        delta += vmsize - filesize
    return bad

if __name__ == '__main__':
    failed = False
    for p in sys.argv[1:]:
        bad = problems(p)
        print(('FAIL ' if bad else 'OK ') + p + ('' if not bad else ': ' + '; '.join(bad)))
        failed |= bool(bad)
    sys.exit(1 if failed else 0)
