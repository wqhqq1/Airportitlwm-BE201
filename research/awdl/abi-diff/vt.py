import sys, struct, bisect, re
args = sys.argv[1:7]
sys.argv = [sys.argv[0]] + args + ['x']
exec(open(sys.argv[0].replace('vt.py','fndiff.py')).read().split("pydir, oldkc")[0])
pydir, oldkc, oldnm, newkc, newnm, entry = args
def tables(kc, nmf):
    syms, order, funcs, read = load(kc, nmf, entry)
    names = {}
    for a, s in syms.items(): names.setdefault(a, s)
    out = {}
    for a, s in syms.items():
        if not s.startswith('__ZTV') or not ('IO80211' in s or 'AWDL' in s or 'Skywalk' in s or 'WCL' in s): continue
        i = bisect.bisect_right(order, a); end = order[i] if i < len(order) else a + 8
        raw = read(a, min(end - a, 0x2000)); ents = []
        for k in range(0, len(raw) // 8 * 8, 8):
            v = struct.unpack_from('<Q', raw, k)[0]
            t = v if v in syms else 0xffffff8000100000 + (v & 0x3fffffff)
            ents.append(syms.get(t, 'null' if v == 0 else '?'))
        out[s] = ents
    return out
a = tables(oldkc, oldnm); b = tables(newkc, newnm)
diff = 0
for s in sorted(set(a) | set(b)):
    if s not in a or s not in b: print('only', 'old' if s in a else 'new', s); diff += 1; continue
    if a[s] != b[s]:
        diff += 1
        n = min(len(a[s]), len(b[s]))
        bad = [(i, a[s][i], b[s][i]) for i in range(n) if a[s][i] != b[s][i]][:4]
        print('DIFF', s, len(a[s]), '->', len(b[s]), bad)
print('vtables', len(a), 'old', len(b), 'new', 'different', diff)
for s in ['__ZTV23IO80211SkywalkInterface', '__ZTV23IO80211VirtualInterface', '__ZTV19IO80211AWDLProtocol', '__ZTV22IO80211AWDLPeerManager']:
    if s in b:
        e = b[s]; print(s, len(e), 'named', sum(1 for x in e if x not in ('?', 'null')), 'unknown', e.count('?'), e[2:5])
