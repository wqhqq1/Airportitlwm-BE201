import sys, json, re
args = sys.argv[1:7]; changed = json.load(open(sys.argv[7])); out = sys.argv[8]
changed = changed['changed'] if isinstance(changed, dict) else changed
sys.argv = [sys.argv[0]] + args + ['x']
exec(open(sys.argv[0].replace('classify.py','fndiff.py')).read().split("pydir, oldkc")[0])
pydir, oldkc, oldnm, newkc, newnm, entry = args
O = load(oldkc, oldnm, entry); N = load(newkc, newnm, entry)
strip = lambda l: re.sub(r'\[[^\]+]*\+0x[0-9a-f]+\]|\[(_\.str|l_\.str|ltmp|___FUNCTION__|_\.memset)[^\]]*\]', '[DATA]', l)
imm = re.compile(r'^(mov|movabs) (\w+),0x([0-9a-f]+)$')
res = {'line_only': [], 'real': {}}
for s in changed:
    x = [strip(l) for l in norm(O[0], O[1], O[3], *O[2][s])]; y = [strip(l) for l in norm(N[0], N[1], N[3], *N[2][s])]
    ok = len(x) == len(y)
    diffs = []
    if ok:
        for a, b in zip(x, y):
            if a == b: continue
            ma, mb = imm.match(a), imm.match(b)
            if ma and mb and ma[2] == mb[2] and abs(int(ma[3], 16) - int(mb[3], 16)) < 0x400 and int(ma[3], 16) >= 0x40:
                continue
            diffs.append((a, b))
    if ok and not diffs: res['line_only'].append(s)
    else: res['real'][s] = {'old_len': len(x), 'new_len': len(y), 'pairs': diffs[:12] if ok else None}
json.dump(res, open(out, 'w'), indent=1)
print('line-number only', len(res['line_only']), 'real', len(res['real']))
