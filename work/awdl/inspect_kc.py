"""Read-only symbol, disassembly and vtable inspection of this host's Boot KC."""
from pathlib import Path
import struct,json,sys,bisect
sys.path.insert(0,str(Path(__file__).parent/'python-deps'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
class KC:
 def __init__(self):
  self.b=Path('/System/Library/KernelCollections/BootKernelExtensions.kc').read_bytes();self.segments=[];pos=32
  for i in range(struct.unpack_from('<I',self.b,16)[0]):
   cmd,n=struct.unpack_from('<II',self.b,pos)
   if cmd==0x19:
    name,addr,size,off,filesize=struct.unpack_from('<16sQQQQ',self.b,pos+8);self.segments.append((addr,filesize,off))
   pos+=n
  self.symbols={};self.byaddr={}
  for l in (Path(__file__).resolve().parents[1]/'research/system-symbols.txt').read_text().splitlines():
   v=l.split()
   if len(v)==3 and v[1]!='U':
    try:a=int(v[0],16)
    except ValueError:continue
    self.symbols[v[2]]=a;self.byaddr.setdefault(a,[]).append(v[2])
  self.ordered=sorted(self.byaddr)
 def read(self,a,n):
  for addr,size,off in self.segments:
   if addr<=a and a+n<=addr+size:return self.b[off+a-addr:off+a-addr+n]
  raise ValueError(hex(a))
 def ptr(self,raw):
  if raw in self.byaddr:return raw
  addr=0xffffff8000100000+(raw & 0x3fffffff)
  return addr
 def sym(self,a):return '|'.join(self.byaddr.get(a,[])) or hex(a)
 def dis(self,s,n=180):
  a=self.symbols[s] if isinstance(s,str) else s
  for i in Cs(CS_ARCH_X86,CS_MODE_64).disasm(self.read(a,n),a):
   annot=''
   if i.mnemonic in ['call','jmp'] and i.op_str.startswith('0x'):annot=self.sym(int(i.op_str,16))
   print(hex(i.address),i.mnemonic,i.op_str,annot)

 def vt(self,s):
  a=self.symbols[s];end=min(x for x in self.ordered if x>a)
  rows=[]
  for off in range(16,min(end-a,0x3000),8):
   raw=struct.unpack('<Q',self.read(a+off,8))[0];p=self.ptr(raw);rows.append({'slot':(off-16)//8,'offset':hex(off-16),'raw':hex(raw),'address':hex(p),'symbol':self.sym(p)})
  return rows
if __name__=='__main__':
 k=KC()
 for s in sys.argv[1:]:
  print(s)
  if '__ZTV' in s:
   rows=k.vt(s);(Path(__file__).parent/(s+'.json')).write_text(json.dumps(rows,indent=2));print('\n'.join(f"{r['offset']} {r['symbol']}" for r in rows))
  else:k.dis(s)
