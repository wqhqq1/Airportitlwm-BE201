"""Restore only the pre-probe IntelBTPatcher bundle selection; preserve later EFI changes."""
from pathlib import Path
import subprocess,plistlib,json,hashlib,shutil,datetime,os,sys
from zoneinfo import ZoneInfo
FOLDER=Path(__file__).resolve().parent;UUID='65EA6FB3-72D2-4697-8E12-8815434C008E';GUID='7C436110-AB2A-4BBB-A880-FE41995C9F82';RECOVERY='IntelBTPatcher-nativeaddr-recovery.kext'
def info(x):return plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist',x]))
def disk():
 e=info(UUID);r=info('/');assert e['DiskUUID']==UUID and e.get('MountPoint'),'请先挂载指定 UUID 的 EFI。此工具不会请求管理员密码。'
 stores=[info(x['APFSPhysicalStore'])['ParentWholeDisk'] for x in r['APFSPhysicalStores']];assert stores==[e['ParentWholeDisk']]
 return e
def manifest(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
e=disk();EFI=Path(e['MountPoint'])/'EFI';OC=EFI/'OC';CFG=OC/'config.plist';old=CFG.read_bytes();d=plistlib.loads(old)
r=json.loads((FOLDER/'安装与校验记录.json').read_text());bundle=OC/'Kexts'/RECOVERY;assert manifest(bundle)==r['old_bundle_manifest']
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(bundle)],check=True)
rows=[x for x in d['Kernel']['Add'] if x['BundlePath'] in ('IntelBTPatcher.kext',RECOVERY)];assert len(rows)==1 and rows[0]['Enabled']
if sys.argv[1:]!=['--restore']:
 print('恢复检查通过。未修改 EFI；运行 --restore 将选回保留的 2.5.3，并只移除 -be201nativeaddr。');sys.exit(0)
rows[0]['BundlePath']=RECOVERY;rows[0]['Comment']='BE201 IntelBTPatcher 2.5.3 pre-address-experiment recovery'
d['NVRAM']['Add'][GUID]['boot-args']=' '.join(x for x in d['NVRAM']['Add'][GUID]['boot-args'].split() if x!='-be201nativeaddr')
deletes=d['NVRAM']['Delete'].setdefault(GUID,[])
if 'boot-args' not in deletes:deletes.append('boot-args')
if d==plistlib.loads(old):print('当前已是原生地址实验回退配置。');sys.exit(0)
p=FOLDER/'config-restore-BLEprobe.new.plist';p.write_bytes(plistlib.dumps(d,sort_keys=False));subprocess.run([str(FOLDER/'ocvalidate'),str(p)],check=True)
before=manifest(EFI);backup=FOLDER/('EFI-before-BLEprobe-restore-'+datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S'));shutil.copytree(EFI,backup/'EFI');assert manifest(backup/'EFI')==before
assert manifest(EFI)==before and CFG.read_bytes()==old;disk();tmp=OC/'config-BLEprobe-restore.new';assert not tmp.exists();tmp.write_bytes(p.read_bytes());os.replace(tmp,CFG);subprocess.run(['/bin/sync'],check=True)
after=manifest(EFI);assert {k for k in set(before)|set(after) if before.get(k)!=after.get(k)}=={'OC/config.plist'}
print('已选回蓝牙 2.5.3，仅移除原生地址实验参数；Wi-Fi 与其他设置保留。请手动重启。完整备份：'+str(backup))
