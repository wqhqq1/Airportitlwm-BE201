import sys, re
args = sys.argv[1:7]; names = sys.argv[7:]
sys.argv = [sys.argv[0]] + args + ['x']
exec(open(sys.argv[0].replace('disp.py','fndiff.py')).read().split("pydir, oldkc")[0])
pydir, oldkc, oldnm, newkc, newnm, entry = args
O = load(oldkc, oldnm, entry); N = load(newkc, newnm, entry)
pat = re.compile(r'\[(r\w+|e\w+)\+(\w*)\*\d\+(-?0x[0-9a-f]+)\]')
for s in names:
    a = {m[3] for l in norm(O[0], O[1], O[3], *O[2][s]) for m in pat.finditer(l) if m[1] not in ('rsp', 'rbp')}
    b = {m[3] for l in norm(N[0], N[1], N[3], *N[2][s]) for m in pat.finditer(l) if m[1] not in ('rsp', 'rbp')}
    print(s[:60], 'offsets old', len(a), 'new', len(b), 'only old', sorted(a - b), 'only new', sorted(b - a))
