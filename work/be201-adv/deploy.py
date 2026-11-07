"""Install the opt-in local LE fallback, touching only the authorized EFI UUID."""
from pathlib import Path
import subprocess,plistlib,json,shutil,hashlib,datetime,os,sys
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'continuity'))
from read_system_bt import read_verified
BASE=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;OUT=BASE/'outputs/BE201连续互通广播修复';OUT.mkdir(exist_ok=True);OUT.chmod(0o700)
UUID='65EA6FB3-72D2-4697-8E12-8815434C008E';GUID='7C436110-AB2A-4BBB-A880-FE41995C9F82';FLAG='-be201leadv';RECOVERY='BlueToolFixup-LE-recovery.kext'
VALIDATOR=Path('/Users/wqhqq/Documents/Codex/2026-10-30/bang/work/oc/Utilities/ocvalidate/ocvalidate')
def info(p):return plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist',p]))
def verify_disk():
 e=info(UUID);r=info('/');assert e['DiskUUID']==UUID and e.get('MountPoint') and e['WritableVolume']
 stores=[info(x['APFSPhysicalStore']) for x in r['APFSPhysicalStores']];assert len(stores)==1 and stores[0]['ParentWholeDisk']==e['ParentWholeDisk']
 return e,stores[0]
def manifest(p):
 assert not any(f.is_symlink() for f in p.rglob('*'))
 return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
def validate(p):
 r=subprocess.run([str(VALIDATOR),str(p)],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr
 (OUT/(p.name+'.ocvalidate.txt')).write_text(r.stdout+r.stderr)
def write_config(path,data):
 tmp=path.with_name(path.name+'.LE-new');assert not tmp.exists();tmp.write_bytes(data);os.replace(tmp,path)
e,store=verify_disk();assert subprocess.check_output(['sw_vers','-buildVersion'],text=True).strip()=='24G824'
_,verification=read_verified();assert verification['x86_code_directory_sha256']==json.loads((W/'system-binary-verification.json').read_text())['x86_code_directory_sha256']
EFI=Path(e['MountPoint'])/'EFI';OC=EFI/'OC';CFG=OC/'config.plist';old=CFG.read_bytes();d=plistlib.loads(old)
rows=[x for x in d['Kernel']['Add'] if x['BundlePath']=='BlueToolFixup.kext'];assert len(rows)==1 and rows[0]['Enabled'] and rows[0]['Arch']=='x86_64' and rows[0]['MaxKernel']=='24.99.99'
old_bundle=OC/'Kexts/BlueToolFixup.kext';old_manifest=manifest(old_bundle)
assert plistlib.loads((old_bundle/'Contents/Info.plist').read_bytes())['CFBundleVersion']=='2.7.3'
assert old_manifest==manifest(BASE/'work/be201-compat/BlueToolFixup.kext')
new_bundle=W/'BlueToolFixup.kext';subprocess.run(['codesign','--verify','--deep','--strict',str(new_bundle)],check=True)
assert plistlib.loads((new_bundle/'Contents/Info.plist').read_bytes())['CFBundleVersion']=='2.7.4'
args=d['NVRAM']['Add'][GUID]['boot-args'].split();assert FLAG not in args
assert {'-be201identity','-btlfxa2dpcheck'}<=set(args)
assert not set(args)&{'-btlfxoff','-liluoff'}
new=plistlib.loads(old);next(x for x in new['Kernel']['Add'] if x['BundlePath']=='BlueToolFixup.kext')['Comment']='BlueToolFixup 2.7.4 LOCAL: native single LE advertising; retain BE201 identity and Music fix'
new['NVRAM']['Add'][GUID]['boot-args']=' '.join(args+[FLAG]);deletes=new['NVRAM']['Delete'].setdefault(GUID,[])
if 'boot-args' not in deletes:deletes.append('boot-args')
# Assert the intended scope before doing any EFI mutation.
scope=plistlib.loads(plistlib.dumps(new));next(x for x in scope['Kernel']['Add'] if x['BundlePath']=='BlueToolFixup.kext')['Comment']=rows[0]['Comment'];scope['NVRAM']=d['NVRAM'];assert scope==d
rollback=plistlib.loads(old);next(x for x in rollback['Kernel']['Add'] if x['BundlePath']=='BlueToolFixup.kext')['BundlePath']=RECOVERY
for name,obj in [('config.plist',new),('config-BE201-LE-rollback.plist',rollback)]:
 p=W/name;p.write_bytes(plistlib.dumps(obj,sort_keys=False));validate(p)
before=manifest(EFI);stamp=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S');backup=OUT/('EFI-before-LE-'+stamp)
assert not backup.exists();shutil.copytree(EFI,backup/'EFI');assert manifest(backup/'EFI')==before
assert CFG.read_bytes()==old and manifest(EFI)==before,'Concurrent EFI mutation; stopped'
verify_disk();retained=OC/'Kexts'/RECOVERY;stage=OC/'Kexts/BlueToolFixup-LE-staged.kext';assert not retained.exists() and not stage.exists()
shutil.copytree(new_bundle,stage);assert manifest(stage)==manifest(new_bundle)
old_bundle.rename(retained)
try:stage.rename(old_bundle)
except BaseException:retained.rename(old_bundle);raise
assert manifest(retained)==old_manifest
write_config(OC/'config-BE201-LE-rollback.plist',(W/'config-BE201-LE-rollback.plist').read_bytes())
write_config(CFG,(W/'config.plist').read_bytes());subprocess.run(['/bin/sync'],check=True)
after=manifest(EFI);changed=sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p))
assert all(p in ('OC/config.plist','OC/config-BE201-LE-rollback.plist') or p.startswith('OC/Kexts/BlueToolFixup.kext/') or p.startswith('OC/Kexts/'+RECOVERY+'/') for p in changed)
assert manifest(old_bundle)==manifest(new_bundle) and CFG.read_bytes()==(W/'config.plist').read_bytes()
record={'time':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'efi_uuid':UUID,'efi_device':e['DeviceIdentifier'],'macos_store':store['DeviceIdentifier'],'backup':str(backup),'backup_manifest_verified':True,'version':'2.7.4 LOCAL','candidate_uuid':json.loads((W/'entry-audit.json').read_text())['uuid'],'added_bootarg':FLAG,'preserved_flags':['-be201identity','-btlfxa2dpcheck'],'changed_paths':changed,'old_bundle_manifest':old_manifest,'before_manifest':before,'after_manifest':after,'kernel_add_order_unchanged':True,'wifi_and_other_kexts_unchanged':True,'runtime_status':'Pending reboot; real LE advertising/Handoff/Clipboard not yet verified'}
(OUT/'安装与校验记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
for n in ['config.plist','config-BE201-LE-rollback.plist']:shutil.copy2(W/n,OUT/n)
shutil.copytree(new_bundle,OUT/'BlueToolFixup.kext');shutil.copytree(retained,OUT/RECOVERY);shutil.copy2(VALIDATOR,OUT/'ocvalidate')
print('Installed 2.7.4 LOCAL with opt-in native single LE advertising; reboot required. Full backup verified; Wi-Fi and other kexts unchanged.')
print('Backup: '+str(backup))
