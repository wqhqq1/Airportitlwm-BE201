from pathlib import Path
import subprocess,plistlib,shutil,sys,hashlib,json,zipfile,os
base=Path.cwd(); repo=base/'work/airportbz'; old=base/'outputs/BE201AWDL提速-1.1.52'; out=base/'outputs/BE201AWDL队列-1.1.53'
assert json.loads((base/'work/awdl-held-1153/checks.json').read_text())['all_passed'], 'Do not package failing checks'
out.mkdir(mode=0o700); bundle=out/'AirportItlwm.kext';shutil.copytree(old/'AirportItlwm.kext',bundle)
p=bundle/'Contents/Info.plist';info=plistlib.loads(p.read_bytes());info['CFBundleVersion']=info['CFBundleShortVersionString']='1.1.53';info['BE201LocalBuild']='AWDL interface and link need a manual arm after boot; no IFF_RUNNING; receive-only native AWDL action input; no TX/data/ranging';p.write_bytes(plistlib.dumps(info,sort_keys=False))
shutil.copy2(base/'work/be201-awdl-held53-build/AirportItlwm',bundle/'Contents/MacOS/AirportItlwm')
subprocess.run(['codesign','--force','--sign','-','--timestamp=none',str(bundle)],check=True);subprocess.run(['codesign','--verify','--deep','--strict',str(bundle)],check=True)
shutil.copy2(old/'audit_entry.py',out/'audit_entry.py');sys.path.insert(0,str(out));from audit_entry import MachO
m=MachO(bundle/'Contents/MacOS/AirportItlwm');a=m.audit();assert a['entry_self_reference_absent'] and a['no_custom_callbacks']
sects={s['name']:s['size'] for s in m.sections if s['name'] in ['__mod_init_func','__mod_term_func']};assert sects=={'__mod_init_func':64,'__mod_term_func':64},sects
imports=lambda p:set(x.split()[-1] for x in subprocess.check_output(['nm','-u',str(p)],text=True).splitlines() if x.strip())
i=imports(m.path);oldi=imports(old/'AirportItlwm.kext/Contents/MacOS/AirportItlwm')
available={v[-1] for line in (base/'work/research/system-symbols.txt').read_text().splitlines() if len(v:=line.split())>=3 and v[-2]!='U'}
assert not i-available,sorted(i-available);assert not oldi-i,sorted(oldi-i)
sdk=base/'work/airportbz-deps/MacKernelSDK';dep=json.loads((base/'outputs/BE201-ax-1.1.0/依赖与构建记录.json').read_text())
manifest={str(p.relative_to(sdk)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sdk.rglob('*') if p.is_file()};assert manifest==dep['sdk_manifest'] and len(manifest)==1232
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
newfiles=['AirportItlwm/AirportItlwmAWDLInterface.cpp','AirportItlwm/AirportItlwmAWDLInterface.hpp','AirportItlwm/BE201SkywalkFactories.hpp','scripts/test-awdl-vif.py','scripts/test-awdl-vif-abi.py','BE201-AWDL-VIF-1.1.53.md','itlwm/hal_iwx/iwx_awdl_native.h','scripts/test-awdl-native.py','itlwm/hal_iwx/iwx_awdl_rx.h','scripts/test-awdl-rx.py','AirportItlwm/BE201ActionBuffer.hpp']
subprocess.run(['git','add','-N',*newfiles],cwd=repo,check=True)
patch=subprocess.check_output(['git','diff','HEAD','--binary'],cwd=repo);(out/'source-1.1.53.patch').write_bytes(patch)
archive=out/'对应源码与依赖.zip';files=subprocess.check_output(['git','ls-files','-z'],cwd=repo).split(b'\0')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for f in files:
  if f and (repo/f.decode()).is_file():z.write(repo/f.decode(),'airportbz/'+f.decode())
 z.write(base/'outputs/BE201-ax-1.1.0/MacKernelSDK.zip','dependencies/MacKernelSDK.zip')
with zipfile.ZipFile(archive) as z:assert len(z.namelist())==len(set(z.namelist())) and z.testzip() is None
b=json.loads((old/'build-audit.json').read_text());b.update(version='1.1.53',old_binary_sha256=sha(old/'AirportItlwm.kext/Contents/MacOS/AirportItlwm'),new_binary_sha256=sha(m.path),uuid=a['uuid'],source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()+' + source-1.1.53.patch (uncommitted)',source_patch_sha256=sha(out/'source-1.1.53.patch'),source_archive_sha256=sha(archive),runtime_status='NOT_LOADED; interface and RX need manual arm; monitor validated in 1.1.27, native input not yet validated',compilation_units=58,compile_units=58,constructors=8,destructors=8,import_count=len(i),import_set_unchanged=(i==oldi),native_imports=len(i),new_imports=sorted(i-oldi),removed_imports=sorted(oldi-i),missing_imports=[],sdk_manifest_files=len(manifest))
for name,d in [('build-audit.json',b),('entry-audit.json',a),('sdk-manifest.json',manifest)]: (out/name).write_text(json.dumps(d,indent=2)+'\n')
for n in ['record.py','开始记录.command','camera_test.py','开始相机实验.command','channel_test.py','开始信道实验.command','airdrop_test.py','开始隔空投送实验.command']:
 shutil.copy2(base/'work/awdl-held-1153'/n,out/n)
for n in ['ocvalidate','tlc_trace.py','join_trace.py','conv.py','tv3.py','view.py','采集手机日志.command']:shutil.copy2(old/n,out/n)
s=(old/'install.py').read_text().replace('awdlagg','awdlheld').replace('1.1.52','1.1.53').replace('1.1.50','1.1.52')
assert 'config-BE201-awdlheld-capability.plist' in s and "== 'MacBookPro16,2'" in s
(out/'install.py').write_text(s)
s=(old/'collect.py').read_text().replace('expected_1_1_52_loaded','expected_1_1_53_loaded').replace('AirportItlwm (1.1.52)','AirportItlwm (1.1.53)').replace(json.loads((old/'build-audit.json').read_text())['uuid'].upper(),a['uuid'].upper())
assert 'vif_report(HERE)' in s and 'r.returncode == 0 and r.stdout' in s
assert "properties={k:(v.hex() if isinstance(v,bytes) else v)" in s
s=s.replace("report['feature_results'] = 'This candidate creates the interface only after a manual arm. AWDL link/data remain disabled; AirDrop file transfer is not implemented. Record hotspot/Bluetooth/Handoff separately.'", "report['feature_results'] = 'Manual arm enables receive-only native AWDL actions. Submitted count is not peer acceptance; TX/data/ranging remain incomplete. Record hotspot/Handoff/Watch separately.'")
s=s.replace("p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\\n')", "p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\\n'); p.chmod(0o600)")
(out/'collect.py').write_text(s)
(out/'采集重启结果.command').write_text('#!/bin/zsh\ncd -- "${0:A:h}" || exit 1\n/usr/bin/python3 collect.py\n');(out/'采集重启结果.command').chmod(0o700)
shutil.copy2(repo/'BE201-AWDL-VIF-1.1.53.md',out/'开发与验证说明.md')
shutil.copy2(base/'work/awdl-held-1153/vif_report.py',out/'vif_report.py')
shutil.copy2(old/'capture.py',out/'capture.py');shutil.copy2(old/'开始抓包.command',out/'开始抓包.command')
shutil.copy2(base/'work/awdl-held-1153/checks.json',out/'checks.json');shutil.copytree(base/'work/awdl-held-1153/tests',out/'test-logs')
shutil.copy2(repo/'build/awdl-vif-abi/validation.json',out/'awdl-vif-abi.json')
shutil.copy2(base/'work/awdl-held-1153/使用与回退.md',out/'使用与回退.md')
print(json.dumps({'kit':str(out),'uuid':a['uuid'],'sha256':b['new_binary_sha256'],'imports':len(i),'compilation_units':58,'new_imports':sorted(i-oldi)},ensure_ascii=False,indent=2))

shutil.copy2(base/'work/awdl-held-1153/package.py',out/'package.py')
