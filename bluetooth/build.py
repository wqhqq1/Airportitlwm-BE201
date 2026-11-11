"""Builds the three Bluetooth drivers into build/bluetooth/<folder> and compares each with the binary in the EFI.

Versions, notes and the fixed build date are in release.json. A rebuild of the installed versions is byte-identical
(the installed_sha256 values); after a source change it differs, which is expected. Never installs anything."""
import hashlib, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REL = json.loads((HERE/'release.json').read_text())
names = sys.argv[1:] or ['firmware', 'bluetoolfixup', 'intelbtpatcher']
for name in names:
    r = REL[name]
    subprocess.run([sys.executable, str(HERE/name/'build.py')], check=True, capture_output=True, text=True)
    binary = ROOT/'build/bluetooth'/name/(r['bundle']+'.kext')/'Contents/MacOS'/r['binary']
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    same = digest == r['installed_sha256']
    print(f"{r['bundle']} {r['version']}: {digest[:16]} {'= installed' if same else '!= installed ' + r['installed_sha256'][:16]}")
    print(f"  {binary.parent.parent.parent}")
