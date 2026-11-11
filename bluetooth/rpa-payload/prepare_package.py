# One-off packager of the 2.7.11 kit (2026-11-02), kept for reference: it reads folders that no longer exist
# (work/continuity, work/bt-cache-capacity-probe). New Bluetooth builds use bluetooth/build.py.
from pathlib import Path
import json,shutil,hashlib,sys,zipfile
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;K=ROOT/'work/be201-rpa-route';O=ROOT/'outputs/BE201近期地址路由实验-2.7.11';O.mkdir(exist_ok=True);O.chmod(0o700)
for name in ['BlueToolFixup.kext']:
 dst=O/name
 if dst.exists():shutil.rmtree(dst)
 shutil.copytree(K/name,dst)
for name in ['entry-audit.json','symbol-check.json','build-commands.json','build.log','BE201Patches.hpp'] :shutil.copy2(K/name,O/name)
for name in ['patch-layout.json','authenticated-rpa-layout.json','authenticated-rpa-build.json','native-route-results.json','page-test.txt']:shutil.copy2(W/name,O/name)
for name in ['common.py','ocvalidate']:shutil.copy2(ROOT/'outputs/BE201缓存入口容量探测-2.7.10'/name,O/name)
# Only bounded undo spans are distributed, never full Apple native code pages.
sys.path.insert(0,str(ROOT/'work/continuity'));from inspect_bluetoothd import Binary
B=Binary(ROOT/'work/continuity/bluetoothd-x86_64');old=json.loads((ROOT/'work/bt-cache-capacity-probe/patch-layout.json').read_text());undo=[]
for row in old['pages']:
 at=row['thin_page']+row['offset'];undo.append({'page':row['fat_page'],'original_sha256':row['original_sha256'],'patched_sha256':row['patched_sha256'],'offset':row['offset'],'original_hex':B.b[at:at+row['size']].hex()})
(O/'previous-probe-undo.json').write_text(json.dumps(undo,indent=2))
s=(K/'read_system_bt.py').read_text().replace('def read_verified(patch_header=None):','def read_verified(patch_header=None,raw_override=None):').replace("raw=Path('/usr/sbin/bluetoothd').read_bytes();b=bytearray(raw)","raw=Path('/usr/sbin/bluetoothd').read_bytes() if raw_override is None else raw_override;b=bytearray(raw)")
(O/'verify_native_base.py').write_text(s)
(O/'verify_native.py').write_text('''from pathlib import Path
import json,hashlib
from verify_native_base import read_verified
HERE=Path(__file__).resolve().parent
def verify():
 raw=bytearray(Path('/usr/sbin/bluetoothd').read_bytes());undo=json.loads((HERE/'previous-probe-undo.json').read_text())
 for row in undo:
  at=row['page'];h=hashlib.sha256(raw[at:at+4096]).hexdigest()
  assert h in [row['original_sha256'],row['patched_sha256']],'Unexpected diagnostic code page'
  if h==row['patched_sha256']:
   p=at+row['offset'];data=bytes.fromhex(row['original_hex']);raw[p:p+len(data)]=data
 verified,report=read_verified(HERE/'BE201Patches.hpp',bytes(raw))
 thin=verified[0x4000:];import struct
 # Slice size is taken from the universal architecture entry.
 size=next(struct.unpack_from('>IIIII',verified,8+20*i)[3] for i in range(struct.unpack_from('>I',verified,4)[0]) if struct.unpack_from('>I',verified,8+20*i)[0]==0x1000007)
 assert hashlib.sha256(thin[:size]).hexdigest()=='ac352c5f24a3b8040703551478854a7d15c2ae119c3bad3d68ee56237d239338'
 report['normalized_thin_sha256']=hashlib.sha256(thin[:size]).hexdigest();return report
if __name__=='__main__':print(json.dumps(verify(),indent=2))
''')
# Source archive excludes Apple fixtures, generated full native pages, object files,
# private logs, EFI and identity material. External SDKs remain pinned dependencies.
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for directory in [W,K]:
  for p in directory.rglob('*'):
   if not p.is_file() or p.suffix not in ['.cpp','.hpp','.py','.c','.plist','.h'] or any(part.endswith(('.kext','.dSYM')) for part in p.parts):continue
   z.write(p,str(p.relative_to(ROOT)))
manifest={str(p.relative_to(O)):hashlib.sha256(p.read_bytes()).hexdigest() for p in O.rglob('*') if p.is_file()}
(O/'SHA256SUMS.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print('Prepared',O)
