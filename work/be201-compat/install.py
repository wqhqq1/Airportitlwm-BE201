from pathlib import Path
import subprocess,plistlib,json,shutil,hashlib,datetime,os
w=Path(__file__).resolve().parent;base=w.parent.parent;out=base/'outputs/BE201型号与Music修复';out.mkdir(exist_ok=True);out.chmod(0o700)
u='65EA6FB3-72D2-4697-8E12-8815434C008E';guid='7C436110-AB2A-4BBB-A880-FE41995C9F82'
def info(x):return plistlib.loads(subprocess.check_output(['diskutil','info','-plist',x]))
def manifest(p):return {str(x.relative_to(p)):hashlib.sha256(x.read_bytes()).hexdigest() for x in p.rglob('*') if x.is_file()}
e=info(u);r=info('/');assert e['DiskUUID']==u and e['ParentWholeDisk']=='disk1' and [s['APFSPhysicalStore'] for s in r['APFSPhysicalStores']]==['disk1s4'];assert e.get('MountPoint')
assert subprocess.check_output(['sw_vers','-buildVersion'],text=True).strip()=='24G824'
assert hashlib.sha256(Path('/usr/sbin/bluetoothd').read_bytes()).hexdigest()==json.loads((w/'patch-verification.json').read_text())['bluetoothd_sha256']
efi=Path(e['MountPoint'])/'EFI';oc=efi/'OC';old=(oc/'config.plist').read_bytes();d=plistlib.loads(old)
rows=[x for x in d['Kernel']['Add'] if x['BundlePath']=='BlueToolFixup.kext'];assert len(rows)==1 and rows[0]['Enabled'];assert rows[0]['Arch']=='x86_64' and rows[0]['MaxKernel']=='24.99.99'
oldkext=oc/'Kexts/BlueToolFixup.kext';assert plistlib.loads((oldkext/'Contents/Info.plist').read_bytes())['CFBundleVersion']=='2.7.2'
args=d['NVRAM']['Add'][guid].get('boot-args','').split();assert not set(args)&{'-btlfxa2dpcheck','-be201identity','-btlfxoff','-liluoff'}
assert len(d['NVRAM']['Add'][guid]['bluetoothInternalControllerInfo'])==14
new=plistlib.loads(old);row=next(x for x in new['Kernel']['Add'] if x['BundlePath']=='BlueToolFixup.kext');row['Comment']='BlueToolFixup 2.7.3 LOCAL: Intel BE201 label + exact 24G824 A2DP clock gate'
new['NVRAM']['Add'][guid]['boot-args']=' '.join(args+['-be201identity','-btlfxa2dpcheck'])
# Boot args are commonly seeded, not overwritten, by OpenCore. Delete then add ensures this change is consumed.
deletes=new['NVRAM']['Delete'].setdefault(guid,[])
if 'boot-args' not in deletes:deletes.append('boot-args')
rollback=plistlib.loads(old);rb=next(x for x in rollback['Kernel']['Add'] if x['BundlePath']=='BlueToolFixup.kext');rb['BundlePath']='BlueToolFixup-before-BE201.kext'
for obj,name in [(new,'config.plist'),(rollback,'config-BE201-compat-rollback.plist')]:
 p=w/name;p.write_bytes(plistlib.dumps(obj,sort_keys=False))
 v=subprocess.run(['/Users/wqhqq/Documents/Codex/2026-10-30/bang/work/oc/Utilities/ocvalidate/ocvalidate',str(p)],capture_output=True,text=True);assert v.returncode==0,v.stdout+v.stderr
 (out/(name+'.ocvalidate.txt')).write_text(v.stdout+v.stderr)
backup=out/'EFI-before-model-Music-fix';assert not backup.exists();before=manifest(efi);shutil.copytree(efi,backup/'EFI');assert manifest(backup/'EFI')==before
assert (oc/'config.plist').read_bytes()==old and manifest(efi)==before,'EFI changed concurrently; stopped'
assert not (oc/'Kexts/BlueToolFixup-before-BE201.kext').exists();shutil.copytree(oldkext,oc/'Kexts/BlueToolFixup-before-BE201.kext');assert manifest(oldkext)==manifest(oc/'Kexts/BlueToolFixup-before-BE201.kext')
stage=oc/'Kexts/BlueToolFixup-local-staged.kext';assert not stage.exists();shutil.copytree(w/'BlueToolFixup.kext',stage);assert manifest(stage)==manifest(w/'BlueToolFixup.kext')
# Preserve a complete stock kext before replacing. No kernel loading occurs here.
shutil.rmtree(oldkext);stage.rename(oldkext)
for name in ['config-BE201-compat-rollback.plist','config.plist']:
 tmp=oc/(name+'.new');tmp.write_bytes((w/name).read_bytes());os.replace(tmp,oc/name)
subprocess.run(['/bin/sync'],check=True)
after=manifest(efi);changed=sorted(x for x in set(before)|set(after) if before.get(x)!=after.get(x))
assert all(x=='OC/config.plist' or x=='OC/config-BE201-compat-rollback.plist' or x.startswith('OC/Kexts/BlueToolFixup.kext/') or x.startswith('OC/Kexts/BlueToolFixup-before-BE201.kext/') for x in changed),changed
assert manifest(oldkext)==manifest(w/'BlueToolFixup.kext');assert (oc/'config.plist').read_bytes()==(w/'config.plist').read_bytes()
for name in ['config.plist','config-BE201-compat-rollback.plist']:shutil.copy2(w/name,out/name)
shutil.copytree(w/'BlueToolFixup.kext',out/'BlueToolFixup.kext')
record={'installed_at':datetime.datetime.now().isoformat(),'efi_uuid':u,'efi_partition':'disk1s3','macos_store':'disk1s4','before_manifest':before,'after_manifest':after,'changed_paths':changed,'boot_args_added':['-be201identity','-btlfxa2dpcheck'],'boot_args_delete_before_add':True,'original_boot_args_delete_present':'boot-args' in d['NVRAM']['Delete'].get(guid,[]),'version':'2.7.3 LOCAL','unchanged_kext_order':True,'unchanged_controller_info_14_bytes':True,'runtime_test':'PENDING REBOOT','model_expected':'Intel BE201','vendor_expected':'Apple (0x004C)'}
(out/'安装与验证.json').write_text(json.dumps(record,indent=2));print('Installed; changed paths:',changed);print('Reboot required; live kext is still stock 2.7.2.')
