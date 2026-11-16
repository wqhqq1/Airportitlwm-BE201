"""Tahoe Wi-Fi into the EFI (python3 wifi/kit/install_tahoe_wifi.py --check | --install).

STALE since 2026-11-15 11:58: written for the 1.4.2 install (fallback 1.3.2). The user restored the 06:43 config and
1.4.3/1.4.4 were installed by hand with minimal edits (see docs/BE201-TAHOE-PREP.md); --install rewrites the Wi-Fi
entries and config-fallback.plist, so do not run it on the current config without updating it first.

--install copies build/wifi-tahoe/AirportItlwm.kext as AirportItlwm-Tahoe.kext, the 25.x entry right after
AirportItlwm-BZ-Tahoe-backup.kext (which stays off: same bundle identifier), and writes EFI/OC/config-fallback.plist:
the same config with only that entry pointing at AirportItlwm-Tahoe-1.3.2.kext, an exact copy of the 1.3.2 that last
booted. If the new version does not boot, copy config-fallback.plist over config.plist (from Recovery) and reboot.
Leftovers of the 1.4.0 install (AirportItlwm-Tahoe-prev.kext, its entry, BE201-wifi-previous.sh) are removed.
Backs up the whole EFI first and writes only the EFI OpenCore booted from (bluetooth/install_tahoe.py boot_efi).
Never mounts, reboots or touches NVRAM."""
import copy, hashlib, importlib.util, json, plistlib, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('bt_install', ROOT/'bluetooth/install_tahoe.py')
bt = importlib.util.module_from_spec(spec); spec.loader.exec_module(bt)
SOURCE = ROOT/'build/wifi-tahoe/AirportItlwm.kext'
KNOWN_GOOD = ROOT/'build/wifi-tahoe/AirportItlwm-1.3.2.kext'
KNOWN_GOOD_SHA = '7c08e4115445baa7'
NEW, GOOD, OLD = 'AirportItlwm-Tahoe.kext', 'AirportItlwm-Tahoe-1.3.2.kext', 'AirportItlwm-BZ-Tahoe-backup.kext'
LEFTOVER = 'AirportItlwm-Tahoe-prev.kext'
VERSION = '1.4.2'
COMMENT = (f'V{VERSION} | BE201 {VERSION} Tahoe: 1.3.2 (hotspot fixes) plus the AWDL interface built for 25G342; AWDL is '
           'not started at boot yet, only by the step-by-step test after login; IO80211Buffer calls are virtual (25G342 malloc buffers; 1.4.1 panicked in getCapacity); '
           'fallback: copy EFI/OC/config-fallback.plist over config.plist (1.3.2)')
GOOD_COMMENT = 'V1.3.2 | BE201 1.3.2 Tahoe, known good (hotspot works, no AWDL); this is config-fallback.plist'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
version_of = lambda kext: plistlib.loads((kext/'Contents/Info.plist').read_bytes())['CFBundleVersion']


def validate(path):
    v = subprocess.run([str(bt.OCVALIDATE), str(path)], capture_output=True, text=True)
    return v.returncode == 0, (v.stdout + v.stderr).strip().splitlines()[-1]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else '--check'
    assert mode in ('--check', '--install'), __doc__
    assert int(subprocess.check_output(['uname', '-r'], text=True).split('.')[0]) == 25, 'Run on Tahoe (Darwin 25)'
    dev, efi = bt.boot_efi()
    config, fallback, kexts = efi/'OC/config.plist', efi/'OC/config-fallback.plist', efi/'OC/Kexts'
    c = plistlib.loads(config.read_bytes()); add = c['Kernel']['Add']
    assert OLD in [e['BundlePath'] for e in add], f'{OLD} entry not found'
    assert version_of(SOURCE) == VERSION, version_of(SOURCE)
    assert version_of(KNOWN_GOOD) == '1.3.2' and sha(KNOWN_GOOD/'Contents/MacOS/AirportItlwm')[:16] == KNOWN_GOOD_SHA
    for k in (SOURCE, KNOWN_GOOD):
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(k)], check=True)
    state = lambda d: {e['BundlePath']: e['Enabled'] for e in d['Kernel']['Add'] if 'AirportItlwm' in e['BundlePath']}
    if mode == '--check':
        print(f'PASS: boot EFI {dev} at {efi}; {VERSION} and 1.3.2 ready; now {state(c)}. No EFI changes.')
        return
    backup = bt.BACKUPS/f'EFI-before-tahoe-wifi-{time.strftime("%Y%m%d-%H%M%S")}'
    shutil.copytree(efi, backup/'EFI')
    for name, src in ((NEW, SOURCE), (GOOD, KNOWN_GOOD)):
        dst = kexts/name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        assert sha(dst/'Contents/MacOS/AirportItlwm') == sha(src/'Contents/MacOS/AirportItlwm')
    old = next(e for e in add if e['BundlePath'] == OLD)
    add[:] = [e for e in add if e['BundlePath'] not in (NEW, GOOD, LEFTOVER)]
    entry = {**{k: old[k] for k in old}, 'BundlePath': NEW, 'Comment': COMMENT, 'Enabled': True,
             'ExecutablePath': 'Contents/MacOS/AirportItlwm', 'MinKernel': '25.0.0', 'MaxKernel': '25.99.99',
             'PlistPath': 'Contents/Info.plist'}
    add.insert([e['BundlePath'] for e in add].index(OLD) + 1, entry)
    old['Enabled'] = False
    f = copy.deepcopy(c)
    good = next(e for e in f['Kernel']['Add'] if e['BundlePath'] == NEW)
    good.update(BundlePath=GOOD, Comment=GOOD_COMMENT)
    config.write_bytes(plistlib.dumps(c, sort_keys=False))
    fallback.write_bytes(plistlib.dumps(f, sort_keys=False))
    results = {p.name: validate(p) for p in (config, fallback)}
    if not all(ok for ok, _ in results.values()):
        shutil.copy2(backup/'EFI/OC/config.plist', config)
        fallback.unlink()
        raise SystemExit(f'ocvalidate failed, config put back: {results}')
    if (kexts/LEFTOVER).exists():
        shutil.rmtree(kexts/LEFTOVER)
    script = efi.parent/'BE201-wifi-previous.sh'
    if script.exists():
        script.unlink()
    print(json.dumps(dict(efi=str(efi), device=dev, backup=str(backup), sha256=sha(kexts/NEW/'Contents/MacOS/AirportItlwm')[:16],
                          config=state(c), fallback=state(f), ocvalidate={k: v for k, (_, v) in results.items()},
                          reboot_required=True), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
