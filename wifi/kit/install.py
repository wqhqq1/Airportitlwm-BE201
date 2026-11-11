"""Surgical Wi-Fi and Bluetooth deployment. Never mount, hotload, reboot or change live NVRAM.

The one kit for every version. kit.json names, for each driver it carries, the version and the binary the EFI must hold
now (the previous one): AirportItlwm, BlueToolFixup and IntelBTPatcher. BE201BluetoothFirmware stays as it is.

Other sessions edit config.plist too, so only these change: the three drivers' row comments, our boot arguments
(since 1.1.88 the BE201 switches are on without boot arguments, so ours are removed) and TakeoffDelay. The file is
written only if it is still exactly what was read.

  --check            verify everything and write the configs here; no EFI change
  --install          back up the whole EFI, then install
  --restore          put back the drivers and config from the last install's backup
  --watch-unlock     Apple Watch unlock without ranging (this driver has no FTM ranging): run as your own user
  --watch-unlock-undo  turn ranging back on"""
from pathlib import Path
import copy, datetime, hashlib, json, os, plistlib, shutil, subprocess, sys
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
UUID = '65EA6FB3-72D2-4697-8E12-8815434C008E'
GUID = '7C436110-AB2A-4BBB-A880-FE41995C9F82'
KIT = json.loads((HERE/'kit.json').read_text())
VER = KIT['version']
# The verified build. Any macOS 15.2 or later Sequoia installs; AWDL is on by default only on this build.
VERIFIED_BUILD = '24G824'
# Boot arguments that 1.1.88 / 2.7.12 / 2.5.10 no longer need: the drivers behave as if they were set.
DEFAULT_ARGS = ['-btlfxa2dpcheck', '-be201identity', '-be201leadv', '-be201addrpause', '-be201lebaseline',
                '-be201nativeaddr', '-be201btprobe', '-be201rparoute',
                'be201_tlc_diag=1', 'be201_awdl_vif=1', 'be201_awdl_auto=1']
# Old experiment switches that must not come back.
RETIRED_ARGS = ('be201_awdl_probe', 'be201_awdl_tx', 'be201_awdl_ctx', 'be201_awdl_if')
# Stays as it is; kit.json carries the binary the EFI must hold (bluetooth/release.json installed_sha256).
FIRMWARE = ('BE201BluetoothFirmware', 'IntelBluetoothFirmware')
# Fixed names, replaced on every install: the EFI keeps one previous copy of each driver and one set of configs.
PREFIX = 'config-BE201-wifi-'
ROLLBACK = PREFIX+'rollback.plist'
BACKUPS = HERE/'EFI-backups'
RECORDS = HERE/'deployments'
WATCH = ['defaults', 'write', 'com.apple.sharingd', 'phoneAutoUnlockSkipRanging', '-bool', 'true']
WATCH_UNDO = ['defaults', 'delete', 'com.apple.sharingd', 'phoneAutoUnlockSkipRanging']


def drivers():
    """(name, executable, entry from kit.json) for every driver this kit replaces."""
    out = [('AirportItlwm', 'AirportItlwm', dict(version=VER, comment=f"BE201 {VER}: {KIT['comment']}",
                                                  new_binary_sha256=KIT['new_binary_sha256'],
                                                  old_binary_sha256=KIT['old_binary_sha256']))]
    for name, d in KIT.get('bluetooth', {}).items():
        out.append((name, name, dict(d, comment=f"{name} {d['version']}: {d['note']}")))
    return out


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def manifest(p):
    assert not any(x.is_symlink() for x in p.rglob('*')), 'Unexpected symlink'
    return {str(x.relative_to(p)): sha(x) for x in p.rglob('*') if x.is_file()}

def info(p):
    return plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', p]))

def disk():
    e, r = info(UUID), info('/')
    assert e['DiskUUID'] == UUID and e.get('MountPoint') and e['WritableVolume'], 'Authorized EFI must be mounted writable'
    stores = [info(x['APFSPhysicalStore']) for x in r['APFSPhysicalStores']]
    assert len(stores) == 1 and stores[0]['ParentWholeDisk'] == e['ParentWholeDisk'], 'EFI/macOS physical disk mismatch'
    return Path(e['MountPoint'])/'EFI', e['DeviceIdentifier'], stores[0]['DeviceIdentifier']

def validate(p):
    r = subprocess.run([str(HERE/'ocvalidate'), str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout + r.stderr

def atomic(p, data):
    stage = p.with_name(p.name+'.hotspot-staged')
    assert not stage.exists()
    stage.write_bytes(data)
    os.replace(stage, p)

def bundle(d, name):
    rows = [x for x in d['Kernel']['Add'] if x['BundlePath'] == name+'.kext']
    assert len(rows) == 1 and rows[0]['Enabled'] and rows[0]['Arch'] == 'x86_64', name
    return rows[0]

def system():
    """Any Sequoia from 15.2 on (the Wi-Fi driver refuses older kernels); returns the build."""
    product = subprocess.check_output(['sw_vers', '-productVersion'], text=True).strip()
    build = subprocess.check_output(['sw_vers', '-buildVersion'], text=True).strip()
    parts = [int(x) for x in product.split('.')[:2]] + [0]
    assert parts[0] == 15 and parts[1] >= 2, f'macOS {product}: these drivers need macOS Sequoia 15.2 or later'
    assert subprocess.check_output(['uname', '-m'], text=True).strip() == 'x86_64'
    return product, build


def watch(undo):
    """Apple Watch unlock: sharingd skips ranging, leaving the Bluetooth signal-strength check (less strict)."""
    assert os.geteuid() != 0, 'Run --watch-unlock as your own user, not with sudo: it is a per-user setting'
    r = subprocess.run(WATCH_UNDO if undo else WATCH, capture_output=True, text=True)
    assert r.returncode == 0 or undo, r.stderr
    subprocess.run(['killall', 'sharingd'], capture_output=True)
    print('Watch unlock ranging is back on.' if undo else
          'Watch unlock now skips ranging (only the Bluetooth signal check remains). Undo: install.py --watch-unlock-undo')

def watch_state():
    r = subprocess.run(['defaults', 'read', 'com.apple.sharingd', 'phoneAutoUnlockSkipRanging'], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == '1'


def restore():
    efi, _, _ = disk()
    reports = sorted(RECORDS.glob('deployment-*.json'))
    assert reports, 'No completed deployment record'
    report = json.loads(reports[-1].read_text())
    assert manifest(efi) == report['after_manifest'], 'EFI changed since installation; refusing to overwrite later work'
    backup = Path(report['backup'])
    if not backup.exists():
        backup = BACKUPS/backup.name
    backup = backup/'EFI'
    assert manifest(backup) == report['before_manifest']
    oc = efi/'OC'
    names = report.get('drivers', ['AirportItlwm'])
    old_config = (oc/'config.plist').read_bytes()
    moved = []
    try:
        for name in names:
            active, stage, saved = oc/'Kexts'/(name+'.kext'), oc/'Kexts'/(name+'-restore-stage.kext'), oc/'Kexts'/(name+'-restoring.kext')
            assert not stage.exists() and not saved.exists()
            shutil.copytree(backup/'OC/Kexts'/(name+'.kext'), stage)
            assert manifest(stage) == manifest(backup/'OC/Kexts'/(name+'.kext'))
            active.rename(saved)
            moved.append(name)
            stage.rename(active)
        atomic(oc/'config.plist', (backup/'OC/config.plist').read_bytes())
        validate(oc/'config.plist')
        for name in names:
            assert manifest(oc/'Kexts'/(name+'.kext')) == manifest(backup/'OC/Kexts'/(name+'.kext'))
        assert disk()[0] == efi
    except BaseException:
        for name in moved:
            active, saved = oc/'Kexts'/(name+'.kext'), oc/'Kexts'/(name+'-restoring.kext')
            if active.exists():
                shutil.rmtree(active)
            saved.rename(active)
        atomic(oc/'config.plist', old_config)
        raise
    for name in names:
        shutil.rmtree(oc/'Kexts'/(name+'-restoring.kext'))
    subprocess.run(['/bin/sync'], check=True)
    print('Restored the previous drivers and config for the next reboot; BE201BluetoothFirmware and SMBIOS preserved.')


def main():
    mode = sys.argv[1] if len(sys.argv) == 2 else '--check'
    assert mode in ['--check', '--install', '--restore', '--watch-unlock', '--watch-unlock-undo']
    if mode.startswith('--watch-unlock'):
        return watch(mode.endswith('undo'))
    product, build = system()
    if mode == '--restore':
        return restore()
    efi, device, store = disk()
    oc = efi/'OC'
    cfg = oc/'config.plist'
    original = cfg.read_bytes()
    old = plistlib.loads(original)
    assert old['PlatformInfo']['Generic']['SystemProductName'] == 'MacBookPro16,2'
    plan = []
    for name, exe, d in drivers():
        p = dict(name=name, exe=exe, d=d, source=HERE/(name+'.kext'), active=oc/'Kexts'/(name+'.kext'),
                 recovery=oc/'Kexts'/(name+'-recovery.kext'), stage=oc/'Kexts'/(name+'-stage.kext'),
                 retired=oc/'Kexts'/(name+'-recovery-old.kext'))
        assert sha(p['source']/'Contents/MacOS'/exe) == d['new_binary_sha256'], name
        p['now'] = sha(p['active']/'Contents/MacOS'/exe)
        plan.append(p)
    if all(p['now'] == p['d']['new_binary_sha256'] for p in plan):
        print(f'{VER} and its Bluetooth drivers are already in the EFI; nothing to do.')
        return
    for p in plan:
        assert p['now'] in (p['d']['old_binary_sha256'], p['d']['new_binary_sha256']), \
            f"The EFI {p['name']} is neither {p['d'].get('old_version', 'the previous version')} nor this one; package against it first"
    plan = [p for p in plan if p['now'] != p['d']['new_binary_sha256']]
    for p in plan:
        for x in [p['source'], p['active']]:
            subprocess.run(['codesign', '--verify', '--deep', '--strict', str(x)], check=True)
        assert not p['stage'].exists() and not p['retired'].exists(), p['name']
        if p['recovery'].exists():
            subprocess.run(['codesign', '--verify', '--deep', '--strict', str(p['recovery'])], check=True)
    fw, fwexe = FIRMWARE
    assert sha(oc/'Kexts'/(fw+'.kext')/'Contents/MacOS'/fwexe) == KIT['firmware_sha256'], 'BE201BluetoothFirmware changed'

    new = copy.deepcopy(old)
    old_comments = {}
    for p in plan:
        row = bundle(new, p['name'])
        old_comments[p['name']] = row.get('Comment', '')
        row['Comment'] = p['d']['comment']
    orig_args = old['NVRAM']['Add'][GUID]['boot-args']
    assert 'boot-args' in old['NVRAM']['Delete'][GUID]
    assert not any(a.startswith(RETIRED_ARGS) for a in orig_args.split()), orig_args
    # Keep every other argument in its place (another session appends its own); drop only the now-default ones.
    args = ' '.join(a for a in orig_args.split() if a not in DEFAULT_ARGS)
    new['NVRAM']['Add'][GUID]['boot-args'] = args
    assert old['Misc']['Boot']['TakeoffDelay'] in (10000, 100000)
    new['Misc']['Boot']['TakeoffDelay'] = 100000
    audit = copy.deepcopy(new)
    for name, comment in old_comments.items():
        bundle(audit, name)['Comment'] = comment
    audit['Misc']['Boot']['TakeoffDelay'] = old['Misc']['Boot']['TakeoffDelay']
    audit['NVRAM']['Add'][GUID]['boot-args'] = orig_args
    assert audit == old, 'Unexpected config mutation'

    # Rollback: the config as it was, with the previous drivers under their recovery names.
    rb = copy.deepcopy(old)
    for p in plan:
        bundle(rb, p['name'])['BundlePath'] = p['recovery'].name
    awdl_off = copy.deepcopy(new)
    awdl_off['NVRAM']['Add'][GUID]['boot-args'] = (args + ' be201_awdl_vif=0').strip()
    bt_stock = copy.deepcopy(new)
    bt_stock['NVRAM']['Add'][GUID]['boot-args'] = (args + ' -be201btstock').strip()
    wifi_off = copy.deepcopy(new)
    bundle(wifi_off, 'AirportItlwm')['Enabled'] = False
    model_back = copy.deepcopy(new)
    model_back['PlatformInfo']['Generic']['SystemProductName'] = 'MacPro7,1'
    versions = {'config.plist': new, ROLLBACK: rb, PREFIX+'off.plist': awdl_off, PREFIX+'btstock.plist': bt_stock,
                PREFIX+'WiFi-disabled.plist': wifi_off, PREFIX+'macpro.plist': model_back}
    validation = {}
    for name, d in versions.items():
        f = HERE/('config.pending.plist' if name == 'config.plist' else name)
        f.write_bytes(plistlib.dumps(d, sort_keys=False))
        f.chmod(0o600)
        validation[name] = validate(f)
    validate(cfg)
    note = '' if build == VERIFIED_BUILD else f' AWDL stays off by default on {build} (verified on {VERIFIED_BUILD}).'
    watch_note = '' if watch_state() else ' Apple Watch unlock needs: python3 install.py --watch-unlock (as your user).'
    if mode == '--check':
        print(f"PASS: macOS {product} ({build}); signed {', '.join(p['name']+' '+p['d']['version'] for p in plan)}; "
              f"same-disk EFI, surgical config, recovery configs. No EFI changes.{note}{watch_note}")
        return

    before = manifest(efi)
    stamp = datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')
    BACKUPS.mkdir(mode=0o700, exist_ok=True)
    RECORDS.mkdir(mode=0o700, exist_ok=True)
    backup = BACKUPS/('EFI-before-install-'+stamp)
    backup.mkdir(mode=0o700)
    shutil.copytree(efi, backup/'EFI')
    assert manifest(backup/'EFI') == before and manifest(efi) == before
    assert cfg.read_bytes() == original and disk()[0] == efi
    expected = dict(before)
    for p in plan:
        shutil.copytree(p['source'], p['stage'])
        assert manifest(p['stage']) == manifest(p['source'])
        expected |= {str(x.relative_to(efi)): sha(x) for x in p['stage'].rglob('*') if x.is_file()}
    done, written = [], {}
    try:
        assert manifest(efi) == expected and cfg.read_bytes() == original and disk()[0] == efi
        for p in plan:
            p['had_recovery'] = p['recovery'].exists()
            if p['had_recovery']:
                p['recovery'].rename(p['retired'])
            p['active'].rename(p['recovery'])
            done.append(p)
            p['stage'].rename(p['active'])
        for name in versions:
            if name != 'config.plist':
                written[oc/name] = (oc/name).read_bytes() if (oc/name).exists() else None
                atomic(oc/name, (HERE/name).read_bytes())
        # Another session may edit config.plist too: write only over the exact file read above, else stop unchanged.
        if cfg.read_bytes() != original:
            raise RuntimeError('config.plist changed during install (another session?): config not written, run --install again')
        atomic(cfg, (HERE/'config.pending.plist').read_bytes())
        subprocess.run(['/bin/sync'], check=True)
        after = manifest(efi)
        changes = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
        allowed = tuple('OC/Kexts/'+x+'/' for p in plan for x in [p['active'].name, p['recovery'].name, p['retired'].name])
        assert all(k in ['OC/'+n for n in versions] or k.startswith(allowed) for k in changes), changes
        for p in plan:
            assert manifest(p['active']) == manifest(p['source'])
            assert manifest(p['recovery']) == manifest(backup/'EFI/OC/Kexts'/p['active'].name)
        assert cfg.read_bytes() == (HERE/'config.pending.plist').read_bytes() and disk()[0] == efi
        for name in versions:
            validate(oc/name)
    except BaseException:
        for p in reversed(done):
            if p['active'].exists():
                shutil.rmtree(p['active'])
            p['recovery'].rename(p['active'])
            if p['had_recovery'] and p['retired'].exists():
                p['retired'].rename(p['recovery'])
        for p in plan:
            if p['stage'].exists():
                shutil.rmtree(p['stage'])
        for f, data in written.items():
            if data is None:
                f.unlink(missing_ok=True)
            else:
                atomic(f, data)
        # Restore only our own write: a file another session wrote meanwhile stays.
        if cfg.read_bytes() == (HERE/'config.pending.plist').read_bytes() and cfg.read_bytes() != original:
            atomic(cfg, original)
        raise
    retired = [p['retired'] for p in plan if p['retired'].exists()]
    for r in retired:
        shutil.rmtree(r)
    if retired:
        subprocess.run(['/bin/sync'], check=True)
        after = manifest(efi)
        changes = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    report = dict(version=VER, drivers=[p['name'] for p in plan],
        replaced={p['name']: p['d'].get('old_version') for p in plan},
        installed={p['name']: p['d']['version'] for p in plan},
        system=dict(product=product, build=build), time=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        efi_uuid=UUID, efi_device=device, macos_store=store, backup=str(backup),
        before_manifest=before, after_manifest=after, changed_paths=changes, validation=validation,
        config_changes=['row comments of the installed drivers', 'boot-args: removed now-default ' + ' '.join(a for a in orig_args.split() if a in DEFAULT_ARGS), 'TakeoffDelay 100000'],
        boot_args_before=orig_args, boot_args_after=args,
        firmware_unchanged=True, smbios_unchanged=True, root_patches=False,
        live_nvram_write=False, driver_hotloaded=False, reboot_required=True)
    (RECORDS/('deployment-'+stamp+'.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in ['before_manifest', 'after_manifest', 'validation', 'changed_paths']}, ensure_ascii=False, indent=2))
    if note or watch_note:
        print((note + watch_note).strip())

if __name__ == '__main__':
    main()
