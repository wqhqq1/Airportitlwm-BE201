"""Tahoe Bluetooth into the EFI, next to the Sequoia drivers (python3 bluetooth/install_tahoe.py --check | --install).

Copies build/bluetooth-tahoe's BlueToolFixup (2.8.0) and IntelBTPatcher (2.6.0), plus the EFI's own
BE201BluetoothFirmware 2.5.3, as <Name>-Tahoe.kext, with Kernel/Add entries for Darwin 25 only, after the Sequoia
Bluetooth entries (which keep 24.x). Backs up the whole EFI first. Never mounts, reboots or touches NVRAM.
Only the EFI that OpenCore booted from (boot-path partition GUID) is written."""
import hashlib, json, plistlib, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL = json.loads((ROOT/'bluetooth/release.json').read_text())
BACKUPS = ROOT/'outputs/BE201-WiFi/EFI-backups'
OCVALIDATE = ROOT/'deps/ocvalidate'
KMIN, KMAX = '25.0.0', '25.99.99'
# (bundle in the EFI, executable, source bundle, version, comment); in injection order, as the Sequoia entries.
def drivers(efi):
    b, i = REL['bluetoolfixup'], REL['intelbtpatcher']
    return [
        ('IntelBTPatcher-Tahoe.kext', 'IntelBTPatcher', ROOT/'build/bluetooth-tahoe/intelbtpatcher/IntelBTPatcher.kext',
         i['tahoe']['version'], f"IntelBTPatcher {i['tahoe']['version']}: {i['tahoe']['note']}"),
        ('BE201BluetoothFirmware-Tahoe.kext', 'IntelBluetoothFirmware', efi/'OC/Kexts/BE201BluetoothFirmware.kext',
         REL['firmware']['version'], f"BE201BluetoothFirmware {REL['firmware']['version']} (the Sequoia bundle, unchanged): firmware upload for 8087:0037; Tahoe entry"),
        ('BlueToolFixup-Tahoe.kext', 'BlueToolFixup', ROOT/'build/bluetooth-tahoe/bluetoolfixup/BlueToolFixup.kext',
         b['tahoe']['version'], f"BlueToolFixup {b['tahoe']['version']}: {b['tahoe']['note']}"),
    ]

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def boot_efi():
    """The mounted EFI whose partition GUID is in OpenCore's boot-path."""
    path = subprocess.run(['nvram', '4D1FDA02-38C7-4A6A-9CC6-4BCCA8B30102:boot-path'], capture_output=True, text=True).stdout
    m = re.search(r'HD\(\d+,GPT,([0-9A-Fa-f-]{36})', path)
    assert m, 'OpenCore boot-path not found in NVRAM'
    guid = m.group(1).upper()
    for line in subprocess.run(['diskutil', 'list'], capture_output=True, text=True).stdout.splitlines():
        v = line.split()
        if len(v) > 1 and v[1] == 'EFI':
            dev = v[-1]
            info = subprocess.run(['diskutil', 'info', dev], capture_output=True, text=True).stdout
            if guid in info.upper():
                mp = re.search(r'Mount Point:\s+(.+)', info)
                assert mp and mp.group(1).strip(), f'{dev} (the boot EFI) is not mounted: sudo diskutil mount {dev}'
                return dev, Path(mp.group(1).strip())/'EFI'
    raise AssertionError(f'No EFI partition with GUID {guid}')

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else '--check'
    assert mode in ('--check', '--install'), 'usage: install_tahoe.py --check | --install'
    assert int(subprocess.check_output(['uname', '-r'], text=True).split('.')[0]) == 25, 'Run on Tahoe (Darwin 25)'
    dev, efi = boot_efi()
    config = efi/'OC/config.plist'
    c = plistlib.loads(config.read_bytes())
    add = c['Kernel']['Add']
    names = [e['BundlePath'] for e in add]
    assert names.index('Lilu.kext') < names.index('BlueToolFixup.kext'), 'Lilu must come first'
    plan = drivers(efi)
    for bundle, exe, src, ver, _ in plan:
        info = plistlib.loads((src/'Contents/Info.plist').read_bytes())
        assert info['CFBundleVersion'] == ver, f'{src}: {info["CFBundleVersion"]} is not {ver}'
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(src)], check=True)
    if mode == '--check':
        print(f'PASS: boot EFI {dev} at {efi}; ' + ', '.join(f'{b} {v}' for b, _, _, v, _ in plan) + '. No EFI changes.')
        return
    stamp = time.strftime('%Y%m%d-%H%M%S')
    backup = BACKUPS/f'EFI-before-tahoe-bt-{stamp}'
    shutil.copytree(efi, backup/'EFI')
    for bundle, exe, src, ver, _ in plan:
        dst = efi/'OC/Kexts'/bundle
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        assert sha(dst/'Contents/MacOS'/exe) == sha(src/'Contents/MacOS'/exe)
    tahoe = {b for b, *_ in plan}
    add[:] = [e for e in add if e['BundlePath'] not in tahoe]
    at = [e['BundlePath'] for e in add].index('BlueToolFixup.kext') + 1
    for k, (bundle, exe, _, _, comment) in enumerate(plan):
        add.insert(at + k, {'Arch': 'x86_64', 'BundlePath': bundle, 'Comment': comment, 'Enabled': True,
                            'ExecutablePath': 'Contents/MacOS/' + exe, 'MaxKernel': KMAX, 'MinKernel': KMIN,
                            'PlistPath': 'Contents/Info.plist'})
    config.write_bytes(plistlib.dumps(c, sort_keys=False))
    v = subprocess.run([str(OCVALIDATE), str(config)], capture_output=True, text=True)
    if v.returncode != 0:
        shutil.copy2(backup/'EFI/OC/config.plist', config)
        raise SystemExit('ocvalidate failed, config put back:\n' + v.stdout + v.stderr)
    print(json.dumps(dict(efi=str(efi), device=dev, backup=str(backup),
                          installed={b: dict(version=ver, sha256=sha(efi/'OC/Kexts'/b/'Contents/MacOS'/exe)[:16])
                                     for b, exe, _, ver, _ in plan},
                          kernel=f'{KMIN}-{KMAX}', ocvalidate=v.stdout.strip().splitlines()[-1], reboot_required=True),
                     indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
