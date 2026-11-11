import json,datetime,re,sys,pickle,os
if not os.path.exists('all.pkl'):
    o=json.load(open('all.json'));pickle.dump(o,open('all.pkl','wb'))
else:o=pickle.load(open('all.pkl','rb'))
spec=re.compile(r'%(?:\{[^}]*\})?[-+ #0]*\d*(?:\.\d+|\.\*)?(?:hh|h|ll|l|z|q|t|j)?[a-zA-Z@%]')
def render(e):
    f=e['fmt'] or '?fmt@%x'%e['loc'];a=list(e['args'])
    def r(m):
        if m.group(0)=='%%':return '%'
        if not a:return m.group(0)
        v=a.pop(0)
        if isinstance(v,int) and ('x' in m.group(0) or 'p' in m.group(0)):return hex(v)
        return str(v)
    return spec.sub(r,f)
def T(s):
    return datetime.datetime.strptime('2026-11-02 '+s,'%Y-%m-%d %H:%M:%S.%f').timestamp()
def win(a,b,procs=None,pat=None,lim=400,w=240):
    a,b=T(a),T(b);n=0
    for e in o:
        if not a<=e['t']<=b:continue
        if procs and e['proc'] not in procs:continue
        s=render(e).replace('\n',' ')
        if pat and not re.search(pat,s,re.I):continue
        print(datetime.datetime.fromtimestamp(e['t']).strftime('%H:%M:%S.%f')[:-3],e['proc'],s[:w]);n+=1
        if n>=lim:print('...');break
    print('n',n)
