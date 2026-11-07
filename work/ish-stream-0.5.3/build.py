from pathlib import Path
import subprocess,json
w=Path(__file__).resolve().parent;b=w.parent.parent;sdk=Path('/Users/wqhqq/Documents/Codex/2026-10-30/bang/work/i2c-hid-build/core/MacKernelSDK');bundle=w/'ThinkBookISHProbe.kext'
f=['-target','x86_64-apple-macos10.12','-mkernel','-fno-common','-fno-stack-protector','-mno-red-zone','-nostdinc','-isystem',str(sdk/'Headers'),'-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-O2']
cmds=[['/Library/Developer/CommandLineTools/usr/bin/clang++',*f,'-fapple-kext','-std=gnu++14','-fno-rtti','-fno-exceptions','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation','-c',str(w/'ThinkBookISHProbe.cpp'),'-o',str(w/'probe.o')],['/Library/Developer/CommandLineTools/usr/bin/clang',*f,'-c',str(w/'module.c'),'-o',str(w/'module.o')],['/Library/Developer/CommandLineTools/usr/bin/ld','-kext','-arch','x86_64','-macos_version_min','10.12','-undefined','dynamic_lookup','-no_fixup_chains','-o',str(bundle/'Contents/MacOS/ThinkBookISHProbe'),str(w/'probe.o'),str(w/'module.o'),str(sdk/'Library/x86_64/libkmod.a')]]
for c in cmds:subprocess.run(c,check=True)
(bundle/'Contents/MacOS/ThinkBookISHProbe').chmod(0o755)
(w/'build-commands.json').write_text(json.dumps(cmds,ensure_ascii=False,indent=2)+'\n')
