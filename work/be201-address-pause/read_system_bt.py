"""Reconstruct a test fixture from known Lilu cache patches; verify every x86 code page.
Never writes the system file. CodeDirectory hashes distinguish a known cache patch
from an unexpected binary version or modification.
"""
from pathlib import Path
import struct,hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
def read_verified(patch_header=None):
 raw=Path('/usr/sbin/bluetoothd').read_bytes();b=bytearray(raw)
 if patch_header is None:
  candidates=[Path(__file__).with_name('BE201Patches.hpp'),ROOT/'work/be201-address-pause/BE201Patches.hpp',ROOT/'work/be201-le-baseline/BE201Patches.hpp',ROOT/'work/be201-peer-address/BE201Patches.hpp',ROOT/'work/be201-adv/BE201Patches.hpp',ROOT/'work/be201-compat/BE201Patches.hpp']
  patch_header=next(x for x in candidates if x.exists())
 s=Path(patch_header).read_text();v={n:bytes(int(x,16) for x in z.split(',')) for n,z in re.findall(r'unsigned char (\w+)\[\] = \{([^}]+)\}',s)}
 sites=[(0x3ede39,v['kBE201ClockOriginal'],v['kBE201ClockPatched']),(0x8c0159,v['kBE201NameOriginal'],v['kBE201NamePatched']),(0xd17f4,bytes.fromhex('81fa5c0a000074'),bytes.fromhex('81fa5c0a0000eb')),(0x2ea321,bytes.fromhex('81f9cf07000072'),bytes.fromhex('81f9cf070000eb')),(0x320a5d,bytes.fromhex('81f9cf07000072'),bytes.fromhex('81f9cf070000eb')),(0x1b7939,bytes.fromhex('81f96f1700007730'),bytes.fromhex('9090909090909090'))]
 if "kBE201LegacyAdvOriginal" in v:sites.append((0x61c0c7,v["kBE201LegacyAdvOriginal"],v["kBE201LegacyAdvPatched"]))
 if "kBE201PeerAddressOriginal" in v:sites.append((0x68f059,v["kBE201PeerAddressOriginal"],v["kBE201PeerAddressPatched"]))
 if "kBE201LEBaselineOriginal" in v:sites.append((0x137c48,v["kBE201LEBaselineOriginal"],v["kBE201LEBaselinePatched"]))
 if "kBE201AddressPauseOriginal" in v:sites.append((0x1ecd13,v["kBE201AddressPauseOriginal"],v["kBE201AddressPausePatched"]))
 restored=[]
 for pos,orig,patch in sites:
  value=bytes(b[pos:pos+len(orig)]);assert value in (orig,patch),f'Unexpected context at {pos:x}'
  if value!=orig:restored.append(hex(pos));b[pos:pos+len(orig)]=orig
 assert b[:4]==bytes.fromhex('cafebabe')
 arches=[struct.unpack_from('>IIIII',b,8+20*i) for i in range(struct.unpack_from('>I',b,4)[0])]
 arch=next(x for x in arches if x[0]==0x1000007);base,size=arch[2:4];assert base==0x4000
 thin=b[base:base+size];at=32;uuid=None
 for _ in range(struct.unpack_from('<I',thin,16)[0]):
  cmd,n=struct.unpack_from('<II',thin,at)
  if cmd==0x1d:off,length=struct.unpack_from('<II',thin,at+8)
  if cmd==0x1b:uuid=bytes(thin[at+8:at+24]).hex()
  at+=n
 sb=thin[off:off+length];assert struct.unpack_from('>I',sb)[0]==0xfade0cc0
 cd=None
 for i in range(struct.unpack_from('>I',sb,8)[0]):
  ty,p=struct.unpack_from('>II',sb,12+8*i)
  if ty==0:
   magic,length=struct.unpack_from('>II',sb,p);assert magic==0xfade0c02;cd=sb[p:p+length]
 assert cd is not None
 ho,io,ns,nc,limit=struct.unpack_from('>IIIII',cd,16);hs,ht,plat,ps=struct.unpack_from('BBBB',cd,36);assert ht==2 and hs==32 and ps==12
 bad=[]
 for i in range(nc):
  got=hashlib.sha256(thin[i*4096:min((i+1)*4096,limit)]).digest()
  if got!=cd[ho+i*hs:ho+(i+1)*hs]:bad.append(hex(base+i*4096))
 assert not bad,f'Unknown code-page changes: {bad}'
 return bytes(b),{'read_sha256':hashlib.sha256(raw).hexdigest(),'verified_fixture_sha256':hashlib.sha256(b).hexdigest(),'x86_uuid':uuid,'x86_code_directory_sha256':hashlib.sha256(cd).hexdigest(),'verified_x86_code_pages':nc,'cache_patch_sites_restored':restored,'system_file_written':False}
if __name__=='__main__':
 b,r=read_verified();print(json.dumps(r,indent=2))
