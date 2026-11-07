"""Execute compiled probe + patched native call path + actual native HCI queue.
Only synthetic memory/controller replies. No system or USB access.
"""
from pathlib import Path
import sys,struct,json,hashlib
W=Path(__file__).resolve().parent
sys.path.insert(0,str(W.parent/'bt-standard-privacy'))
from native_queue_test import Machine,B,HEAP,p64,u64
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_RIP
layout=json.loads((W/'capacity-probe-layout.json').read_text())
patch=json.loads((W/'patch-layout.json').read_text())
def run(slide=0,status=0,capacity=16,ready=True,full=False,payload_present=True,dirty=False,backend=None,bad_reply=False,cache=False):
 funcs=[0x1006e38b4,0x1001b5725,0x1001529ba,0x100152c41,0x100159d67,0x100159ce2,
        0x100155a84,0x1001951f0,0x1001952cb,0x10015a081,0x10015a098]
 m=Machine([(s+slide,e+slide) for s,e in [B.function(a) for a in funcs]],slide=slide)
 m.allowed.append((layout['payload_vm']+16+slide,layout['payload_vm']+layout['payload_size']+slide))
 for row in patch['pages']:
  if row['name']=='payload' and not payload_present:continue
  m.write(0x100000000+row['thin_page']+slide,(W/(row['name']+'-page-patched.bin')).read_bytes())
 controller=m.data(16);m.write(controller,bytes([0,0,4,5,6,7,8])+bytes(9))
 slots=m.data(192);expected=m.data(128)
 m.write(0x100a69230+slide,p64(controller));m.write(0x100a4e9d8+slide,p64(slots))
 m.write(0x100a4ed50+slide,p64(expected));m.write(0x100a4ed40+slide,bytes(2))
 m.write(0x100a4e9c8+slide,bytes(1));m.write(0x100a4e9cc+slide,struct.pack('<I',4 if full else 0))
 m.write(0x100a69478+slide,struct.pack('<I',1 if ready else 0))
 state=layout['state_vm']+slide
 if dirty:m.write(state,b'\x01')
 original_state=bytes(m.u.mem_read(state,32));sent=[];fragments=[];backend_calls=[]
 if backend is not None:
  fn=HEAP+0x5000;m.write(0x100a4f688+slide,p64(fn))
  m.stub(fn,lambda *args:backend_calls.append(args) or backend)
 def clock(out,*_):m.write(out,struct.pack('<II',1000,0));return 0
 m.stub(0x1000d5be3+slide,clock);m.stub(0x100159ebe+slide,lambda *a:0)
 m.stub(0x10021d2ac+slide,lambda *a:0)
 m.stub(0x10021d83f+slide,lambda obj,p,n,*a:fragments.append(bytes(m.u.mem_read(p,n)) if n else b'') or 0)
 m.stub(0x10014397f+slide,lambda kind,op,buf,n,*a:sent.append((kind,op,n)) or 0)
 m.stub(0x10021c674+slide,lambda *a:0);m.stub(0x10015a2ac+slide,lambda *a:0)
 address=m.data(7);key=m.data(16);m.write(address,b'\x00\x01\x02\x03\x04\x05\xc6');m.write(key,b'\xa5'*16)
 original_key=bytes(m.u.mem_read(key,16));original_address=bytes(m.u.mem_read(address,6))
 obj=m.data(0x2000);m.write(obj,bytes(0x2000));m.write(obj+0x275,original_key+bytes(m.u.mem_read(address,7))+b'\x01')
 def invoke():
  if cache:m.call(0x1006e38b4+slide,obj,address,key);return 0xe11
  return m.call(0x1001b5725+slide,0,address,key,16,0)
 def no_secret_reads(u,access,a,n,value,ctx):
  if not(layout['payload_vm']+16+slide<=u.reg_read(UC_X86_REG_RIP)<layout['payload_vm']+layout['payload_size']+slide):return
  assert not(a<key+16 and a+n>key), 'probe read IRK bytes'
  assert not(a<address+6 and a+n>address), 'probe read peer address bytes'
 def bounded_probe_writes(u,access,a,n,value,ctx):
  pc=u.reg_read(UC_X86_REG_RIP)
  if layout['payload_vm']+16+slide<=pc<layout['payload_vm']+layout['payload_size']+slide:
   assert state<=a and a+n<=state+32 or HEAP<=a and a+n<=HEAP+0x100000 or 0x300000000<=a and a+n<=0x300100000, ('probe wrote native global',hex(a))
 m.u.hook_add(UC_HOOK_MEM_READ,no_secret_reads);m.u.hook_add(UC_HOOK_MEM_WRITE,bounded_probe_writes)

 # Invalid native input must preserve OI_INVALID_PARAMETERS and issue no probe.
 assert m.call(0x1001b5725+slide,0,address,0,16,0)==0x65
 assert bytes(m.u.mem_read(state,32))==original_state
 result=invoke()
 assert result==(0xe11 if backend is None else backend)
 queued=struct.unpack('<I',m.u.mem_read(0x100a4e9cc+slide,4))[0]
 if not payload_present or dirty or backend is not None:
  assert queued==(4 if full else 0) and bytes(m.u.mem_read(state,32))==original_state
  return {'slide':hex(slide),'guarded_skip':True,'backend_passthrough':backend,'native_result':result}
 magic,phase,submit,complete,cap,malformed,callbacks=struct.unpack('<QIIIIII',m.u.mem_read(state,32))
 assert magic==0x4254323031505242
 if not ready or full:
  assert phase==4 and callbacks==0 and queued==(4 if full else 0)
  assert submit==(0x263 if full else 0)
  assert len(m.freed)==(1 if full else 0)
  return {'slide':hex(slide),'rejected_before_send':True,'native_submission_status':submit,'packet_freed_once':full}
 assert phase==2 and submit==0 and callbacks==0 and queued==1
 # Repeated IRK requests do not send another diagnostic or read key bytes.
 for i in range(3):assert invoke()==0xe11
 assert struct.unpack('<I',m.u.mem_read(0x100a4e9cc+slide,4))[0]==1
 native_callback=u64(m.u.mem_read(slots+32,8));native_context=u64(m.u.mem_read(slots+40,8))
 assert native_context==state
 packet=u64(m.u.mem_read(slots,8));assert bytes(m.u.mem_read(packet,4))==b'\x01\x2a\x20\x00'
 m.write(0x100a4e9c8+slide,b'\x01');m.write(0x100a692d1+slide,b'\x01');m.call(0x100152c41+slide)
 assert sent==[(1,0x202a,0)] and fragments==[b''] and m.freed==[packet]
 returned=bytes([capacity]) if not status and not bad_reply else b''
 event_wire=bytes([14,4+len(returned),1,0x2a,0x20,status])+returned
 event=m.data(len(event_wire));m.write(event,event_wire);context=m.data(16);m.write(context,bytes(16))
 m.call(0x100155a84+slide,event,len(event_wire),context)
 magic,phase,submit,complete,cap,malformed,callbacks=struct.unpack('<QIIIIII',m.u.mem_read(state,32))
 assert phase==3 and callbacks==1 and (complete==0)==(status==0)
 assert cap==(capacity if not status and not bad_reply else 0) and malformed==int(bad_reply)
 assert struct.unpack('<H',m.u.mem_read(0x100a4ed40+slide,2))[0]==0
 assert bytes(m.u.mem_read(0x100a692d1+slide,1))==b'\x01'
 before=bytes(m.u.mem_read(state,32));m.call(native_callback,0,state,0);assert bytes(m.u.mem_read(state,32))==before
 assert bytes(m.u.mem_read(key,16))==original_key and bytes(m.u.mem_read(address,6))==original_address
 return {'slide':hex(slide),'native_result_preserved':result,'command':0x202a,'native_completion_status':complete,'capacity':cap,'malformed':bool(malformed),'callbacks':callbacks,'duplicate_callback_ignored':True,'address_and_key_unchanged':True}
if __name__=='__main__':
 results=[run(),run(slide=-0x100000),run(slide=0x118000000),run(slide=0x12345000),run(slide=0x56789000,status=12),run(status=1),run(bad_reply=True),run(capacity=0),run(ready=False),run(full=True),run(payload_present=False),run(dirty=True),run(backend=0),run(backend=712),run(cache=True),run(cache=True,slide=0x12345000),run(cache=True,payload_present=False),run(cache=True,status=12)]
 (W/'native-probe-results.json').write_text(json.dumps({'offline_only':True,'cases':results},indent=2)+'\n')
 print('PASS:',len(results),'compiled probe/native queue cases: ASLR, real completion/status/credits, guards, ownership, native result preservation; read-only synthetic controller.')
