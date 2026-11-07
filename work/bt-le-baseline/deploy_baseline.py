from pathlib import Path
import subprocess,plistlib,json,hashlib,shutil,datetime,os
from zoneinfo import ZoneInfo
BASE=Path(__file__).resolve().parents[2];OUT=BASE/'outputs/BE201真实LE事件回退-2.5.7';OUT.mkdir(exist_ok=True);OUT.chmod(0o700);GUID='7C436110-AB2A-4BBB-A880-FE41995C9F82';UUID='65EA6FB3-72D2-4697-8E12-8815434C008E'
VALIDATOR=Path('/Users/wqhqq/Documents/Codex/2026-10-30/bang/work/oc/Utilities/ocvalidate/ocvalidate')
PAIRS=[('IntelBTPatcher','bt-le-baseline','bt-advert-observer','IntelBTPatcher-baseline-recovery.kext'),('BlueToolFixup','be201-le-baseline','be201-patch-observer','BlueToolFixup-baseline-recovery.kext')]
def info(x):return plistlib.loads(subprocess.check_output(['diskutil','info','-plist',x]))
def disk():
 e=info(UUID);r=info('/');assert e['DiskUUID']==UUID and e.get('MountPoint') and e['WritableVolume']
 stores=[info(x['APFSPhysicalStore']) for x in r['APFSPhysicalStores']];assert len(stores)==1 and stores[0]['ParentWholeDisk']==e['ParentWholeDisk'];return e,stores[0]
def manifest(p):
 assert not any(f.is_symlink() for f in p.rglob('*'))
 return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
def validate(p):
 r=subprocess.run([str(VALIDATOR),str(p)],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr;(OUT/(p.name+'.ocvalidate.txt')).write_text(r.stdout+r.stderr)
def atomic(p,b):
 t=p.with_name(p.name+'.link-new');assert not t.exists();t.write_bytes(b);os.replace(t,p)
e,store=disk();EFI=Path(e['MountPoint'])/'EFI';OC=EFI/'OC';CFG=OC/'config.plist';old=CFG.read_bytes();d=plistlib.loads(old);new=plistlib.loads(old);rollback=plistlib.loads(old);binary_checks=[]
flags=d['NVRAM']['Add'][GUID]['boot-args'].split();assert '-be201lebaseline' not in flags and '-be201btprobe' in flags and {'-be201peeraddr','-be201leadv','-be201nativeaddr','-be201identity','-btlfxa2dpcheck'}<=set(flags)
for name,folder,prior,recovery in PAIRS:
 source=BASE/'work'/folder/(name+'.kext');installed=OC/'Kexts'/(name+'.kext');retained=OC/'Kexts'/recovery
 assert not retained.exists() and manifest(installed)==manifest(BASE/'work'/prior/(name+'.kext'))
 for bundle in [source,installed]:subprocess.run(['codesign','--verify','--deep','--strict',str(bundle)],check=True)
 audit=json.loads((BASE/'work'/folder/'entry-audit.json').read_text());assert audit['lilu_callbacks_verified'] and audit['constructors'];assert hashlib.sha256((source/'Contents/MacOS'/name).read_bytes()).hexdigest()==audit['sha256']
 rows=[x for x in new['Kernel']['Add'] if x['BundlePath']==name+'.kext'];assert len(rows)==1 and rows[0]['Enabled'] and rows[0]['Arch']=='x86_64'
 rows[0]['Comment']=name+' LOCAL: native LE EDL/2M predicate fallback + preserve real feature events; no new fabricated events'
 next(x for x in rollback['Kernel']['Add'] if x['BundlePath']==name+'.kext')['BundlePath']=recovery
 binary_checks.append({'bundle':name,'uuid':audit['uuid'],'sha256':audit['sha256'],'recovery':recovery,'source_manifest':manifest(source),'old_manifest':manifest(installed)})
new['NVRAM']['Add'][GUID]['boot-args']=' '.join(flags+['-be201lebaseline']);assert 'boot-args' in new['NVRAM']['Delete'][GUID]
# Limit changes to two comments and the explicit diagnostic boot argument.
rest=plistlib.loads(plistlib.dumps(new));rest['NVRAM']=d['NVRAM']
for x,y in zip(rest['Kernel']['Add'],d['Kernel']['Add']):x['Comment']=y['Comment']
assert rest==d
for filename,obj in [('config.plist',new),('config-BE201-lebaseline-rollback.plist',rollback)]:
 p=OUT/filename;p.write_bytes(plistlib.dumps(obj,sort_keys=False));validate(p)
assert not (OC/'config-BE201-lebaseline-rollback.plist').exists()
before=manifest(EFI);stamp=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S');backup=OUT/('EFI-before-lebaseline-'+stamp);shutil.copytree(EFI,backup/'EFI');assert manifest(backup/'EFI')==before
assert manifest(EFI)==before and CFG.read_bytes()==old;disk();stages=[];done=[]
try:
 for (name,folder,prior,recovery),check in zip(PAIRS,binary_checks):
  stage=OC/'Kexts'/(name+'-link-staged.kext');assert not stage.exists();shutil.copytree(BASE/'work'/folder/(name+'.kext'),stage);stages.append(stage);assert manifest(stage)==check['source_manifest']
 for name,folder,prior,recovery in PAIRS:
  installed=OC/'Kexts'/(name+'.kext');retained=OC/'Kexts'/recovery;installed.rename(retained);done.append((installed,retained));(OC/'Kexts'/(name+'-link-staged.kext')).rename(installed)
 atomic(OC/'config-BE201-lebaseline-rollback.plist',(OUT/'config-BE201-lebaseline-rollback.plist').read_bytes());atomic(CFG,(OUT/'config.plist').read_bytes())
except BaseException:
 for installed,retained in reversed(done):
  if installed.exists():shutil.rmtree(installed)
  retained.rename(installed)
 if CFG.read_bytes()!=old:atomic(CFG,old)
 raise
finally:
 for p in stages:
  if p.exists():shutil.rmtree(p)
subprocess.run(['/bin/sync'],check=True);after=manifest(EFI);changed=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k));allowed=['OC/Kexts/'+name+'.kext/' for name,*_ in PAIRS]+['OC/Kexts/'+recovery+'/' for *_,recovery in PAIRS]
assert all(k in ['OC/config.plist','OC/config-BE201-lebaseline-rollback.plist'] or any(k.startswith(prefix) for prefix in allowed) for k in changed)
for (name,folder,prior,recovery),check in zip(PAIRS,binary_checks):assert manifest(OC/'Kexts'/(name+'.kext'))==check['source_manifest'] and manifest(OC/'Kexts'/recovery)==check['old_manifest']
assert CFG.read_bytes()==(OUT/'config.plist').read_bytes()
record={'time':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'efi_uuid':UUID,'efi_device':e['DeviceIdentifier'],'macos_store':store['DeviceIdentifier'],'backup':str(backup),'full_backup_manifest_verified':True,'binary_checks':binary_checks,'changed_paths':changed,'other_kexts_and_NV_settings_unchanged':True,'boot_argument_added':'-be201lebaseline','scope':'BE201-only opt-in: suppress duplicate LE remote-feature reads and global event rewrites; native Sequoia local EDL/2M predicates return unavailable. Preserve actual event/status/feature bytes; current advertising, identity, Music, RPA and Wi-Fi unchanged.','reboot_status':'Pending user reboot; native BLE/GATT and Continuity not yet verified','before_manifest':before,'after_manifest':after}
(OUT/'部署与校验记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2));shutil.copy2(VALIDATOR,OUT/'ocvalidate')
print(json.dumps({k:v for k,v in record.items() if k not in ['before_manifest','after_manifest','binary_checks','changed_paths']},ensure_ascii=False,indent=2))
