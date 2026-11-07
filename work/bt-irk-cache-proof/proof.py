from pathlib import Path
import sys,struct,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bt-standard-privacy'))
from native_queue_test import Machine,B,HEAP,p64

def case(same=True,enabled=False):
 m=Machine([B.function(0x1006e38b4)]);calls=[]
 obj=m.data(0x2000);m.write(obj,bytes(0x2000));address=m.data(7);key=m.data(16)
 addr=bytes([0,1,2,3,4,5,6]);original=bytes(range(16));new=original if same else bytes(range(16,32))
 m.write(address,addr);m.write(key,new);m.write(obj+0x275,original+addr+b'\x01');m.write(obj+0x29,bytes([enabled]))
 m.stub(0x1007e4ea8,lambda *a:1)
 def fmt(out,*a):m.write(out,bytes(32));return 0
 m.stub(0x10066fb00,fmt);m.stub(0x1007e479a,lambda *a:calls.append('Incorrect IRK log') or 0)
 m.stub(0x1006e51d6,lambda *a:calls.append('remove cache entry') or 0)
 m.stub(0x1006e0728,lambda *a:0)
 controller=m.data(16);vt=m.data(0x180);m.write(controller,p64(vt));m.write(vt+0x168,p64(HEAP+0x5000));m.write(vt+0x170,p64(HEAP+0x5100))
 m.stub(0x100337b70,lambda *a:controller)
 m.stub(HEAP+0x5000,lambda *a:calls.append('controller add IRK') or 0)
 m.stub(HEAP+0x5100,lambda *a:calls.append('controller remove IRK') or 0)
 m.stub(0x1006f0aa0,lambda *a:HEAP);m.stub(0x1007e4db8,lambda *a:HEAP);m.stub(0x1006e01ec,lambda *a:0)
 m.stub(0x1009db0a8,lambda *a:0) # objc release indirect slot is replaced below
 # The native tail jumps through this import. Use a synthetic stub target.
 m.write(0x1009db0a8,p64(HEAP+0x5200));m.stub(HEAP+0x5200,lambda *a:0)
 m.call(0x1006e38b4,obj,address,key)
 stored=bytes(m.u.mem_read(obj+0x275,16));assert stored==new
 assert ('Incorrect IRK log' in calls)==same
 assert ('controller add IRK' in calls)==(not same and enabled)
 return {'same_key':same,'backend_condition':enabled,'calls':calls,'stored_key_equals_requested':True}
r=[case(s,e) for s in [True,False] for e in [False,True]]
Path(__file__).with_name('proof-results.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
