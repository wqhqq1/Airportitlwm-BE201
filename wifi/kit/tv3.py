"""Read-only minimal tracev3 reader for one local iPhone archive."""
import struct,ctypes,os,glob,sys,json,bisect
lib=ctypes.CDLL('/usr/lib/libcompression.dylib')
def lz4(src,size):
    d=ctypes.create_string_buffer(size)
    n=lib.compression_decode_buffer(d,ctypes.c_size_t(size),src,ctypes.c_size_t(len(src)),None,ctypes.c_int(0x101))
    return d.raw[:n]
A=sys.argv[1]
info=None
import plistlib
info=plistlib.load(open(A+'/Info.plist','rb'))
end=info['EndTimeRef'];ECT,EW=end['ContinuousTime'],end['WallTime']
def wall(ct):return (EW-(ECT-ct)*125/3)/1e9
# -- format strings
class UT:
    def __init__(s,p):
        b=open(p,'rb').read();s.ok=False
        if b[:4]!=b'\x99\x88\x77\x66':return
        n=struct.unpack_from('<I',b,12)[0];s.r=[];o=16;off=16+n*8;
        for i in range(n):
            a,sz=struct.unpack_from('<II',b,o);o+=8;s.r.append((a,sz,off));off+=sz
        s.b=b;s.ok=True;s.path=b[off:].split(b'\0')[0].decode('utf8','replace')
    def fmt(s,loc):
        for a,sz,off in s.r:
            if a<=loc<a+sz:
                e=s.b.find(b'\0',off+loc-a);return s.b[off+loc-a:e].decode('utf8','replace')
uts={}
def ut(u):
    u=u.upper()
    if u not in uts:
        p=f'{A}/{u[:2]}/{u[2:]}';uts[u]=UT(p) if os.path.exists(p) else None
    return uts[u]
class DSC:
    def __init__(s,p):
        b=open(p,'rb').read();s.b=b;s.ok=b[:4]==b'hcsd'
        if not s.ok:return
        maj,mino,nr,nu=struct.unpack_from('<HHII',b,4);s.maj=maj;o=16;s.r=[]
        for i in range(nr):
            if maj>=2:
                ui,_=struct.unpack_from('<HH',b,o) if False else (0,0)
                off,dat,size,ui=struct.unpack_from('<QIIQ',b,o)[:4] if False else (0,0,0,0)
            s_=struct.unpack_from('<QIIQ',b,o) if maj>=2 else None
            if maj>=2:
                ro,doff,sz=struct.unpack_from('<QII',b,o);ui=struct.unpack_from('<Q',b,o+16)[0]&0xffff;o+=24
            else:
                ui,_,doff,ro,sz=struct.unpack_from('<HHIII',b,o);o+=16
            s.r.append((ro,sz,doff))
        s.r.sort();s.k=[x[0] for x in s.r]
    def fmt(s,loc):
        i=bisect.bisect_right(s.k,loc)-1
        if i<0:return None
        ro,sz,doff=s.r[i]
        if loc>=ro+sz:return None
        e=s.b.find(b'\0',doff+loc-ro);return s.b[doff+loc-ro:e].decode('utf8','replace')
dscs={}
def dsc(u):
    u=u.upper()
    if u not in dscs:
        p=f'{A}/dsc/{u}';dscs[u]=DSC(p) if os.path.exists(p) else None
    return dscs[u]
# -- parser
def hexu(b):return b.hex().upper()
def parse_catalog(b):
    so,po,np_,co,cc=struct.unpack_from('<HHHHH',b,0)
    base=24
    uuids=[hexu(b[base+i:base+i+16]) for i in range(0,so,16)]
    subs=b[base+so:base+po]
    def sstr(o):
        e=subs.find(b'\0',o);return subs[o:e].decode('utf8','replace')
    o=base+po;procs={}
    for _ in range(np_):
        idx,_u,mi,di=struct.unpack_from('<HHHH',b,o);fp,sp,pid,euid=struct.unpack_from('<QIII',b,o+8);o+=8+8+4+4+4
        o+=4;nu=struct.unpack_from('<I',b,o)[0];o+=8
        o+=nu*16
        ns=struct.unpack_from('<I',b,o)[0];o+=8
        sm={}
        for i in range(ns):
            sid,so1,co1=struct.unpack_from('<HHH',b,o);o+=6;sm[sid]=(sstr(so1),sstr(co1))
        o=(o+7)&~7
        procs[(fp,sp)]=dict(pid=pid,main=uuids[mi] if mi<len(uuids) else None,dsc=uuids[di] if di<len(uuids) else None,subs=sm,uuids=uuids)
    return procs
def fire(b,procs,out,stats):
    fp,sp=struct.unpack_from('<QI',b,0);ttl=b[12]
    pubsz,privoff=struct.unpack_from('<HH',b,16)
    bct=struct.unpack_from('<Q',b,24)[0]
    p=procs.get((fp,sp));off=32;end_=16+pubsz+16 if False else 32+pubsz-16
    priv=b[privoff+16:] if False else None
    while off+24<=len(b) and off<32+pubsz-16:
        at,lt,fl,loc=struct.unpack_from('<BBHI',b,off);tid=struct.unpack_from('<Q',b,off+8)[0]
        d1,d2,ds=struct.unpack_from('<IHH',b,off+16)
        if at==0:break
        data=b[off+24:off+24+ds];ct=bct+(d1|(d2<<32))
        off=(off+24+ds+7)&~7
        stats[at]=stats.get(at,0)+1
        if at!=4:continue
        try:out.append(entry(data,fl,loc,lt,ct,tid,p))
        except Exception as e:stats['err']=stats.get('err',0)+1
def entry(d,fl,loc,lt,ct,tid,p):
    o=0
    if fl&1:o+=8
    if fl&0x100:o+=4
    o+=4
    fk=fl&0xe;large=None;uu=None;alt=None
    # per libtrace flag layout
    if fl&0x20:large=struct.unpack_from('<H',d,o)[0];o+=2
    if fk==0xc:large=struct.unpack_from('<H',d,o)[0];o+=2
    elif fk==0x8:alt=struct.unpack_from('<H',d,o)[0];o+=2
    elif fk==0xa:uu=hexu(d[o:o+16]);o+=16
    sub=None
    if fl&0x200:sub=struct.unpack_from('<H',d,o)[0];o+=2
    if fl&0x400:o+=1
    if fl&0x800:o+=2
    f=None
    if p:
        if fk==0x2:
            u=ut(p['main']);f=u.fmt(loc) if u and u.ok else None
        elif fk in(0x4,0xc):
            x=dsc(p['dsc']);l=loc|((large or 0)<<31 if fk==4 and False else 0)
            if large:l=loc+(large<<32) if False else (large*(1<<28)*0+loc)
            if x and x.ok:f=x.fmt(loc if not large else (large<<31)|loc)
        elif fk==0xa and uu:
            u=ut(uu);f=u.fmt(loc) if u and u.ok else None
        elif fk==0x8 and alt is not None and alt<len(p['uuids']):
            u=ut(p['uuids'][alt]);f=u.fmt(loc) if u and u.ok else None
    args=[]
    if o+2<=len(d):
        o+=1;n=d[o];o+=1;region=[];vals=[]
        for i in range(n):
            t,s=d[o],d[o+1];o+=2
            if t in(0x10,0x12):
                o+=s;continue
            if t in(0x20,0x21,0x22,0x25,0x40,0x41,0x42,0x30,0x31,0x32,0xf2,0x35,0x81,0xf1):
                so,sl=struct.unpack_from('<HH',d,o);o+=4;vals.append(('s',t,so,sl))
            elif t in(0,2):
                vals.append(('n',int.from_bytes(d[o:o+s],'little')));o+=s
            else:
                vals.append(('n?',t));o+=s
        reg=d[o:]
        for v in vals:
            if v[0]=='s':
                if v[1]&1 or v[1]==0x25: args.append('<private>')
                else:
                    x=reg[v[2]:v[2]+v[3]]
                    args.append(x.rstrip(b'\0').decode('utf8','replace') if v[1] not in(0x30,0x31,0x32,0xf2) else x.hex())
            elif v[0]=='n':args.append(v[1])
            else:args.append('?')
    sn=p['subs'].get(sub) if (p and sub) else None
    nm=None
    if p:
        u=ut(p['main']);nm=u.path.split('/')[-1] if u and u.ok else p['main']
    return dict(t=wall(ct),pid=p and p['pid'],proc=nm,lt=lt,sub=sn,fmt=f,args=args,loc=loc,fk=fk)
def read(path,out,stats):
    b=open(path,'rb').read();o=0;procs={}
    while o+16<=len(b):
        tag,sub,sz=struct.unpack_from('<IIQ',b,o);body=b[o+16:o+16+sz];o=(o+16+sz+7)&~7
        if tag==0x600b:
            try:procs=parse_catalog(body)
            except Exception as e:stats['caterr']=str(e);procs={}
        elif tag==0x600d:
            if body[:4]!=b'bv41':
                stats['nonbv41']=stats.get('nonbv41',0)+1;continue
            usz,bsz=struct.unpack_from('<II',body,4);c=lz4(body[12:12+bsz],usz);q=0
            while q+16<=len(c):
                t,s2,z=struct.unpack_from('<IIQ',c,q);x=c[q+16:q+16+z];q=(q+16+z+7)&~7
                stats[hex(t)]=stats.get(hex(t),0)+1
                if t==0x6001:fire(x,procs,out,stats)
if __name__=='__main__':
    out=[];stats={}
    for f in sorted(glob.glob(A+'/Persist/*.tracev3')+glob.glob(A+'/Special/*.tracev3')+glob.glob(A+'/logdata.LiveData.tracev3')):
        read(f,out,stats)
    out.sort(key=lambda e:e['t'])
    json.dump(out,open(sys.argv[2],'w'))
    print(stats,len(out))
    if out:
        import datetime
        print(datetime.datetime.fromtimestamp(out[0]['t']),datetime.datetime.fromtimestamp(out[-1]['t']))
        print('fmt resolved',sum(1 for e in out if e['fmt']),'of',len(out))
        import collections
        print(collections.Counter(e['proc'] for e in out).most_common(25))
