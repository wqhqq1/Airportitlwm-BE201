from pathlib import Path
import subprocess,plistlib,json,shutil
w=Path(__file__).resolve().parent;s=w/'src'
sdk=Path('/Users/wqhqq/Documents/Codex/2026-10-30/bang/work/sources/acidanthera-MacKernelSDK-3f75008')
bundle=w/'BE201BluetoothFirmware.kext';(bundle/'Contents/MacOS').mkdir(parents=True,exist_ok=True)
fw=[];descs=[]
for i,p in enumerate(sorted((w/'fw').iterdir())):
 b=p.read_bytes();fw.append('static const unsigned char data%d[]={%s};'%(i,','.join('0x%02x'%v for v in b)))
 descs.append('{"%s",data%d,%d}'%(p.name,i,len(b)))
(s/'FirmwareData.cpp').write_text('#include "FwData.h"\n'+'\n'.join(fw)+'\nconst FwDesc fwList[]={'+','.join(descs)+'};\nconst int fwNumber=2;\n')
flags=['-target','x86_64-apple-macos10.12','-mkernel','-fno-common','-fno-stack-protector','-mno-red-zone','-nostdinc','-isystem',str(sdk/'Headers'),'-I',str(s),'-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-O2','-Wall','-Wextra','-Wno-unused-parameter','-Wno-unused-variable','-Wno-sign-compare','-Wno-deprecated-declarations','-Wno-missing-field-initializers']
cmds=[];objs=[]
for p in sorted(s.glob('*.cpp')):
 o=w/(p.stem+'.o');cmd=['clang++',*flags,'-fapple-kext','-std=gnu++14','-fno-rtti','-fno-exceptions','-c',str(p),'-o',str(o)];cmds.append(cmd);subprocess.run(cmd,check=True);objs.append(str(o))
cmd=['clang',*flags,'-c',str(w/'module.c'),'-o',str(w/'module.o')];cmds.append(cmd);subprocess.run(cmd,check=True)
cmd=['ld','-kext','-arch','x86_64','-macos_version_min','10.12','-undefined','dynamic_lookup','-no_fixup_chains','-o',str(bundle/'Contents/MacOS/IntelBluetoothFirmware'),*objs,str(w/'module.o'),str(sdk/'Library/x86_64/libkmod.a')];cmds.append(cmd);subprocess.run(cmd,check=True)
shutil.copy2(w/'Info.plist',bundle/'Contents/Info.plist');(w/'build-commands.json').write_text(json.dumps(cmds,indent=2))
subprocess.run(['codesign','--force','--sign','-','--timestamp=none',str(bundle)],check=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(bundle)],check=True)
