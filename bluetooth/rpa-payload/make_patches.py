"""Prepare exact-page diagnostic/experimental patches; never edit a system file."""
from pathlib import Path
import sys,struct,json,hashlib
W=Path(__file__).resolve().parent
sys.path.insert(0,str(W.parent/'continuity'));from inspect_bluetoothd import Binary
B=Binary(W.parent/'continuity/bluetoothd-x86_64')
assert hashlib.sha256(B.b).hexdigest()=='8272d7fcd7bd72d07ef0d09f6c7e4d51985e5c38996c59014f713397cae6dd63'
layout=json.loads((W/'authenticated-rpa-layout.json').read_text());payload=(W/'authenticated-rpa-payload.bin').read_bytes();vm=layout['payload_vm']
entries={k:vm+16+v-layout['text']['vm'] for k,v in layout['entries'].items()}
def rel(op,at,target):return op+struct.pack('<i',target-at-len(op)-4)
def guard(at,entry,original):
 # Called normally; only tail-jumps, so module and original preserve caller ABI.
 code=bytearray();fallback=at+29
 for off in [0,4]:
  pos=at+len(code);code+=b'\x81\x3d'+struct.pack('<i',vm+off-pos-10)+payload[off:off+4]
  pos=at+len(code);code+=b'\x75'+struct.pack('b',fallback-pos-2)
 code+=rel(b'\xe9',at+len(code),entry);assert len(code)==29
 code+=rel(b'\xe9',at+len(code),original);return code
changes={}
def change(at,data):
 off=B.off(at);page=off&~4095
 assert (off+len(data)-1)&~4095==page
 changes.setdefault(page,[]).append((off-page,bytes(data)))
# Existing log-only error path skips its logging body but keeps original cleanup.
change(0x1001f1cab,rel(b'\xe9',0x1001f1cab,0x1001f1cea)+b'\x90'*(0x3f-5))
change(0x1001f1cb0,guard(0x1001f1cb0,entries['_BE201ResolveRPA'],0x1001f58d3))
assert B.b[B.off(0x1001f19e1):B.off(0x1001f19e1)+5]==rel(b'\xe8',0x1001f19e1,0x1001f58d3)
change(0x1001f19e1,rel(b'\xe8',0x1001f19e1,0x1001f1cb0))
# Reuse a second log-only body for two guarded tail-jump entry points.
change(0x10068b3c4,rel(b'\xe9',0x10068b3c4,0x10068b40d)+b'\x90'*(0x49-5))
change(0x10068b3c9,guard(0x10068b3c9,entries['_BE201BuildFilter'],0x10069214c))
change(0x10068b3eb,guard(0x10068b3eb,entries['_BE201InsertMulti'],0x1002913fe))
for at,original,target in [(0x10068b079,0x10069214c,0x10068b3c9),(0x10068b26a,0x1002913fe,0x10068b3eb),(0x10068b333,0x1002913fe,0x10068b3eb)]:
 assert B.b[B.off(at):B.off(at)+5]==rel(b'\xe8',at,original)
 change(at,rel(b'\xe8',at,target))
change(vm,payload)
# Prove state and payload extents are outside all native sections/fixups.
raw=B.b;lc=32;segments=[];sections=[]
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 c,n=struct.unpack_from('<II',raw,lc)
 if c==0x19:
  name=raw[lc+8:lc+24].rstrip(b'\0').decode();a,size,fo,fs,maxp,initp=struct.unpack_from('<QQQQII',raw,lc+24);segments.append((name,a,a+size,initp))
  for j in range(struct.unpack_from('<I',raw,lc+64)[0]):
   p=lc+72+80*j;sa,sn=struct.unpack_from('<QQ',raw,p+32);sections.append((sa,sa+sn,name))
 lc+=n
state=layout['state_vm'];size=layout['state_size']
assert any(n=='__DATA' and a<=state<state+size<=e and prot&2 for n,a,e,prot in segments)
assert not any(a<state+size and e>state for a,e,n in sections)
assert not any(a<vm+len(payload) and e>vm for a,e,n in sections)
assert vm+len(payload)<=0x1009da000 and not any(B.b[B.off(vm):B.off(vm)+len(payload)])
# __DATA chained-fixup pages end before zero-fill common/tail (pinned layout).
assert state>=0x100a45000

def fnv(p):
 h=14695981039346656037
 for b in p:h=((h^b)*1099511628211)&((1<<64)-1)
 return h
names={0x1f1000:'Scan',0x68b000:'Filter',0x9d9000:'Payload'};rows=[]
header='// Generated exact-page routing patches. Opt-in -be201rparoute only.\n#pragma once\n#include <stdint.h>\n#include <stddef.h>\n'
for page,mods in sorted(changes.items()):
 name=names[page];before=B.b[page:page+4096];after=bytearray(before)
 for off,data in mods:after[off:off+len(data)]=data
 start=min(i for i in range(4096) if before[i]!=after[i]);end=max(i for i in range(4096) if before[i]!=after[i])+1
 # Package only spans of generated modifications, not full private native pages.
 spans=[];i=0
 while i<4096:
  if before[i]==after[i]:i+=1;continue
  start=i
  while i<4096 and before[i]!=after[i]:i+=1
  spans.append((start,bytes(after[start:i])))
 row={'name':name,'thin_page':page,'fat_page':page+0x4000,'original_fnv':fnv(before),'patched_fnv':fnv(after),'original_sha256':hashlib.sha256(before).hexdigest(),'patched_sha256':hashlib.sha256(after).hexdigest(),'spans':[]}
 for k,(off,data) in enumerate(spans):
  header+=f'static const uint8_t kRPA{name}{k}[]={{'+','.join(hex(x) for x in data)+'};\n';row['spans'].append({'offset':off,'size':len(data)})
 header+=f'static constexpr uint64_t kRPA{name}OriginalHash={fnv(before)}ULL,kRPA{name}PatchedHash={fnv(after)}ULL;\n'
 (W/(name.lower()+'-page-original.bin')).write_bytes(before);(W/(name.lower()+'-page-patched.bin')).write_bytes(after);rows.append(row)
header+='''static inline uint64_t be201RPAPageHash(const uint8_t *p,size_t n){uint64_t h=14695981039346656037ULL;for(size_t i=0;i<n;i++)h=(h^p[i])*1099511628211ULL;return h;}
static inline unsigned be201RPAApply(uint8_t *p,size_t n,uint64_t off){
 if(!p||n!=4096)return 0;const uint64_t h=be201RPAPageHash(p,n);
'''
for k,row in enumerate(rows):
 name=row['name'];header+=f' if(off=={row["thin_page"]}ULL||off=={row["fat_page"]}ULL){{\n  if(h==kRPA{name}PatchedHash)return {128|(1<<k)};if(h!=kRPA{name}OriginalHash)return 0;\n'
 for j,span in enumerate(row['spans']):header+=f'  for(size_t i=0;i<sizeof(kRPA{name}{j});i++)p[{span["offset"]}+i]=kRPA{name}{j}[i];\n'
 header+=f'  return {1<<k};\n }}\n'
header+=' return 0;\n}\n';(W/'AuthenticatedRPAPatch.hpp').write_text(header)
(W/'patch-layout.json').write_text(json.dumps({'pages':rows,'layout':layout,'entries':entries,'guards':{'scan':0x1001f1cb0,'single':0x10068b3c9,'multi':0x10068b3eb},'state_outside_sections':True,'payload_outside_sections':True,'ttl_milliseconds':15000,'capacity':8,'deployment':False},indent=2)+'\n')
print('PASS: 3 exact-page patches, 3 ABI-preserving guarded entries, 232-byte zero-fill state and guarded executable payload.')
