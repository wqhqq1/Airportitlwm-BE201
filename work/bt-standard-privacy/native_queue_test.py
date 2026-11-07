"""Offline execution of the local, pinned Apple x86 code; synthetic data only.
No process attachment, USB device, HCI channel, or system file mutation.
The fixture stays private and must not be copied into the output package.
"""
from pathlib import Path
import sys, struct, hashlib, json
W=Path(__file__).resolve().parent
sys.path[:0]=[str(W/'python-deps'),str(W.parent/'continuity')]
from inspect_bluetoothd import Binary
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import *
B=Binary(W.parent/'continuity/bluetoothd-x86_64')
assert hashlib.sha256(B.b).hexdigest()=='8272d7fcd7bd72d07ef0d09f6c7e4d51985e5c38996c59014f713397cae6dd63', 'unsupported native fixture'
BASE=0x100000000; HEAP=0x200000000; STACK=0x300000000; END=0x400000000
R=[UC_X86_REG_RDI,UC_X86_REG_RSI,UC_X86_REG_RDX,UC_X86_REG_RCX,UC_X86_REG_R8,UC_X86_REG_R9]
def p64(v):return struct.pack('<Q',v)
def u64(v):return struct.unpack('<Q',v)[0]
class Machine:
 def __init__(self,allowed,slide=0):
  self.u=u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(BASE+slide,0x1000000)
  for a,n,o in B.segments:u.mem_write(a+slide,B.b[o:o+n])
  for a,n in [(HEAP,0x100000),(STACK,0x100000),(END,0x1000)]:u.mem_map(a,n)
  self.top=HEAP+0x10000;self.allocs={};self.freed=[];self.stubs={};self.visited=[];self.allowed=allowed
  self.write(0x1009db508+slide,p64(HEAP));self.write(HEAP,p64(0x12345678))
  self.stub(0x1000cbcd3+slide,lambda *a:0) # logging disabled
  self.stub(0x1000d6f6d+slide,self.alloc)
  self.stub(0x1000d6fbe+slide,self.free)
  u.hook_add(UC_HOOK_CODE,self.step)
 def write(self,a,b):self.u.mem_write(a,bytes(b))
 def alloc(self,n,*_):
  a=self.top;self.top+=(n+15)&~15;assert self.top<HEAP+0xf0000
  self.allocs[a]=n;self.write(a,b'\xa5'*n);return a
 def free(self,a,*_):
  assert a in self.allocs,('double/foreign free',hex(a));self.freed.append(a);del self.allocs[a];return 0
 def stub(self,a,f):self.stubs[a]=f
 def step(self,u,a,n,ctx):
  if a in self.stubs:
   args=[u.reg_read(r) for r in R];v=self.stubs[a](*args)
   sp=u.reg_read(UC_X86_REG_RSP);ret=u64(u.mem_read(sp,8))
   u.reg_write(UC_X86_REG_RSP,sp+8);u.reg_write(UC_X86_REG_RAX,v or 0);u.reg_write(UC_X86_REG_RIP,ret);return
  if a==END:u.emu_stop();return
  assert any(s<=a<e for s,e in self.allowed),('unexpected native execution',hex(a))
  self.visited.append(a)
 def call(self,a,*args):
  sp=STACK+0xfff08;self.write(sp,p64(END));self.u.reg_write(UC_X86_REG_RSP,sp)
  self.u.reg_write(UC_X86_REG_RAX,0)
  for r,v in zip(R,args):self.u.reg_write(r,v)
  self.u.emu_start(a,END,count=200000)
  assert self.u.reg_read(UC_X86_REG_RIP)==END,'instruction limit'
  return self.u.reg_read(UC_X86_REG_RAX)&0xffffffff
 def data(self,n):return self.alloc(n)
def raw_vendor_guard():
 # Run the genuine raw wrapper, dispatcher, descriptor lookup and marshaller.
 allowed=[B.function(a) for a in [0x1001437e9,0x1001466f4,0x10019518d,0x100146a6d,0x1001951bb]]
 m=Machine(allowed);m.write(0x100a693c0+0xb8,struct.pack('<I',1))
 m.write(0x100a69238,struct.pack('<I',2))
 # Read-supported-command bits, including the original raw descriptor bit.
 m.write(0x100a69260,b'\xff'*64)
 m.stub(0x1000d732d,lambda *a:0)
 m.stub(0x100130f4e,lambda *a:0)
 seen=[]
 m.stub(0x1001529ba,lambda *a:seen.append(a) or 0)
 param=m.data(39);m.write(param,bytes(range(39)))
 out={}
 for op,n in [(0x2027,39),(0x202a,0),(0x202d,1),(0xfc27,39)]:
  before=len(seen);status=m.call(0x1001437e9,op,n,param,HEAP+0x100,HEAP+0x200)
  out[hex(op)]={'oi_status':status,'queued':len(seen)>before}
  if op<0xfc00:assert status==0x26f and len(seen)==before
  else:assert status==0 and len(seen)==before+1
 assert len(m.freed)==3
 return out
def queue_ownership():
 m=Machine([B.function(0x1001529ba)])
 controller=m.data(16);m.write(controller,bytes([0,0,2])+bytes(13))
 slots=m.data(96)
 m.write(0x100a69230,p64(controller));m.write(0x100a4e9d8,p64(slots))
 m.write(0x100a4e9c8,bytes(16)) # overwrite counts, pointer gets restored below
 m.write(0x100a4e9d8,p64(slots))
 meta=m.data(32);m.write(meta,bytes(32));m.write(meta+4,struct.pack('<HHB',0x202a,0x110,0x0e))
 packet=m.data(4);m.write(packet,b'\x01\x2a\x20\x00')
 rc=m.call(0x1001529ba,packet,4,meta)
 assert rc==0 and packet in m.allocs
 assert bytes(m.u.mem_read(slots,8))==p64(packet)
 assert bytes(m.u.mem_read(slots+16,32))==bytes(m.u.mem_read(meta,32))
 # Enqueue copied the metadata; modifying the caller's stack is harmless.
 m.write(meta,bytes([0xcc])*32)
 assert bytes(m.u.mem_read(slots+16+4,5))==struct.pack('<HHB',0x202a,0x110,0x0e)
 m.write(0x100a4e9cc,struct.pack('<I',2))
 packet2=m.data(4);m.write(packet2,b'\x01\x2a\x20\x00')
 rc=m.call(0x1001529ba,packet2,4,meta)
 assert rc==0x263 and packet2 not in m.allocs and m.freed==[packet2]
 return {'accepted_packet_retained':True,'request_copied':True,'full_queue_status':rc,'full_queue_packet_freed_once':True}
def complete_case(op,status,payload=b''):
 allowed=[B.function(a) for a in [0x100155a84,0x1001951f0,0x1001952cb,0x10015a081,0x10015a098]]
 m=Machine(allowed);seen=[];removed=[]
 cb=HEAP+0x5000;opaque=HEAP+0x6000
 def callback(oi,ctx,stream,*_):
  p,cap,limit,cursor,mode,error=struct.unpack('<QHHHBB',m.u.mem_read(stream,16))
  seen.append({'oi_status':oi,'opaque_matches':ctx==opaque,'capacity':cap,'limit':limit,'cursor':cursor,'mode':mode,'error':error,'remaining':bytes(m.u.mem_read(p+cursor,limit-cursor)).hex()})
  return 0
 m.stub(cb,callback)
 m.stub(0x10015a2ac,lambda *a:0)
 m.stub(0x100159ce2,lambda i,*a:removed.append(i) or 0)
 m.stub(0x100159ebe,lambda *a:0)
 m.stub(0x10021c674,lambda *a:0) # native next-command work scheduler
 entry=m.data(32);meta=bytearray(32)
 struct.pack_into('<HH',meta,4,op,0x110);meta[8]=0x0e
 struct.pack_into('<QQ',meta,16,cb,opaque);m.write(entry,meta)
 m.write(0x100a4ed40,struct.pack('<H',1));m.write(0x100a4ed50,p64(entry))
 packet=bytes([0x0e,4+len(payload),1,op&255,op>>8,status])+payload
 buf=m.data(len(packet));m.write(buf,packet);context=m.data(16);m.write(context,bytes(16))
 m.call(0x100155a84,buf,len(packet),context)
 assert len(seen)==1 and removed==[0],(seen,removed)
 assert seen[0]['opaque_matches'] and seen[0]['remaining']==payload.hex(),seen
 assert seen[0]['cursor']==6 and seen[0]['mode']==1 and seen[0]['error']==0
 assert (seen[0]['oi_status']==0)==(status==0)
 return seen[0]
def native_error_case(status):
 m=Machine([B.function(a) for a in [0x100157744,0x10019518d]])
 seen=[];cb=HEAP+0x5000;ctx=HEAP+0x6000
 m.stub(0x1001952ea,lambda *a:HEAP)
 m.stub(0x10021bd47,lambda *a:0) # format only
 m.stub(0x1000e0086,lambda *a:0) # log record only
 m.stub(0x1000d732d,lambda *a:0)
 m.stub(0x10015a286,lambda *a:0);m.stub(0x10015a293,lambda *a:0)
 m.stub(0x1000d59b6,lambda *a:0)
 def callback(oi,opaque,stream,*_):
  seen.append((oi,opaque));return 0
 m.stub(cb,callback)
 request=m.data(32);meta=bytearray(32)
 struct.pack_into('<HHB',meta,4,0x2027,0x110,0x0e);struct.pack_into('<QQ',meta,16,cb,ctx);m.write(request,meta)
 m.call(0x100157744,status,request)
 assert seen==[(status,ctx)],seen
 return {'native_status':status,'callback_once':True,'opaque_matches':True}
def queue_roundtrip(op=0x202a,parameters=b'',returned=b'\x10',hci_status=0,compiled=False):
 funcs=[0x1001529ba,0x100152c41,0x100159d67,0x100159ce2,
        0x100155a84,0x1001951f0,0x1001952cb,0x10015a081,0x10015a098]
 m=Machine([B.function(a) for a in funcs]);sent=[];seen=[]
 controller=m.data(16);m.write(controller,bytes([0,0,4,5,6,7,8])+bytes(9))
 slots=m.data(192);expected=m.data(128)
 m.write(0x100a69230,p64(controller));m.write(0x100a4e9d8,p64(slots))
 m.write(0x100a4ed50,p64(expected));m.write(0x100a4ed40,struct.pack('<H',0))
 m.write(0x100a4e9c8,bytes(1)) # enqueue first, then start native sender
 def clock(out,*_):m.write(out,struct.pack('<II',1000,0));return 0
 m.stub(0x1000d5be3,clock);m.stub(0x100159ebe,lambda *a:0)
 m.stub(0x10021d2ac,lambda *a:0)
 fragments=[]
 def append_fragment(obj,data,n,mode,*_):
  fragments.append(bytes(m.u.mem_read(data,n)) if n else b'');return 0
 m.stub(0x10021d83f,append_fragment)
 def transport(kind,op,buffer,n,*_):sent.append((kind,op,n));return 0
 m.stub(0x10014397f,transport)
 m.stub(0x10021c674,lambda *a:0);m.stub(0x10015a2ac,lambda *a:0)
 cb=HEAP+0x5000;ctx=HEAP+0x6000
 def callback(status,opaque,stream,*_):
  ptr,cap,limit,cursor,mode,error=struct.unpack('<QHHHBB',m.u.mem_read(stream,16))
  seen.append((status,opaque,bytes(m.u.mem_read(ptr+cursor,limit-cursor))))
  return 0
 m.stub(cb,callback)
 wire=bytes([1,op&255,op>>8,len(parameters)])+parameters
 if compiled:
  layout=json.loads((W/'native-adapter-layout.json').read_text());code=(W/'native-adapter-code.bin').read_bytes()
  assert hashlib.sha256(code).hexdigest()==layout['code_sha256']
  codebase=0x500000000;m.u.mem_map(codebase,0x1000);m.write(codebase,code);m.allowed.append((codebase,codebase+len(code)))
  ready=HEAP+0x5100;m.stub(ready,lambda *a:1)
  api=m.data(32);m.write(api,struct.pack('<QQQQ',ready,0x1000d6f6d,0x1000d6fbe,0x1001529ba))
  command=m.data(56);memory=bytearray(56);memory[:len(wire)-1]=wire[1:];struct.pack_into('<Q',memory,48,len(wire)-1);m.write(command,memory)
  entry=codebase+layout['entries']['_BE201SubmitStandard']-layout['text']['vm']
  assert m.call(entry,api,command,cb,ctx)==0
  packet=u64(m.u.mem_read(slots,8))
  assert bytes(m.u.mem_read(packet,len(wire)))==wire
 else:
  request=m.data(32);meta=bytearray(32)
  struct.pack_into('<HHB',meta,4,op,0x110,0x0e);struct.pack_into('<QQ',meta,16,cb,ctx);m.write(request,meta)
  packet=m.data(len(wire));m.write(packet,wire)
  assert m.call(0x1001529ba,packet,len(wire),request)==0
 assert struct.unpack('<I',m.u.mem_read(0x100a4e9cc,4))[0]==1
 m.write(0x100a4e9c8,b'\x01');m.write(0x100a692d1,b'\x01')
 m.call(0x100152c41)
 assert sent==[(1,op,len(parameters))] and packet not in m.allocs and m.freed==[packet],sent
 assert fragments==[parameters],fragments
 assert struct.unpack('<H',m.u.mem_read(0x100a4ed40,2))[0]==1
 assert bytes(m.u.mem_read(0x100a692d1,1))==b'\x00' # native credit consumed
 event_wire=bytes([14,4+len(returned),1,op&255,op>>8,hci_status])+returned
 event=m.data(len(event_wire));m.write(event,event_wire)
 eventContext=m.data(16);m.write(eventContext,bytes(16))
 m.call(0x100155a84,event,len(event_wire),eventContext)
 assert len(seen)==1 and seen[0][1:]==(ctx,returned) and (seen[0][0]==0)==(hci_status==0),seen
 assert struct.unpack('<H',m.u.mem_read(0x100a4ed40,2))[0]==0
 assert bytes(m.u.mem_read(0x100a692d1,1))==b'\x01' # actual event replenished credit
 return {'opcode':op,'parameter_length':len(parameters),'compiled_adapter':compiled,'native_status':seen[0][0],'native_enqueue_send_complete':True,'packet_freed_once':True,
         'credit_decremented_and_restored':True,'expected_request_removed':True,'return_parameter_length':len(returned)}
if __name__=='__main__':
 results={'fixture_sha256':hashlib.sha256(B.b).hexdigest(),'raw_guard':raw_vendor_guard(),
  'queue_ownership':queue_ownership(),'native_roundtrips':[queue_roundtrip(),queue_roundtrip(0x2027,bytes([1,1,2,3,4,5,0xc6])+bytes(range(32)),b''),queue_roundtrip(0x202d,b'\x01',b'',12),queue_roundtrip(compiled=True),queue_roundtrip(0x2027,bytes([1,1,2,3,4,5,0xc6])+bytes(range(32)),b'',compiled=True),queue_roundtrip(0x202d,b'\x01',b'',12,compiled=True)],
  'native_error_callbacks':[native_error_case(s) for s in [0x26d,0x275,0xe78]],
  'native_completions':{'read_capacity':complete_case(0x202a,0,b'\x10'),'add_ok':complete_case(0x2027,0),'add_disallowed':complete_case(0x2027,0x0c)}}
 print(json.dumps(results,indent=2))
