from pathlib import Path
import subprocess,plistlib,json,shutil,hashlib,datetime,os
from zoneinfo import ZoneInfo
W=Path(__file__).resolve().parent;BASE=W.parents[1];OUT=BASE/'outputs/BE201异步地址保护测试-2.5.5';OUT.mkdir(exist_ok=True);OUT.chmod(0o700)
UUID='65EA6FB3-72D2-4697-8E12-8815434C008E';GUID='7C436110-AB2A-4BBB-A880-FE41995C9F82';FLAG='-be201nativeaddr';RECOVERY='IntelBTPatcher-asyncaddr-recovery.kext'
VALIDATOR=Path('/Users/wqhqq/Documents/Codex/2026-10-30/bang/work/oc/Utilities/ocvalidate/ocvalidate')
def info(p):return plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist',p]))
def disk():
 e=info(UUID);r=info('/');assert e['DiskUUID']==UUID and e.get('MountPoint') and e['WritableVolume'],'Specified EFI is not mounted'
 stores=[info(x['APFSPhysicalStore']) for x in r['APFSPhysicalStores']];assert len(stores)==1 and stores[0]['ParentWholeDisk']==e['ParentWholeDisk']
 return e,stores[0]
def manifest(p):
 assert not any(f.is_symlink() for f in p.rglob('*'))
 return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
def atomic(p,b):
 t=p.with_name(p.name+'.BLE-new');assert not t.exists();t.write_bytes(b);os.replace(t,p)
e,store=disk();assert subprocess.check_output(['sw_vers','-buildVersion'],text=True).strip()=='24G824'
EFI=Path(e['MountPoint'])/'EFI';OC=EFI/'OC';CFG=OC/'config.plist';old=CFG.read_bytes();d=plistlib.loads(old)
rows=[x for x in d['Kernel']['Add'] if x['BundlePath']=='IntelBTPatcher.kext'];assert len(rows)==1 and rows[0]['Enabled'] and rows[0]['Arch']=='x86_64' and rows[0]['MaxKernel']=='24.99.99'
active=OC/'Kexts/IntelBTPatcher.kext';previous=manifest(active);assert previous==manifest(BASE/'work/bt-native-address/IntelBTPatcher.kext')
assert plistlib.loads((active/'Contents/Info.plist').read_bytes())['CFBundleVersion']=='2.5.4'
src=W/'IntelBTPatcher.kext';subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(src)],check=True)
audit=json.loads((W/'entry-audit.json').read_text());assert hashlib.sha256((src/'Contents/MacOS/IntelBTPatcher').read_bytes()).hexdigest()==audit['sha256']
args=d['NVRAM']['Add'][GUID]['boot-args'].split();assert FLAG in args and {'-be201leadv','-be201identity','-btlfxa2dpcheck','-be201btprobe'}<=set(args)
new=plistlib.loads(old);next(x for x in new['Kernel']['Add'] if x['BundlePath']=='IntelBTPatcher.kext')['Comment']='IntelBTPatcher 2.5.5 LOCAL: native RPA USB completion observer including async; retains existing compatibility fixes'
# Existing boot arguments and NVRAM are preserved byte-for-byte semantically.
check=plistlib.loads(plistlib.dumps(new));next(x for x in check['Kernel']['Add'] if x['BundlePath']=='IntelBTPatcher.kext')['Comment']=rows[0]['Comment'];check['NVRAM']=d['NVRAM'];assert check==d
recovery=plistlib.loads(old);next(x for x in recovery['Kernel']['Add'] if x['BundlePath']=='IntelBTPatcher.kext')['BundlePath']=RECOVERY
for n,v in [('config.plist',new),('config-BE201-asyncaddr-rollback.plist',recovery)]:
 p=W/n;p.write_bytes(plistlib.dumps(v,sort_keys=False));r=subprocess.run([str(VALIDATOR),str(p)],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr;(OUT/(n+'.ocvalidate.txt')).write_text(r.stdout+r.stderr)
before=manifest(EFI);backup=OUT/('EFI-before-asyncaddr-'+datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S'));assert not backup.exists();shutil.copytree(EFI,backup/'EFI');assert manifest(backup/'EFI')==before
assert CFG.read_bytes()==old and manifest(EFI)==before,'Concurrent EFI changes; stopped'
disk();retained=OC/'Kexts'/RECOVERY;stage=OC/'Kexts/IntelBTPatcher-asyncaddr-staged.kext';assert not retained.exists() and not stage.exists()
shutil.copytree(src,stage);assert manifest(stage)==manifest(src);active.rename(retained)
try:stage.rename(active)
except BaseException:retained.rename(active);raise
assert manifest(retained)==previous
atomic(OC/'config-BE201-asyncaddr-rollback.plist',(W/'config-BE201-asyncaddr-rollback.plist').read_bytes());atomic(CFG,(W/'config.plist').read_bytes());subprocess.run(['/bin/sync'],check=True)
after=manifest(EFI);changed=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
assert all(k in ['OC/config.plist','OC/config-BE201-asyncaddr-rollback.plist'] or k.startswith('OC/Kexts/IntelBTPatcher.kext/') or k.startswith('OC/Kexts/'+RECOVERY+'/') for k in changed)
assert manifest(active)==manifest(src) and CFG.read_bytes()==(W/'config.plist').read_bytes()
record={'time':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'efi_uuid':UUID,'efi_device':e['DeviceIdentifier'],'macos_store':store['DeviceIdentifier'],'candidate_uuid':audit['uuid'],'version':'2.5.5 LOCAL','backup':str(backup),'backup_verified':True,'old_bundle_manifest':previous,'before_manifest':before,'after_manifest':after,'changed_paths':changed,'bootarg_added':None,'bootarg_reused':FLAG,'WiFi_BlueToolFixup_firmware_unchanged':True,'hotspot_runtime_result':'Pending reboot; experimental native RPA policy; hotspot repair not verified'}
(OUT/'安装与校验记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
for n in ['config.plist','config-BE201-asyncaddr-rollback.plist']:shutil.copy2(W/n,OUT/n)
shutil.copytree(src,OUT/'IntelBTPatcher.kext');shutil.copytree(retained,OUT/RECOVERY);shutil.copy2(VALIDATOR,OUT/'ocvalidate')
print('Installed experimental native RPA preservation; full backup verified; reboot required.');print(str(backup))
