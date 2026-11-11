from pathlib import Path
import subprocess,plistlib,json,shutil
import os
# Dependencies from deps/, output to build/bluetooth/firmware (README.md). The version is in Info.plist.
w=Path(__file__).resolve().parent;s=w/'src';root=w.parents[1]
sdk=Path(os.environ.get('MAC_KERNEL_SDK',str(root/'deps/MacKernelSDK-3f75008')))
out=Path(os.environ.get('BUILD_OUTPUT',str(root/'build/bluetooth'/w.name)));out.mkdir(parents=True,exist_ok=True)
bundle=out/'BE201BluetoothFirmware.kext';(bundle/'Contents/MacOS').mkdir(parents=True,exist_ok=True)
fw=[];descs=[]
for i,p in enumerate(sorted(x for x in (w/'fw').iterdir() if x.suffix in ('.sfi','.ddc'))):
 b=p.read_bytes();fw.append('static const unsigned char data%d[]={%s};'%(i,','.join('0x%02x'%v for v in b)))
 descs.append('{"%s",data%d,%d}'%(p.name,i,len(b)))
(s/'FirmwareData.cpp').write_text('#include "FwData.h"\n'+'\n'.join(fw)+'\nconst FwDesc fwList[]={'+','.join(descs)+'};\nconst int fwNumber=2;\n')
flags=['-target','x86_64-apple-macos10.12','-mkernel','-fno-common','-fno-stack-protector','-mno-red-zone','-nostdinc','-isystem',str(sdk/'Headers'),'-I',str(s),'-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-O2','-Wall','-Wextra','-Wno-unused-parameter','-Wno-unused-variable','-Wno-sign-compare','-Wno-deprecated-declarations','-Wno-missing-field-initializers']
cmds=[];objs=[]
for p in sorted(s.glob('*.cpp')):
 o=out/(p.stem+'.o');cmd=['clang++',*flags,'-fapple-kext','-std=gnu++14','-fno-rtti','-fno-exceptions','-c',str(p),'-o',str(o)];cmds.append(cmd);subprocess.run(cmd,check=True);objs.append(str(o))
cmd=['clang',*flags,'-c',str(w/'module.c'),'-o',str(out/'module.o')];cmds.append(cmd);subprocess.run(cmd,check=True)
cmd=['ld','-kext','-arch','x86_64','-macos_version_min','10.12','-undefined','dynamic_lookup','-no_fixup_chains','-o',str(bundle/'Contents/MacOS/IntelBluetoothFirmware'),*objs,str(out/'module.o'),str(sdk/'Library/x86_64/libkmod.a')];cmds.append(cmd);subprocess.run(cmd,check=True)
shutil.copy2(w/'Info.plist',bundle/'Contents/Info.plist');(out/'build-commands.json').write_text(json.dumps(cmds,indent=2))
subprocess.run(['codesign','--force','--sign','-','--timestamp=none',str(bundle)],check=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(bundle)],check=True)
