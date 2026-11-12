"""Normalized per-function disassembly diff of one fileset entry between two kernel collections."""
import struct, sys, bisect, json, re
sys.path.insert(0, sys.argv[1])
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_MEM, X86_OP_IMM, X86_REG_RIP

def load(kc, nmfile, entry):
    b = open(kc, 'rb').read()
    ncmds = struct.unpack_from('<I', b, 16)[0]; pos = 32; segs = []; eoff = None
    for _ in range(ncmds):
        cmd, n = struct.unpack_from('<II', b, pos)
        if cmd == 0x19:
            name, vm, vs, fo, fs = struct.unpack_from('<16sQQQQ', b, pos + 8); segs.append((vm, fs, fo))
        elif cmd == 0x80000035:
            vm, off, no = struct.unpack_from('<QQI', b, pos + 8)
            if b[pos + no:b.index(b'\0', pos + no)].decode() == entry: eoff = off
        pos += n
    # the entry's executable ranges
    nc = struct.unpack_from('<I', b, eoff + 16)[0]; p = eoff + 32; ex = []
    for _ in range(nc):
        cmd, n = struct.unpack_from('<II', b, p)
        if cmd == 0x19:
            name, vm, vs, fo, fs, maxp, initp = struct.unpack_from('<16sQQQQii', b, p + 8)
            if initp & 4: ex.append((vm, vm + vs))
        p += n
    syms = {}; allad = set()
    for l in open(nmfile):
        v = l.split()
        if len(v) == 3:
            try: a = int(v[0], 16)
            except ValueError: continue
            allad.add(a); syms.setdefault(a, v[2])
    order = sorted(allad)
    def read(a, n):
        for vm, fs, fo in segs:
            if vm <= a and a + n <= vm + fs: return b[fo + a - vm:fo + a - vm + n]
        return b''
    funcs = {}
    for a, s in syms.items():
        if any(lo <= a < hi for lo, hi in ex) and not s.startswith('ltmp'):
            i = bisect.bisect_right(order, a); end = order[i] if i < len(order) else a + 64
            hi = min(h for lo, h in ex if lo <= a < h); end = min(end, hi, a + 0x10000)
            funcs[s] = (a, end)
    return syms, order, funcs, read

def name_at(syms, order, t):
    if t in syms: return syms[t]
    i = bisect.bisect_right(order, t) - 1
    return f'{syms[order[i]]}+{t - order[i]:#x}' if i >= 0 and t - order[i] < 0x100000 else 'addr'

def norm(syms, order, read, a, end):
    md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True
    code = read(a, end - a); insns = list(md.disasm(code, a)); idx = {i.address: k for k, i in enumerate(insns)}; out = []
    for i in insns:
        s = i.mnemonic; ops = []
        for o in i.operands:
            if o.type == X86_OP_MEM:
                if o.mem.base == X86_REG_RIP:
                    t = i.address + i.size + o.mem.disp; ops.append('[' + (f'L{idx[t]}' if t in idx else name_at(syms, order, t)) + ']')
                else:
                    ops.append(f'[{i.reg_name(o.mem.base) if o.mem.base else ""}+{i.reg_name(o.mem.index) if o.mem.index else ""}*{o.mem.scale}+{o.mem.disp:#x}]')
            elif o.type == X86_OP_IMM:
                v = o.imm & 0xffffffffffffffff
                if i.group(1) or i.group(2) or i.group(7) or v >= 0xffffff8000000000:  # jump/call/relative
                    ops.append(f'L{idx[v]}' if v in idx else name_at(syms, order, v))
                else: ops.append(f'{v:#x}')
            else: ops.append(i.reg_name(o.reg) if o.type == 1 else '?')
        out.append(s + ' ' + ','.join(ops))
    return out

pydir, oldkc, oldnm, newkc, newnm, entry, outjson = sys.argv[1:8]
O = load(oldkc, oldnm, entry); N = load(newkc, newnm, entry)
of, nf = O[2], N[2]
changed, same = [], 0
for s in sorted(set(of) & set(nf)):
    x = norm(O[0], O[1], O[3], *of[s]); y = norm(N[0], N[1], N[3], *nf[s])
    if x == y: same += 1
    else: changed.append(s)
res = dict(entry=entry, same=same, changed=changed, only_old=sorted(set(of) - set(nf)), only_new=sorted(set(nf) - set(of)))
json.dump(res, open(outjson, 'w'), indent=1)
print(entry, 'functions same', same, 'changed', len(changed), 'only old', len(res['only_old']), 'only new', len(res['only_new']))
