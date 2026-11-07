"""Offline direct-call cross references; validates candidate instruction boundaries."""
from pathlib import Path
import sys,struct,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'continuity'))
from inspect_bluetoothd import Binary
b=Binary(Path(__file__).resolve().parents[1]/'continuity/bluetoothd-x86_64')
targets={int(x,16) for x in sys.argv[1:]};rows=[];validated={}
for name,a,n,o in b.sections:
 if name!='__text':continue
 data=b.b[o:o+n];at=-1
 while True:
  at=data.find(b'\xe8',at+1)
  if at<0 or at+5>len(data):break
  addr=a+at;target=addr+5+struct.unpack_from('<i',data,at+1)[0]
  if target not in targets:continue
  start,end=b.function(addr)
  if start not in validated:validated[start]={i.address for i in b.md.disasm(b.b[b.off(start):b.off(end)],start) if i.mnemonic=='call'}
  if addr in validated[start]:rows.append({'call':hex(addr),'function':hex(start),'target':hex(target)})
print(json.dumps(rows,indent=2))
