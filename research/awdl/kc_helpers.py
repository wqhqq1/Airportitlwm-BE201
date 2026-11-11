"""Reverse helpers over inspect_kc.KC: exec this file from work/awdl. Read only."""
import sys,pathlib,re,struct,bisect,subprocess
base=pathlib.Path(__file__).resolve().parent
src=(base/'inspect_kc.py').read_text().rsplit('\nif __name__',1)[0]
src=src.split("for s in sys.argv[1:]")[0]
ns={'__file__':str(base/'inspect_kc.py')}
exec(src,ns)
kc=ns['KC']();Cs=ns['Cs'];CS_ARCH_X86=ns['CS_ARCH_X86'];CS_MODE_64=ns['CS_MODE_64']
def demangle(names):
    return subprocess.run(['/usr/bin/c++filt','-_'],input='\n'.join(names),capture_output=True,text=True).stdout.splitlines()
def owner(a):
    i=bisect.bisect_right(kc.ordered,a)-1
    return kc.sym(kc.ordered[i]),a-kc.ordered[i]
def oname(a):
    o=owner(a)[0];return demangle([o.split('|')[0]])[0] if o.startswith('__') else o
def xrefs(target_names,lo=0xffffff8002110000,hi=0xffffff80023bc000):
    targets={kc.symbols[n]:n for n in target_names};out={}
    for addr,size,off in kc.segments:
        s=max(lo,addr);e=min(hi,addr+size)
        if s>=e: continue
        data=kc.b[off+s-addr:off+e-addr]
        for i in range(len(data)-5):
            if data[i] in (0xe8,0xe9):
                t=s+i+5+struct.unpack_from('<i',data,i+1)[0]
                if t in targets: out.setdefault(targets[t],[]).append(s+i)
    return out
def fn(part,cls='22IO80211AWDLPeerManager'):
    return [n for n in kc.symbols if cls in n and part in n]
def fdis(s,maxn=4000):
    a=kc.symbols[s] if isinstance(s,str) else s
    i=bisect.bisect_right(kc.ordered,a)
    end=kc.ordered[i] if i<len(kc.ordered) else a+maxn
    n=min(end-a,maxn);out=[]
    for ins in Cs(CS_ARCH_X86,CS_MODE_64).disasm(kc.read(a,n),a):
        annot=''
        if ins.mnemonic in ['call','jmp'] and ins.op_str.startswith('0x'): annot=kc.sym(int(ins.op_str,16))
        m=re.search(r'rip ([+-]) (0x[0-9a-f]+)',ins.op_str)
        if m:
            t=ins.address+ins.size+(int(m.group(2),16) if m.group(1)=='+' else -int(m.group(2),16));annot=hex(t)
            try:
                c=kc.read(t,64).split(b'\0')[0]
                if len(c)>3 and all(32<=x<127 for x in c): annot='"'+c.decode()+'"'
            except Exception: pass
        out.append((ins.address,ins.mnemonic,ins.op_str,annot))
    return out
def show(s,maxn=4000,filt=None):
    for a,m,o,an in fdis(s,maxn):
        if filt is None or filt(m,o,an): print(hex(a)[-6:],m,o,an)
def slot_calls(off):
    pats=[bytes([0xff,0x90+r])+struct.pack('<I',off) for r in range(8)]+[bytes([0xff,0xa0+r])+struct.pack('<I',off) for r in range(8)];res=[]
    for addr,size,o in kc.segments:
        data=kc.b[o:o+size]
        for p in pats:
            i=0
            while True:
                i=data.find(p,i)
                if i<0: break
                res.append(addr+i);i+=1
    return sorted(set(res))
def disp_refs(disp,lo=0xffffff8002146ecc,hi=0xffffff80023bc000,writes_only=True):
    addr,size,off=[x for x in kc.segments if x[0]<=lo<x[0]+x[1]][0];hi=min(hi,addr+size)
    code=kc.b[off+lo-addr:off+hi-addr];md=Cs(CS_ARCH_X86,CS_MODE_64);pat=struct.pack('<I',disp);pos=0;hits={};hx=hex(disp)
    while True:
        i=code.find(pat,pos)
        if i<0: break
        pos=i+1
        for back in range(2,9):
            ins=list(md.disasm(code[i-back:i-back+12],lo+i-back,count=1))
            if ins and hx in ins[0].op_str and ins[0].address+ins[0].size>=lo+i+4:
                if (not writes_only) or (ins[0].mnemonic in('or','and','mov','xor','inc','dec','add','sub') and ins[0].op_str.split(',')[0].strip().endswith(']')):
                    hits.setdefault(oname(ins[0].address),[]).append((hex(ins[0].address)[-6:],ins[0].mnemonic,ins[0].op_str))
                break
    return hits
IOTAB=0xffffff8002195fcd+0x257203
def ioname(i):
    try: return kc.read(kc.ptr(struct.unpack('<Q',kc.read(IOTAB+i*8,8))[0]),64).split(b'\0')[0].decode(errors='replace')
    except Exception: return '?'
