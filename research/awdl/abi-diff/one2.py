import sys, difflib, re
args = sys.argv[1:7]; names = sys.argv[7:]
sys.argv = [sys.argv[0]] + args + ['x']
exec(open(sys.argv[0].replace('one2.py','fndiff.py')).read().split("pydir, oldkc")[0])
pydir, oldkc, oldnm, newkc, newnm, entry = args
O = load(oldkc, oldnm, entry); N = load(newkc, newnm, entry)
def strip(l):
    l = re.sub(r'\[[^\]+]*\+0x[0-9a-f]+\]|\[(_\.str|l_\.str|ltmp|___FUNCTION__|_\.memset)[^\]]*\]', '[DATA]', l)
    l = re.sub(r'\bL\d+\b', 'L', l)
    l = re.sub(r'kalloc_type_view_\d+', 'KTV', l)
    return l
for s in names:
    x = [strip(l) for l in norm(O[0], O[1], O[3], *O[2][s])]; y = [strip(l) for l in norm(N[0], N[1], N[3], *N[2][s])]
    print('=====', s)
    sm = difflib.SequenceMatcher(None, x, y, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal': continue
        a, b = x[i1:i2], y[j1:j2]
        if tag == 'replace' and len(a) == len(b) and all(re.match(r'^(mov|movabs) \w+,0x[0-9a-f]+$', p) and re.match(r'^(mov|movabs) \w+,0x[0-9a-f]+$', q) and p.split(',')[0] == q.split(',')[0] for p, q in zip(a, b)):
            continue
        print(f'-- {tag} old[{i1}:{i2}] new[{j1}:{j2}]')
        for l in a: print('  -', l)
        for l in b: print('  +', l)
