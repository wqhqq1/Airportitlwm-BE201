"""Compare fileset entries of two kernel collections: UUID, segment sizes and segment bytes."""
import struct, sys, hashlib
def entries(path):
    b = open(path, 'rb').read()
    ncmds = struct.unpack_from('<I', b, 16)[0]; pos = 32; out = {}
    for _ in range(ncmds):
        cmd, n = struct.unpack_from('<II', b, pos)
        if cmd == 0x80000035:  # LC_FILESET_ENTRY
            vm, off, nameoff = struct.unpack_from('<QQI', b, pos + 8)
            name = b[pos + nameoff:b.index(b'\0', pos + nameoff)].decode()
            out[name] = off
        pos += n
    return b, out
def macho(b, off):
    ncmds = struct.unpack_from('<I', b, off + 16)[0]; pos = off + 32; segs = []; uuid = None
    for _ in range(ncmds):
        cmd, n = struct.unpack_from('<II', b, pos)
        if cmd == 0x19:
            name, vm, vs, fo, fs = struct.unpack_from('<16sQQQQ', b, pos + 8)
            segs.append((name.rstrip(b'\0').decode(), vs, fo, fs))
        elif cmd == 0x1b:
            uuid = b[pos + 8:pos + 24].hex()
        pos += n
    return uuid, segs
a, ea = entries(sys.argv[1]); c, ec = entries(sys.argv[2])
names = sys.argv[3:] or sorted(set(ea) | set(ec))
for nm in names:
    if nm not in ea or nm not in ec:
        print(nm, 'only in', 'old' if nm in ea else 'new'); continue
    ua, sa = macho(a, ea[nm]); uc, sc = macho(c, ec[nm])
    same_uuid = ua == uc
    segrows = []
    for (n1, v1, f1, s1), (n2, v2, f2, s2) in zip(sa, sc):
        h1 = hashlib.sha256(a[f1:f1 + s1]).hexdigest()[:12]; h2 = hashlib.sha256(c[f2:f2 + s2]).hexdigest()[:12]
        segrows.append(f"{n1}:{'=' if (v1, s1, h1) == (v2, s2, h2) else f'{v1:#x}/{h1}->{v2:#x}/{h2}'}")
    print(nm, 'UUID same' if same_uuid else f'UUID {ua[:8]}->{uc[:8]}', ' '.join(segrows))
