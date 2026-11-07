from pathlib import Path
import subprocess,plistlib,json
w=Path(__file__).resolve().parent
prior=Path('/Users/wqhqq/Documents/Codex/2026-10-30/bang/work')
sdk=prior/'sources/acidanthera-MacKernelSDK-3f75008';lilu=prior/'native-als/Lilu/Lilu'
bundle=w/'BlueToolFixup.kext';(bundle/'Contents/MacOS').mkdir(parents=True,exist_ok=True)
flags=['-target','x86_64-apple-macos10.12','-mkernel','-fno-common','-fno-stack-protector','-mno-red-zone','-nostdinc','-isystem',str(sdk/'Headers'),'-I',str(lilu),'-I',str(w),'-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-DPRODUCT_NAME=BlueToolFixup','-DMODULE_VERSION=2.7.3','-DLILU_CUSTOM_IOKIT_INIT=1','-O2','-Wall','-Wextra','-Wno-unused-parameter','-Wno-unused-variable','-Wno-deprecated-declarations']
cmds=[];objs=[]
for source in [w/'BlueToolFixup.cpp',lilu/'Library/plugin_start.cpp']:
 obj=w/(source.stem+'.o');cmd=['clang++',*flags,'-fapple-kext','-std=gnu++14','-fno-rtti','-fno-exceptions','-c',str(source),'-o',str(obj)];cmds.append(cmd);subprocess.run(cmd,check=True);objs.append(str(obj))
cmd=['clang',*flags,'-c',str(w/'module.c'),'-o',str(w/'module.o')];cmds.append(cmd);subprocess.run(cmd,check=True)
cmd=['ld','-kext','-arch','x86_64','-macos_version_min','10.12','-undefined','dynamic_lookup','-no_fixup_chains','-o',str(bundle/'Contents/MacOS/BlueToolFixup'),*objs,str(w/'module.o'),str(sdk/'Library/x86_64/libkmod.a')];cmds.append(cmd);subprocess.run(cmd,check=True)
d=plistlib.loads(Path('work/research/blue/BlueToolFixup.kext/Contents/Info.plist').read_bytes());d['CFBundleVersion']=d['CFBundleShortVersionString']='2.7.3';d['BE201LocalBuild']='Sequoia 24G824 exact A2DP gate and truthful chipset display'
for k in list(d):
 if k.startswith('DT') or k=='BuildMachineOSBuild':del d[k]
(bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(d,sort_keys=False));(w/'build-commands.json').write_text(json.dumps(cmds,indent=2))
subprocess.run(['codesign','--force','--sign','-','--timestamp=none',str(bundle)],check=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(bundle)],check=True)
