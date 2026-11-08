from pathlib import Path
import subprocess,plistlib,shutil,sys,hashlib,json,zipfile,os
# Run from the project root. Since 2026-11-07 work/airportbz lives inside the one project repository.
base=Path.cwd(); repo=base/'work/airportbz'; tools=base/'work/awdl-tid-1157'
old=base/'outputs/BE201AWDL队列重试-1.1.56'; out=base/'outputs/BE201AWDL切网修正-1.1.57'
VER,OLDVER,PREFIX,OLDPREFIX='1.1.57','1.1.56','awdltid','awdlretry'
assert json.loads((tools/'checks.json').read_text())['all_passed'], 'Do not package failing checks'
out.mkdir(mode=0o700); bundle=out/'AirportItlwm.kext';shutil.copytree(old/'AirportItlwm.kext',bundle)
p=bundle/'Contents/Info.plist';info=plistlib.loads(p.read_bytes());info['CFBundleVersion']=info['CFBundleShortVersionString']=VER
info['BE201LocalBuild']='AWDL starts by itself with be201_awdl_auto; own queue with aggregation on by default; second channel is a RAM test switch'
p.write_bytes(plistlib.dumps(info,sort_keys=False))
shutil.copy2(base/'work/be201-awdl-tid57-build/AirportItlwm',bundle/'Contents/MacOS/AirportItlwm')
subprocess.run(['codesign','--force','--sign','-','--timestamp=none',str(bundle)],check=True);subprocess.run(['codesign','--verify','--deep','--strict',str(bundle)],check=True)
# 1.1.54 was skipped by OpenCore at boot (page gap before __LINKEDIT): never package a layout it rejects.
subprocess.run([sys.executable,str(repo/'scripts/oc_layout_check.py'),str(bundle/'Contents/MacOS/AirportItlwm')],check=True)
shutil.copy2(old/'audit_entry.py',out/'audit_entry.py');sys.path.insert(0,str(out));from audit_entry import MachO
m=MachO(bundle/'Contents/MacOS/AirportItlwm');a=m.audit();assert a['entry_self_reference_absent'] and a['no_custom_callbacks']
sects={s['name']:s['size'] for s in m.sections if s['name'] in ['__mod_init_func','__mod_term_func']};assert sects=={'__mod_init_func':64,'__mod_term_func':64},sects
imports=lambda p:set(x.split()[-1] for x in subprocess.check_output(['nm','-u',str(p)],text=True).splitlines() if x.strip())
i=imports(m.path);oldi=imports(old/'AirportItlwm.kext/Contents/MacOS/AirportItlwm')
available={v[-1] for line in (base/'work/research/system-symbols.txt').read_text().splitlines() if len(v:=line.split())>=3 and v[-2]!='U'}
assert not i-available,sorted(i-available);assert not oldi-i,sorted(oldi-i)
# The SDK manifest and SDK archive come from the previous kit (the 1.1.0 kit they first came from was cleaned up).
sdk=base/'work/airportbz-deps/MacKernelSDK'
manifest={str(p.relative_to(sdk)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sdk.rglob('*') if p.is_file()}
assert manifest==json.loads((old/'sdk-manifest.json').read_text()) and len(manifest)==1232
with zipfile.ZipFile(old/'对应源码与依赖.zip') as oz: sdkzip=oz.read('dependencies/MacKernelSDK.zip')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
note=f'BE201-AWDL-VIF-{VER}.md'
subprocess.run(['git','add','-N',note],cwd=repo,check=True)
# Changes since the last commit, with paths relative to work/airportbz.
patch=subprocess.check_output(['git','diff','HEAD','--binary','--relative'],cwd=repo);(out/f'source-{VER}.patch').write_bytes(patch)
archive=out/'对应源码与依赖.zip';files=subprocess.check_output(['git','ls-files','-z'],cwd=repo).split(b'\0')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for f in files:
  if f and (repo/f.decode()).is_file():z.write(repo/f.decode(),'airportbz/'+f.decode())
 z.writestr('dependencies/MacKernelSDK.zip',sdkzip)
with zipfile.ZipFile(archive) as z:assert len(z.namelist())==len(set(z.namelist())) and z.testzip() is None
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
b=json.loads((old/'build-audit.json').read_text());b.update(version=VER,old_binary_sha256=sha(old/'AirportItlwm.kext/Contents/MacOS/AirportItlwm'),new_binary_sha256=sha(m.path),uuid=a['uuid'],source_commit=commit+f' + source-{VER}.patch (uncommitted)',source_patch_sha256=sha(out/f'source-{VER}.patch'),source_archive_sha256=sha(archive),runtime_status='NOT_LOADED; AWDL auto start with own queue and aggregation on by default; second channel automatic choice and own-slot windows are RAM test switches',compilation_units=58,compile_units=58,constructors=8,destructors=8,import_count=len(i),import_set_unchanged=(i==oldi),native_imports=len(i),new_imports=sorted(i-oldi),removed_imports=sorted(oldi-i),missing_imports=[],sdk_manifest_files=len(manifest))
for name,d in [('build-audit.json',b),('entry-audit.json',a),('sdk-manifest.json',manifest)]: (out/name).write_text(json.dumps(d,indent=2)+'\n')
for n in ['record.py','开始记录.command','channel_test.py','开始信道实验.command','airdrop_test.py','开始隔空投送实验.command']:
 shutil.copy2(tools/n,out/n)
for n in ['ocvalidate','tlc_trace.py','join_trace.py','conv.py','tv3.py','view.py','采集手机日志.command','capture.py','开始抓包.command']:shutil.copy2(old/n,out/n)
s=(old/'install.py').read_text()
assert s.count("row['Comment'] = 'BE201 1.1.56: AWDL starts by itself each boot, AirDrop speed-up on; second channel, UMI and llw0 test switches off'")==1
s=s.replace(OLDPREFIX,PREFIX).replace(OLDVER,VER)
assert OLDPREFIX not in s and OLDVER not in s and f'config-BE201-{PREFIX}-capability.plist' in s and "== 'MacBookPro16,2'" in s
(out/'install.py').write_text(s)
s=(old/'collect.py').read_text()
s=s.replace('expected_1_1_56_loaded','expected_1_1_57_loaded').replace('AirportItlwm (1.1.56)','AirportItlwm (1.1.57)').replace(json.loads((old/'build-audit.json').read_text())['uuid'].upper(),a['uuid'].upper())
assert 'vif_report(HERE)' in s and 'r.returncode == 0 and r.stdout' in s and 'expected_1_1_57_loaded' in s and 'p.chmod(0o600)' in s
(out/'collect.py').write_text(s)
(out/'采集重启结果.command').write_text('#!/bin/zsh\ncd -- "${0:A:h}" || exit 1\n/usr/bin/python3 collect.py\n');(out/'采集重启结果.command').chmod(0o700)
shutil.copy2(repo/note,out/'开发与验证说明.md')
shutil.copy2(tools/'vif_report.py',out/'vif_report.py')
shutil.copy2(tools/'checks.json',out/'checks.json');shutil.copytree(tools/'tests',out/'test-logs')
shutil.copy2(repo/'build/awdl-vif-abi/validation.json',out/'awdl-vif-abi.json')
shutil.copy2(tools/'使用与回退.md',out/'使用与回退.md')
shutil.copy2(tools/'package.py',out/'package.py')
print(json.dumps({'kit':str(out),'uuid':a['uuid'],'sha256':b['new_binary_sha256'],'imports':len(i),'compilation_units':58,'new_imports':sorted(i-oldi)},ensure_ascii=False,indent=2))
