#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export MAC_KERNEL_SDK="${MAC_KERNEL_SDK:-$ROOT/../MacKernelSDK}"
cd "$ROOT"
python3 - <<'PY'
from pathlib import Path
import hashlib, shutil
dest=Path('build/firmware-be201');dest.mkdir(parents=True,exist_ok=True)
expected={
 'iwlwifi-bz-b0-fm-c0-92.ucode':'820f9fb78e43b424befdc2d9253e2b56f9d2bb250d8a42217d9bb1d8b6d7957d',
 'iwlwifi-bz-b0-fm-c0.pnvm':'2da92f02418fbde8d8210eb582d9697faa222f8ee2da229e29b8a108ea5c4c5c'}
assert set(p.name for p in dest.iterdir()) <= set(expected),'Unexpected firmware in BE201 build directory'
for name,digest in expected.items():
 source=Path('firmware-bz92')/name
 assert hashlib.sha256(source.read_bytes()).hexdigest()==digest,name
 shutil.copy2(source,dest/name)
PY
python3 scripts/zlib_compress_fw.py include/FwBinary.cpp build/firmware-be201
bash scripts/build-sequoia-macos.sh
