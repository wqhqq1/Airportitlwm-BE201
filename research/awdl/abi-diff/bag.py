import sys, re, collections
args = sys.argv[1:7]; names = sys.argv[7:]
sys.argv = [sys.argv[0]] + args + ['x']
exec(open(sys.argv[0].replace('bag.py','fndiff.py')).read().split("pydir, oldkc")[0])
pydir, oldkc, oldnm, newkc, newnm, entry = args
O = load(oldkc, oldnm, entry); N = load(newkc, newnm, entry)
def strip(l):
    l = re.sub(r'\[[^\]+]*\+0x[0-9a-f]+\]|\[(_\.str|l_\.str|ltmp|___FUNCTION__|_\.memset)[^\]]*\]', '[DATA]', l)
    l = re.sub(r'\bL\d+\b', 'L', l); l = re.sub(r'kalloc_type_view_\d+', 'KTV', l)
    l = re.sub(r'^(mov|movabs) (r8d|r9d|ecx|edx|esi),0x[0-9a-f]{3,4}$', r'\1 \2,LINE', l)
    return l
for s in names:
    x = collections.Counter(strip(l) for l in norm(O[0], O[1], O[3], *O[2][s])); y = collections.Counter(strip(l) for l in norm(N[0], N[1], N[3], *N[2][s]))
    print('=====', s, 'removed', sum((x - y).values()), 'added', sum((y - x).values()))
    for k, v in (x - y).items(): print('  -', v, k)
    for k, v in (y - x).items(): print('  +', v, k)
