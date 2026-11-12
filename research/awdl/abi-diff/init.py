import sys, re
args = sys.argv[1:7]
sys.argv = [sys.argv[0]] + args + ['x']
exec(open(sys.argv[0].replace('init.py','fndiff.py')).read().split("pydir, oldkc")[0])
pydir, oldkc, oldnm, newkc, newnm, entry = args
O = load(oldkc, oldnm, entry); N = load(newkc, newnm, entry)
imm = re.compile(r',(0x[0-9a-f]+)$')
diff = 0; total = 0
for s in sorted(set(O[2]) & set(N[2])):
    if not s.startswith('__GLOBAL__sub_I_'): continue
    total += 1
    a = [m[1] for l in norm(O[0], O[1], O[3], *O[2][s]) if (m := imm.search(l))]
    b = [m[1] for l in norm(N[0], N[1], N[3], *N[2][s]) if (m := imm.search(l))]
    if a != b:
        diff += 1; print('DIFF', s, a[:10], b[:10])
print('static initializers', total, 'with different immediates (object sizes)', diff)
