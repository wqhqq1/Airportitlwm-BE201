from inspect_kc import KC
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
import re,json
from pathlib import Path
k=KC();md=Cs(CS_ARCH_X86,CS_MODE_64);result={}
for s,a in k.symbols.items():
 m=re.match(r'__Z\d+apple80211((?:get|set)\w+)P23IO80211SkywalkInterface',s)
 if not m:continue
 end=min(x for x in k.ordered if x>a);end=min(end,a+2048)
 slots=set()
 for i in md.disasm(k.read(a,end-a),a):
  z=re.search(r'qword ptr \[rax \+ (0x[0-9a-f]+)\]',i.op_str)
  if z:
   off=int(z[1],16)
   if off%8==0 and 500<=off//8<=562:slots.add(off//8)
 for slot in slots:result.setdefault(slot,[]).append({'method':m[1],'symbol':s})
for slot in range(500,563):print(slot,[x['method'] for x in result.get(slot,[])])
Path(__file__).with_name('awdl-method-slots.json').write_text(json.dumps(result,indent=2))
