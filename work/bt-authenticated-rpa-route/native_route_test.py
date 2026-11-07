"""Compiled module + genuine local native resolver/AH/scan/set code; synthetic keys only.
CommonCrypto AES is used offline. No system process/device/network modifications.
"""
from pathlib import Path
import sys,struct,json,ctypes,hashlib
W=Path(__file__).resolve().parent
sys.path.insert(0,str(W.parent/'bt-standard-privacy'))
from native_queue_test import Machine,B,HEAP,p64,u64
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_RIP,UC_X86_REG_RDX
P=json.loads((W/'patch-layout.json').read_text());L=P['layout'];BASE=0x100000000
cc=ctypes.CDLL('/usr/lib/libSystem.B.dylib').CCCrypt
cc.argtypes=[ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
def aes(key,plain):
 out=ctypes.create_string_buffer(16);moved=ctypes.c_size_t();a=ctypes.create_string_buffer(key);b=ctypes.create_string_buffer(plain)
 assert cc(0,0,2,a,16,None,b,16,out,16,ctypes.byref(moved))==0 and moved.value==16
 return out.raw
# FIPS-197 AES-128 known-answer test validates the real AES backend used below.
assert aes(bytes.fromhex('000102030405060708090a0b0c0d0e0f'),bytes.fromhex('00112233445566778899aabbccddeeff')).hex()=='69c4e0d86a7b0430d8cdb78070b4c55a'
class Scenario:
 def __init__(self,slide=0,payload=True):
  self.slide=s=slide;self.clock=[1000,0];self.observed=[];self.keys=[];self.stages=[]
  funcs=[0x1001f1948,0x1001f58d3,0x1001f5824,0x100135c54,0x10069214c,0x1002913fe,0x10068b008]
  allowed=[(a+s,e+s) for a,e in [B.function(f) for f in funcs]]+[(0x10068b3c9+s,0x10068b40d+s)]
  self.m=m=Machine(allowed,slide=s)
  if payload:m.allowed.append((L['payload_vm']+16+s,L['payload_vm']+L['payload_size']+s))
  for row in P['pages']:
   if row['name']=='Payload' and not payload:continue
   m.write(BASE+row['thin_page']+s,(W/(row['name'].lower()+'-page-patched.bin')).read_bytes())
  self.state=L['state_vm']+s;self.secret=[]
  self.getter=0
  m.write(0x1009db0b0+s,p64(HEAP+0x5200));m.stub(HEAP+0x5200,lambda obj,*a:obj)
  m.write(0x1009db0a8+s,p64(HEAP+0x5300));m.stub(HEAP+0x5300,lambda *a:0)
  m.stub(0x10068b0c8+s,lambda *a:0)
  def peer_getter(obj,name,prefer_raw,*a):
   assert prefer_raw==0,'obsolete force-raw hook conflicts with identity routing'
   return self.getter
  m.stub(0x10067ea3c+s,peer_getter)
  def encrypt(key,kn,plain,pn,out,on):
   assert kn==pn==on==16;m.write(out,aes(bytes(m.u.mem_read(key,16)),bytes(m.u.mem_read(plain,16))));return 0
  m.stub(0x1000d60e9+s,encrypt)
  m.stub(0x1007e4ea8+s,lambda *a:0)
  def log(dso,logger,kind,fmt,buf,n):
   assert dso==BASE+s and kind==0 and n==12 and fmt==0x1008ee330+s
   assert bytes(m.u.mem_read(fmt,11))==b'%{public}s\0'
   header,msg=struct.unpack('<IQ',m.u.mem_read(buf,12));assert header==0x08220102
   text=bytes(m.u.mem_read(msg,17));assert text[:15]==b'BE201RPA stage=' and text[16]==0
   stage=text[15]-48;assert 1<=stage<=5
   self.stages.append(stage);return 0
  m.stub(0x1007e47a6+s,log)
  m.stub(0x1000d5be3+s,lambda out,*a:m.write(out,struct.pack('<IH',*self.clock)) or 0)
  m.stub(0x10021a2c7+s,lambda *a:0)
  self.callback=HEAP+0x5000
  m.stub(self.callback,lambda report,*a:self.observed.append(bytes(m.u.mem_read(report+1,7))) or 0)
  m.write(0x100a5ef90+s,p64(self.callback))
  def inserted(tree,hint,key,value,*a):
   assert key==value;self.keys.append(u64(m.u.mem_read(key,8)));return 0
  m.stub(0x100304878+s,inserted)
  m.stub(0x1007e46f8+s,m.alloc)
  def linked(tree,parent,slot,node,*a):
   self.keys.append(u64(m.u.mem_read(node+0x20,8)));m.write(tree+8,p64(node));return 0
  m.stub(0x10002c442+s,linked)
  def secret_reads(u,access,a,n,val,ctx):
   pc=u.reg_read(UC_X86_REG_RIP)
   if L['payload_vm']+16+s<=pc<L['payload_vm']+L['payload_size']+s:
    assert not any(a<e and a+n>b for b,e in self.secret),'routing module read an IRK'
  def writes(u,access,a,n,val,ctx):
   pc=u.reg_read(UC_X86_REG_RIP)
   if L['payload_vm']+16+s<=pc<L['payload_vm']+L['payload_size']+s:
    assert self.state<=a and a+n<=self.state+L['state_size'] or 0x300000000<=a and a+n<=0x300100000,('module wrote foreign memory',hex(a))
  m.u.hook_add(UC_HOOK_MEM_READ,secret_reads);m.u.hook_add(UC_HOOK_MEM_WRITE,writes)
 def cache(self,identities):
  m=self.m;ptr=m.data(max(24,len(identities)*24));data=bytearray()
  for i,a in enumerate(identities):
   key=bytes((j+i*17)&255 for j in range(16));data+=a+key+b'\x01';self.secret.append((ptr+24*i+7,ptr+24*i+23))
  m.write(ptr,data or bytes(24));m.write(0x100a5f1b8+self.slide,p64(ptr));m.write(0x100a5f1c0+self.slide,struct.pack('<H',len(identities)))
  self.cacheptr=ptr;self.cachebytes=bytes(data)
 def raw(self,index=0,nonce=1):
  m=self.m;key=self.cachebytes[index*24+7:index*24+23];prand=bytes([0x40+(nonce%64),(nonce>>8)&255,nonce&255])
  # Native AH receives big-endian prand; the native AH reverses stored IRK.
  plain=bytes(13)+prand;return b'\x01'+prand+aes(key[::-1],plain)[-3:]
 def scan(self,raw):
  m=self.m;report=m.data(80);m.write(report,bytes(80));m.write(report+1,raw);m.write(report+0x18,b'\xc9')
  before=len(self.observed);m.call(0x1001f1948+self.slide,report)
  assert len(self.observed)==before+1
  assert bytes(m.u.mem_read(self.cacheptr,len(self.cachebytes)))==self.cachebytes
  return self.observed[-1]
 def build(self,values,multi=False):
  m=self.m;self.keys=[];ptr=m.data(max(8,len(values)*8));m.write(ptr,b''.join(p64(v) for v in values) or bytes(8));tree=m.data(24);m.write(tree,bytes(24))
  if multi:
   assert len(values)==1;m.call(P['guards']['multi']+self.slide,tree,ptr,ptr)
   assert m.u.reg_read(UC_X86_REG_RDX)&255==1,'native two-register insert result lost'
  else:m.call(P['guards']['single']+self.slide,tree,ptr,len(values),0)
  assert bytes(m.u.mem_read(ptr,max(8,len(values)*8)))==(b''.join(p64(v) for v in values) or bytes(8))
  return list(self.keys)
 def native_single_filter(self,stable):
  self.getter=stable;self.keys=[];m=self.m;tree=m.data(24);m.write(tree,bytes(24))
  m.call(0x10068b008+self.slide,tree,HEAP+0x5400,HEAP+0x5500)
  return list(self.keys)
 def counters(self):return struct.unpack('<QIIIIII',self.m.u.mem_read(self.state,32))
def number(address):return int.from_bytes(address,'big')
ID=b'\x00\x02\x03\x04\x05\x06\x07';OTHER=b'\x00\x03\x04\x05\x06\x07\x08'
results=[]
for slide in [0,-0x100000,0x12345000,0x118000000]:
 s=Scenario(slide);s.cache([ID,OTHER]);raw=s.raw();assert s.scan(raw)==ID
 assert s.build([number(ID)])==[number(raw)]
 assert s.native_single_filter(number(ID))==[number(raw)]
 assert s.build([number(ID)],multi=True)==[number(raw)]
 assert s.build([number(OTHER),number(raw),0,0xffffffffffffffff])==[number(OTHER),number(raw),0,0xffffffffffffffff]
 # A distinct device's correctly resolved packet must never route this identity.
 second=s.raw(1,9);assert s.scan(second)==OTHER;assert s.build([number(ID),number(OTHER)])==[number(raw),number(second)]
 new=s.raw(0,10);assert s.scan(new)==ID;assert s.build([number(ID)])==[number(new)]
 s.clock=[1015,0];assert s.build([number(ID)])==[number(new)]
 s.clock=[1015,1];assert s.build([number(ID)])==[number(ID)]
 s.clock=[999,999];assert s.build([number(ID)])==[number(ID)]
 s.clock=[1000,0];s.m.write(s.state+8,struct.pack('<I',1));assert s.build([number(ID)])==[number(ID)];s.m.write(s.state+8,bytes(4))
 assert s.counters()[-1]==1
 assert len(s.stages)==len(set(s.stages)) and set(s.stages)=={1,2,3,4}
 results.append({'slide':hex(slide),'native_software_AES_resolution':True,'single_multi_route':True,'other_identity_passthrough':True,'rotation_updates':True,'ttl_boundary_rollback_busy_passthrough':True,'keys_and_source_unchanged':True})
for payload in [True,False]:
 s=Scenario(payload=payload);s.cache([ID]);raw=s.raw();unmatched=raw[:-1]+bytes([raw[-1]^1]);assert s.scan(unmatched)==unmatched
 assert s.build([number(ID)])==[number(ID)]
 if not payload:
  assert s.scan(raw)==ID;assert s.build([number(ID)],multi=True)==[number(ID)];assert not any(s.m.u.mem_read(s.state,L['state_size']))
  assert s.native_single_filter(number(ID))==[number(ID)]
 results.append({'payload':payload,'unmatched_rejected':True,'missing_payload_native_fallback':not payload})
# Eviction is bounded, no unvalidated address input or service/name mapping.
s=Scenario();ids=[bytes([0,2,3,4,5,6,i+1]) for i in range(10)];s.cache(ids)
for i,a in enumerate(ids):assert s.scan(s.raw(i,i+1))==a
for i in range(10):assert s.build([number(ids[i])])==[number(s.raw(i,i+1)) if i>=2 else number(ids[i])]
# A dirty module marker refuses entry and preserves native behavior.
s=Scenario();s.cache([ID]);s.m.write(L['payload_vm'],b'\x00')
assert s.scan(s.raw())==ID and s.build([number(ID)])==[number(ID)]
results.append({'bounded_eight_entry_eviction':True,'dirty_marker_native_fallback':True})
# Boundary/fallback and refresh checks execute the same compiled module.
s=Scenario();s.cache([ID]);raw=s.raw();assert s.scan(raw)==ID
assert s.build([])==[]
assert s.build([number(ID)]*64)==[number(raw)]*64
assert s.build([number(ID)]*65)==[number(ID)]*65
s.clock=[1000,1000];assert s.build([number(ID)])==[number(ID)]
s.clock=[1000,0];s.m.write(s.state,p64(0xdeadbeef));assert s.build([number(ID)])==[number(ID)]
s=Scenario();s.cache([ID]);raw=s.raw();s.scan(raw);s.clock=[1020,0];assert s.build([number(ID)])==[number(ID)]
s.scan(raw);assert s.build([number(ID)])==[number(raw)]
# Unmatched packet only emits one fixed public stage, without adding a mapping.
s=Scenario();s.cache([ID]);raw=s.raw();bad=raw[:-1]+bytes([raw[-1]^1]);s.scan(bad);s.scan(bad);assert s.stages==[5]
results.append({'array_counts_0_64_65':True,'invalid_clock_dirty_state_passthrough':True,'expired_entry_refresh':True,'unmatched_log_once_no_mapping':True})
(W/'native-route-results.json').write_text(json.dumps({'offline_only':True,'AES_backend':'local CommonCrypto AES-128 ECB; FIPS-197 known answer passed','native_fixture_sha256':hashlib.sha256(B.b).hexdigest(),'cases':results},indent=2)+'\n')
print('PASS: compiled routing module + native scan/IRK resolver/AH/set code:',len(results),'scenario groups; synthetic keys only; no IRK reads by routing code, foreign global writes, input mutation or real HCI commands.')
