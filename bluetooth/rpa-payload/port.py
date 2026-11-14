"""Port the recent-RPA routing patch (-be201rparoute) to one bluetoothd build (BlueToolFixup 2.7.13).

    python3 port.py BUILD [bluetoothd]   locate everything in that bluetoothd (fat or thin; default /usr/sbin/bluetoothd),
                                         build the routing module for it into builds/BUILD/, then regenerate the header
    python3 port.py --header             only regenerate AuthenticatedRPAPatch.hpp (here and in ../bluetoolfixup)

Offline only: reads files, never touches the system or a running process.

How each native piece is found. The references are the 24G824 (15.7.8) pages kept in this folder, which hold the code
the patch was first written against (scan-page-original.bin, filter-page-original.bin):
  * call sites and the two log-only blocks reused for the guards: a window of 24G824 instructions around each one,
    masked like ../bluetoolfixup/make_masks.py (rel32 and RIP disp32 are wildcards, everything else exact), must
    match exactly once in the new __text;
  * the resolver, the set-from-array builder and the set insert: the targets of those call sites;
  * OI_Time_Now: the OSAL function at a fixed distance below the allocator the scan code calls, accepted only if
    its body has the OI_TIME shape (stores dword [rbx] seconds and word [rbx+4] milliseconds, then returns);
  * _os_log_impl / __os_log_default: the __got binds (dyld_info), and the __stubs entry that jumps through the first;
  * the format: an existing "%{public}s" string in __oslogstring;
  * payload: zero padding at the end of __TEXT, after its last section; state: zero-fill at the end of __DATA,
    after its last section.
Then the safety checks that the 24G824 port made by hand: every entry is in LC_FUNCTION_STARTS, the call site and
its guard share one 4 KiB page, a guard block is not entered by fall-through and no branch anywhere in __text
lands inside the bytes that are overwritten, the payload and state are outside every section.
If anything does not hold, it stops; nothing is written for that build."""
from pathlib import Path
import hashlib, json, re, struct, subprocess, sys

W = Path(__file__).resolve().parent
ROOT = W.parents[1]
sys.path.insert(0, str(ROOT/'deps/python'))  # capstone 5.0.9
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP

BASE = 0x100000000
PAGE = 4096
GUARD = 34          # cmp/jne, cmp/jne, jmp module entry (29 bytes) + jmp original (5 bytes)
STATE_SIZE = 232
md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True

# 24G824 reference pages: vm address of the page, and the windows used as anchors (page offsets, instruction-aligned).
REF = {'scan': ('scan-page-original.bin', 0x1001f1000), 'filter': ('filter-page-original.bin', 0x10068b000)}
ANCHORS = {
    # name: (page, window start, window end, offset of the call or block inside the page)
    'scan_call':    ('scan', 0x9c3, 0x9f6, 0x9e1),     # RPA bits test, resolver call, status/found checks
    'scan_block':   ('scan', 0xc84, 0xcea, 0xcab),     # tail of the list walk, then a log-only error block
    'build_call':   ('filter', 0x059, 0x087, 0x079),   # single-address path: set from an array
    'multi_call1':  ('filter', 0x25a, 0x278, 0x26a),   # multi-key path: set insert
    'multi_call2':  ('filter', 0x31a, 0x341, 0x333),   # multi-key path, second insert
    'filter_block': ('filter', 0x3b4, 0x40d, 0x3c4),   # log-only error block before the shared cleanup
}
# OI_Time_Now sits this far below the OSAL allocator in the 24G824 OSAL object (0x1000d6f6d - 0x1000d5be3).
ALLOC_TO_TIME = 0x138a
ALLOC_CALL = ('scan', 0xb38)  # `mov edi, 0x50; call allocator` in the scan page


class Image:
    """x86_64 slice of a fat or thin bluetoothd."""
    def __init__(self, path):
        self.path = Path(path); raw = self.path.read_bytes(); self.fat = 0
        if struct.unpack_from('>I', raw, 0)[0] == 0xcafebabe:
            for i in range(struct.unpack_from('>I', raw, 4)[0]):
                cpu, sub, off, size, al = struct.unpack_from('>IIIII', raw, 8 + 20 * i)
                if cpu == 0x01000007: self.fat = off; raw = raw[off:off + size]; break
            else: raise SystemExit(f'{path}: no x86_64 slice')
        b = self.b = raw
        assert struct.unpack_from('<I', b, 0)[0] == 0xfeedfacf and struct.unpack_from('<I', b, 4)[0] == 0x01000007
        self.segments, self.sections = {}, []; p = 32; fs_off = fs_size = None; dic = (0, 0)
        for _ in range(struct.unpack_from('<I', b, 16)[0]):
            cmd, n = struct.unpack_from('<II', b, p)
            if cmd == 0x19:
                name = b[p + 8:p + 24].rstrip(b'\0').decode(); vm, vs, fo, fsz = struct.unpack_from('<QQQQ', b, p + 24)
                self.segments[name] = (vm, vs, fo, fsz)
                for j in range(struct.unpack_from('<I', b, p + 64)[0]):
                    q = p + 72 + 80 * j; sa, sz = struct.unpack_from('<QQ', b, q + 32); so, = struct.unpack_from('<I', b, q + 48)
                    self.sections.append((name, b[q:q + 16].rstrip(b'\0').decode(), sa, sz, so))
            elif cmd == 0x26: fs_off, fs_size = struct.unpack_from('<II', b, p + 8)
            elif cmd == 0x29: dic = struct.unpack_from('<II', b, p + 8)
            p += n
        assert self.segments['__TEXT'][0] == BASE and self.segments['__TEXT'][2] == 0
        self.functions = []; a = BASE; p = fs_off
        while p < fs_off + fs_size:
            v = s = 0
            while True:
                c = b[p]; p += 1; v |= (c & 0x7f) << s; s += 7
                if c < 0x80: break
            if not v: break
            a += v; self.functions.append(a)
        self.function_set = set(self.functions)
        self.data_in_code = [(BASE + struct.unpack_from('<I', b, dic[0] + 8 * i)[0], struct.unpack_from('<H', b, dic[0] + 8 * i + 4)[0])
                             for i in range(dic[1] // 8)]
        self.text = self.section('__TEXT', '__text')

    def section(self, seg, name):
        return next((a, a + s, o) for g, n, a, s, o in self.sections if g == seg and n == name)

    def off(self, vm):
        for vm0, vs, fo, fsz in self.segments.values():
            if vm0 <= vm < vm0 + fsz: return fo + vm - vm0
        raise ValueError(hex(vm))

    def read(self, vm, n): o = self.off(vm); return self.b[o:o + n]

    def call_target(self, at):
        assert self.b[self.off(at)] == 0xe8, f'{at:#x} is not a call rel32'
        return at + 5 + struct.unpack_from('<i', self.b, self.off(at) + 1)[0]

    def function(self, at):
        """[start, end) of the function containing `at` (LC_FUNCTION_STARTS)."""
        import bisect
        i = bisect.bisect_right(self.functions, at) - 1; assert i >= 0
        end = self.functions[i + 1] if i + 1 < len(self.functions) else self.text[1]
        return self.functions[i], end

    def instructions(self, start, end):
        """Linear sweep, skipping data-in-code ranges; must decode with no gaps."""
        out = []; at = start
        holes = sorted((a, a + n) for a, n in self.data_in_code if start <= a < end)
        for hs, he in holes + [(end, end)]:
            for i in md.disasm(self.read(at, hs - at), at):
                out.append(i); at = i.address + i.size
            assert at == hs, f'{self.path.name}: decode gap at {at:#x}'
            at = he
        return out


def mask(code, base):
    m = bytearray(b'\xff' * len(code)); end = 0
    for i in md.disasm(code, base):
        o = i.address - base; end = o + i.size
        if i.bytes[0] in (0xe8, 0xe9): m[o + 1:o + 5] = bytes(4)
        if len(i.bytes) == 6 and i.bytes[0] == 0x0f and 0x80 <= i.bytes[1] <= 0x8f: m[o + 2:o + 6] = bytes(4)
        for op in i.operands:
            if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP: m[o + i.disp_offset:o + i.disp_offset + 4] = bytes(4)
    assert end == len(code), 'reference window is not instruction-aligned'
    return bytes(m)


def find_masked(img, code, m):
    lo, hi, _ = img.text; t0 = img.off(lo); t1 = img.off(hi)
    runs = []; k = 0
    while k < len(code):
        if m[k]:
            j = k
            while j < len(code) and m[j]: j += 1
            runs.append((j - k, k)); k = j
        else: k += 1
    n, a = max(runs); needle = code[a:a + n]; hits = []; i = t0
    while (j := img.b.find(needle, i, t1)) >= 0:
        s = j - a; i = j + 1
        if s >= t0 and s + len(code) <= t1 and all(img.b[s + k] == code[k] for k in range(len(code)) if m[k]):
            hits.append(BASE + s)
    return hits


def anchor(img, name):
    page, s, e, at = ANCHORS[name]; ref, vm = REF[page]; code = (W/ref).read_bytes()[s:e]
    hits = find_masked(img, code, mask(code, vm + s))
    if len(hits) != 1: raise SystemExit(f'{name}: {len(hits)} matches of the 24G824 context (need exactly 1)')
    return hits[0] + (at - s)


def branch_targets(img):
    """Every rel8/rel32 branch or call target in __text, by linear sweep of every function, plus every
    data-in-code entry decoded as a jump-table offset. Over-approximates, which only makes the check stricter."""
    targets = set(); lite = Cs(CS_ARCH_X86, CS_MODE_64)
    for k, f in enumerate(img.functions):
        end = img.functions[k + 1] if k + 1 < len(img.functions) else img.text[1]
        if not (img.text[0] <= f < img.text[1]): continue
        for a, n, mn, ops in lite.disasm_lite(img.read(f, end - f), f):
            if (mn[0] == 'j' or mn == 'call' or mn.startswith('loop')) and ops.startswith('0x'): targets.add(int(ops, 16))
    for a, n in img.data_in_code:
        for q in range(a, a + n - 3, 4): targets.add(a + struct.unpack_from('<i', img.b, img.off(q))[0])
    return targets


def guard_block(img, at, need, targets):
    """A log-only block at `at`: not entered by fall-through, its first conditional branch skips the whole block,
    and no branch lands inside the bytes [at+1, at+need) that will be overwritten."""
    f0, f1 = img.function(at); ins = img.instructions(f0, f1); idx = next(k for k, i in enumerate(ins) if i.address == at)
    prev = ins[idx - 1]
    assert prev.mnemonic in ('jmp', 'ret') or prev.mnemonic.startswith('ud'), f'{at:#x}: entered by fall-through ({prev.mnemonic})'
    skip = next(i for i in ins[idx:] if i.mnemonic == 'je').operands[0].imm
    assert skip - at >= need, f'{at:#x}: block is {skip - at} bytes, need {need}'
    inside = sorted(t for t in targets if at < t < at + need)
    assert not inside, f'{at:#x}: branch targets inside the block: {[hex(t) for t in inside]}'
    return skip


def rel(op, at, target): return op + struct.pack('<i', target - at - len(op) - 4)


def guard(at, entry, original, payload_vm, marker):
    # Called like the original; only tail-jumps, so the caller's ABI is untouched either way.
    code = bytearray(); fallback = at + 29
    for o in (0, 4):
        pos = at + len(code); code += b'\x81\x3d' + struct.pack('<i', payload_vm + o - pos - 10) + marker[o:o + 4]
        pos = at + len(code); code += b'\x75' + struct.pack('b', fallback - pos - 2)
    code += rel(b'\xe9', at + len(code), entry); assert len(code) == 29
    code += rel(b'\xe9', at + len(code), original); assert len(code) == GUARD
    return bytes(code)


def dyld_got(img, symbol):
    out = subprocess.run(['xcrun', 'dyld_info', '-arch', 'x86_64', '-fixups', str(img.path)], capture_output=True, text=True, check=True).stdout
    hits = [int(m.group(1), 16) for m in re.finditer(r'__got\s+0x([0-9A-Fa-f]+)\s+bind\s+\S+/' + re.escape(symbol) + r'$', out, re.M)]
    if len(hits) != 1: raise SystemExit(f'{symbol}: {len(hits)} __got binds')
    return hits[0]


def stub_for(img, got):
    lo, hi, _ = img.section('__TEXT', '__stubs'); hits = []
    for a in range(lo, hi, 6):
        c = img.read(a, 6)
        if c[:2] == b'\xff\x25' and a + 6 + struct.unpack_from('<i', c, 2)[0] == got: hits.append(a)
    if len(hits) != 1: raise SystemExit(f'stub for {got:#x}: {len(hits)} matches')
    return hits[0]


def oi_time_now(img, scan_call):
    alloc_site = scan_call + (ALLOC_CALL[1] - ANCHORS['scan_call'][3])
    assert img.read(alloc_site - 5, 5) == b'\xbf\x50\x00\x00\x00', 'allocator call context moved'
    t = img.call_target(alloc_site) - ALLOC_TO_TIME
    assert t in img.function_set, f'OI_Time_Now candidate {t:#x} is not a function start'
    f0, f1 = img.function(t); ins = img.instructions(f0, f1)
    ins = ins[:max(k for k, i in enumerate(ins) if i.mnemonic == 'ret') + 1]  # drop the alignment padding
    assert [i.mnemonic for i in ins[:4]] == ['push', 'mov', 'push', 'push'] and ins[3 + 1].op_str == 'rbx, rdi', 'prologue'
    tail = ins[-6:]
    shape = [(i.mnemonic, i.op_str) for i in tail]
    assert shape[0][0] == 'mov' and shape[0][1].startswith('word ptr [rbx + 4],'), shape
    assert shape[1][0] == 'mov' and shape[1][1].startswith('dword ptr [rbx],'), shape
    assert shape[-1][0] == 'ret', shape
    assert any(i.op_str == 'eax, edx, 0x3e8' for i in tail[-8:] + ins[-8:]), 'no millisecond split'
    return t


def free_tail(img, seg, need, align):
    vm, vs, fo, fsz = img.segments[seg]
    last = max(a + s for g, n, a, s, o in img.sections if g == seg)
    start = (last + align - 1) // align * align
    assert start + need <= vm + vs, f'{seg}: {vm + vs - start} bytes after the last section, need {need}'
    return start


def locate(img):
    r = {}
    r['scan_call'] = anchor(img, 'scan_call'); r['resolver'] = img.call_target(r['scan_call'])
    r['build_call'] = anchor(img, 'build_call'); r['build_filter'] = img.call_target(r['build_call'])
    r['multi_calls'] = [anchor(img, 'multi_call1'), anchor(img, 'multi_call2')]
    inserts = {img.call_target(a) for a in r['multi_calls']}; assert len(inserts) == 1, 'the two inserts differ'
    r['insert_multi'] = inserts.pop()
    r['scan_block'] = anchor(img, 'scan_block'); r['filter_block'] = anchor(img, 'filter_block')
    r['time_now'] = oi_time_now(img, r['scan_call'])
    for k in ('resolver', 'build_filter', 'insert_multi', 'time_now'):
        assert r[k] in img.function_set, f'{k} {r[k]:#x} is not a function start'
    r['log_default'] = dyld_got(img, '__os_log_default')
    r['log_impl'] = stub_for(img, dyld_got(img, '__os_log_impl'))
    # The 24G824 filter block ends in `call _os_log_impl`: same stub here, or the stub search is wrong.
    assert img.call_target(r['filter_block'] + (0x408 - 0x3c4)) == r['log_impl'], 'filter log call is not _os_log_impl'
    lo, hi, o = img.section('__TEXT', '__oslogstring'); blob = img.b[o:o + hi - lo]
    k = blob.find(b'\0%{public}s\0'); assert k >= 0, 'no "%{public}s" in __oslogstring'; r['format'] = lo + k + 1
    return r


def port(build, path):
    img = Image(path); r = locate(img)
    targets = branch_targets(img)
    scan_skip = guard_block(img, r['scan_block'], 5 + GUARD, targets)
    filter_skip = guard_block(img, r['filter_block'], 5 + 2 * GUARD, targets)
    page = lambda a: a & ~(PAGE - 1)
    assert page(r['scan_call']) == page(r['scan_block']) == page(r['scan_block'] + 5 + GUARD - 1), 'scan call/guard pages'
    for a in [r['build_call']] + r['multi_calls'] + [r['filter_block'] + 5 + 2 * GUARD - 1]:
        assert page(a) == page(r['filter_block']), 'filter call/guard pages'
    sys.path.insert(0, str(W)); import build as module
    payload_vm = free_tail(img, '__TEXT', 0x5f0, 16)
    state_vm = free_tail(img, '__DATA', STATE_SIZE, 256)
    assert state_vm >= img.segments['__DATA'][0] + img.segments['__DATA'][3], 'state must be zero-fill, past the file'
    defines = {'BE201_TIME_NOW': r['time_now'], 'BE201_LOG_IMPL': r['log_impl'], 'BE201_LOG_DEFAULT': r['log_default'],
               'BE201_FORMAT': r['format'], 'BE201_RESOLVER': r['resolver'], 'BE201_BUILD_FILTER': r['build_filter'],
               'BE201_INSERT_MULTI': r['insert_multi']}
    out = W/'builds'/build
    layout, payload = module.build(defines, payload_vm, state_vm, out)
    assert payload_vm + len(payload) <= img.segments['__TEXT'][0] + img.segments['__TEXT'][3]
    assert page(payload_vm) == page(payload_vm + len(payload) - 1), 'payload crosses a page'
    assert not any(img.read(payload_vm, len(payload))), 'payload area is not zero'
    entries = {k: payload_vm + 16 + v - layout['text']['vm'] for k, v in layout['entries'].items()}
    marker = payload[:8]; assert any(marker)
    # The same edits as the 24G824 port, at this build's addresses.
    edits = []
    sb, fb = r['scan_block'], r['filter_block']
    scan_guard, single_guard, multi_guard = sb + 5, fb + 5, fb + 5 + GUARD
    edits.append((sb, rel(b'\xe9', sb, scan_skip) + b'\x90' * (scan_skip - sb - 5)))
    edits.append((scan_guard, guard(scan_guard, entries['_BE201ResolveRPA'], r['resolver'], payload_vm, marker)))
    edits.append((r['scan_call'], rel(b'\xe8', r['scan_call'], scan_guard)))
    edits.append((fb, rel(b'\xe9', fb, filter_skip) + b'\x90' * (filter_skip - fb - 5)))
    edits.append((single_guard, guard(single_guard, entries['_BE201BuildFilter'], r['build_filter'], payload_vm, marker)))
    edits.append((multi_guard, guard(multi_guard, entries['_BE201InsertMulti'], r['insert_multi'], payload_vm, marker)))
    edits.append((r['build_call'], rel(b'\xe8', r['build_call'], single_guard)))
    for a in r['multi_calls']: edits.append((a, rel(b'\xe8', a, multi_guard)))
    edits.append((payload_vm, payload))
    pages = {}
    for at, data in edits:
        assert page(at) == page(at + len(data) - 1)
        pages.setdefault(page(at), []).append((at - page(at), data))
    roles = {page(r['scan_call']): ('Scan', 1), page(r['filter_block']): ('Filter', 2), page(payload_vm): ('Payload', 4)}
    assert len(roles) == 3, 'two roles share a page'
    rows = []
    for p in sorted(pages):
        before = img.read(p, PAGE); after = bytearray(before)
        for o, data in pages[p]: after[o:o + len(data)] = data
        name, kind = roles[p]; spans = []; i = 0
        while i < PAGE:
            if before[i] == after[i]: i += 1; continue
            s = i
            while i < PAGE and before[i] != after[i]: i += 1
            spans.append({'offset': s, 'bytes': after[s:i].hex()})
        (out/f'{name.lower()}-page-original.bin').write_bytes(before); (out/f'{name.lower()}-page-patched.bin').write_bytes(bytes(after))
        thin = img.off(p)
        rows.append({'name': name, 'kind': kind, 'vm': p, 'thin_page': thin, 'fat_page': img.fat + thin if img.fat else None,
                     'original_fnv': fnv(before), 'patched_fnv': fnv(after), 'original_sha256': hashlib.sha256(before).hexdigest(),
                     'patched_sha256': hashlib.sha256(bytes(after)).hexdigest(), 'spans': spans})
    info = {'build': build, 'source': str(Path(path)), 'x86_64_sha256': hashlib.sha256(img.b).hexdigest(), 'fat_offset': img.fat,
            'native': {k: (hex(v) if isinstance(v, int) else [hex(x) for x in v]) for k, v in r.items()},
            'guards': {'scan': hex(scan_guard), 'single': hex(single_guard), 'multi': hex(multi_guard),
                       'scan_skip': hex(scan_skip), 'filter_skip': hex(filter_skip)},
            'payload_vm': hex(payload_vm), 'payload_size': len(payload), 'state_vm': hex(state_vm), 'state_size': STATE_SIZE,
            'entries': {k: hex(v) for k, v in entries.items()}, 'marker': marker.hex(), 'code_sha256': layout['code_sha256'],
            'pages': rows}
    (out/'port.json').write_text(json.dumps(info, indent=2) + '\n')
    return info


def fnv(p):
    h = 14695981039346656037
    for x in p: h = ((h ^ x) * 1099511628211) & ((1 << 64) - 1)
    return h


def header():
    builds = sorted((json.loads(p.read_text()) for p in (W/'builds').glob('*/port.json')), key=lambda b: b['build'])
    h = ['// Generated by port.py from builds/*/port.json: recent-RPA routing pages, one block per bluetoothd build.',
         '// A page is patched only at its own file offset (thin or fat) and only if the whole page has the exact',
         '// original FNV-1a hash; a page already carrying the patch is reported, not patched twice.',
         '#pragma once', '#include <stdint.h>', '#include <stddef.h>',
         'struct BE201RPASpan {uint16_t offset, size; const uint8_t *bytes;};',
         'struct BE201RPAPage {uint64_t thin, fat, originalHash, patchedHash; unsigned kind; const BE201RPASpan *spans; unsigned count;};']
    table = []
    for b in builds:
        tag = 'k' + re.sub(r'\W', '', b['build'])
        h.append(f'// {b["build"]}: x86_64 sha256 {b["x86_64_sha256"]}')
        for row in b['pages']:
            names = []
            for k, s in enumerate(row['spans']):
                data = bytes.fromhex(s['bytes']); n = f'{tag}{row["name"]}{k}'; names.append((s['offset'], len(data), n))
                h.append(f'static const uint8_t {n}[] = {{' + ','.join(f'0x{x:02x}' for x in data) + '};')
            h.append(f'static const BE201RPASpan {tag}{row["name"]}Spans[] = {{' + ','.join(f'{{{o},{n},{v}}}' for o, n, v in names) + '};')
            fat = row['fat_page'] if row['fat_page'] is not None else row['thin_page']
            table.append(f' {{{row["thin_page"]}ULL,{fat}ULL,{row["original_fnv"]}ULL,{row["patched_fnv"]}ULL,{row["kind"]},'
                         f'{tag}{row["name"]}Spans,{len(names)}}}, // {b["build"]} {row["name"]}')
    h.append('static const BE201RPAPage kBE201RPAPages[] = {'); h += table; h.append('};')
    h.append('static constexpr unsigned kBE201RPAPageCount = sizeof(kBE201RPAPages)/sizeof(kBE201RPAPages[0]);')
    h.append('static inline uint64_t be201RPAPageHash(const uint8_t *p,size_t n){uint64_t h=14695981039346656037ULL;'
             'for(size_t i=0;i<n;i++)h=(h^p[i])*1099511628211ULL;return h;}')
    h.append('// Role of a page with this hash (1 scan, 2 filter, 4 payload), original or already patched; 0 if none.')
    h.append('static inline unsigned be201RPAKind(uint64_t h){for(unsigned i=0;i<kBE201RPAPageCount;i++)'
             'if(h==kBE201RPAPages[i].originalHash||h==kBE201RPAPages[i].patchedHash)return kBE201RPAPages[i].kind;return 0;}')
    h.append('// Returns the role on a patch, 128|role if the page is already patched, 0 if nothing matches.')
    h.append('static inline unsigned be201RPAApply(uint8_t *p,size_t n,uint64_t off){')
    h.append(' if(!p||n!=4096)return 0;const uint64_t h=be201RPAPageHash(p,n);')
    h.append(' for(unsigned i=0;i<kBE201RPAPageCount;i++){const BE201RPAPage &e=kBE201RPAPages[i];')
    h.append('  if(off!=e.thin&&off!=e.fat)continue;if(h==e.patchedHash)return 128|e.kind;if(h!=e.originalHash)continue;')
    h.append('  for(unsigned s=0;s<e.count;s++)for(unsigned k=0;k<e.spans[s].size;k++)p[e.spans[s].offset+k]=e.spans[s].bytes[k];')
    h.append('  return e.kind;}')
    h.append(' return 0;\n}')
    text = '\n'.join(h) + '\n'
    for d in (W, W.parent/'bluetoolfixup'): (d/'AuthenticatedRPAPatch.hpp').write_text(text)
    return builds


if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] != '--header':
        info = port(args[0], args[1] if len(args) > 1 else '/usr/sbin/bluetoothd')
        n = info['native']
        print(f"{info['build']}: resolver {n['resolver']} build {n['build_filter']} insert {n['insert_multi']} "
              f"time {n['time_now']} log {n['log_impl']}/{n['log_default']} format {n['format']}")
        print(f"  payload {info['payload_vm']} ({info['payload_size']} bytes) state {info['state_vm']} guards {info['guards']}")
        for row in info['pages']:
            print(f"  {row['name']:<8} page {row['vm']:#x} thin {row['thin_page']:#x} fat {row['fat_page']:#x} "
                  f"{sum(len(s['bytes']) // 2 for s in row['spans'])} bytes in {len(row['spans'])} spans")
    builds = header()
    print('AuthenticatedRPAPatch.hpp:', ', '.join(f"{b['build']} ({len(b['pages'])} pages)" for b in builds))
