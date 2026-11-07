# -*- coding: utf-8 -*-
from pathlib import Path
import shutil, zipfile
w=Path(__file__).resolve().parent
o=w.parents[1]/'outputs/BE201连续互通广播修复'
src=o/'source';src.mkdir(exist_ok=True)
for name in ['BlueToolFixup.cpp','BE201Patches.hpp','module.c','build.py','Info.template.plist','patch_test.cpp','deploy.py','restore_advertising.py','collect_advertising.py','LICENSE']:
    shutil.copy2(w/name,src/name)
shutil.copytree(w/'Headers',src/'Headers',dirs_exist_ok=True)
for name in ['entry-audit.json','symbol-check.json','system-binary-verification.json','patch-verification.json','patch-test.txt','build.log','build-commands.json']:
    shutil.copy2(w/name,o/name)
for name in ['restore_advertising.py','collect_advertising.py']:
    shutil.copy2(w/name,o/name)
for name in ['read_system_bt.py','inspect_bluetoothd.py','prepare_legacy_adv.py']:
    shutil.copy2(w.parent/'continuity'/name,src/name)
for name,py in [('恢复广播补丁','restore_advertising.py --restore'),('采集广播状态','collect_advertising.py')]:
    p=o/(name+'.command')
    p.write_text('#!/bin/zsh\nset -eu\ncd -- "${0:A:h}"\n/usr/bin/python3 '+py+'\nprintf "\\nPress Enter to close..."\nread -r\n')
    p.chmod(0o755)
prior=Path('/Users/wqhqq/Documents/Codex/2026-10-30/bang/work')
with zipfile.ZipFile(o/'build-dependencies.zip','w',zipfile.ZIP_DEFLATED) as z:
    for label,p in [('MacKernelSDK',prior/'sources/acidanthera-MacKernelSDK-3f75008'),('Lilu',prior/'native-als/Lilu/Lilu')]:
        for f in sorted(p.rglob('*')):
            if f.is_file() and not any(x in {'.git','build','__pycache__'} for x in f.relative_to(p).parts):
                z.write(f,Path(label)/f.relative_to(p))
print('Package created:',o)
