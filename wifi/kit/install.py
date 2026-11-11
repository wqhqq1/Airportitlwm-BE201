"""Surgical Wi-Fi deployment. Never mount, hotload, reboot or change live NVRAM.

The one kit for every version: kit.json names the version and the driver the EFI must hold now (the previous one).
Other sessions edit config.plist too, so only the Wi-Fi row comment, our be201_awdl_* boot arguments and
TakeoffDelay change; the file is written only if it is still exactly what was read."""
from pathlib import Path
import copy, datetime, hashlib, json, os, plistlib, shutil, subprocess, sys
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
UUID = '65EA6FB3-72D2-4697-8E12-8815434C008E'
GUID = '7C436110-AB2A-4BBB-A880-FE41995C9F82'
FLAG = 'be201_tlc_diag=1'
KIT = json.loads((HERE/'kit.json').read_text())
VER = KIT['version']
# Fixed names, replaced on every install: the EFI keeps one previous driver and one set of rollback configs.
RECOVERY = 'AirportItlwm-recovery.kext'
PREFIX = 'config-BE201-wifi-'
ROLLBACK = PREFIX+'rollback.plist'
DISABLED = PREFIX+'WiFi-disabled.plist'
BACKUPS = HERE/'EFI-backups'
RECORDS = HERE/'deployments'

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

def bundle(d):
    rows = [x for x in d['Kernel']['Add'] if x['BundlePath'] == 'AirportItlwm.kext']
    assert len(rows) == 1 and rows[0]['Enabled'] and rows[0]['Arch'] == 'x86_64'
    return rows[0]

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
    active = oc/'Kexts/AirportItlwm.kext'
    stage = oc/'Kexts/AirportItlwm-restore-stage.kext'
    saved = oc/'Kexts/AirportItlwm-restoring.kext'
    assert not stage.exists() and not saved.exists()
    shutil.copytree(backup/'OC/Kexts/AirportItlwm.kext', stage)
    assert manifest(stage) == manifest(backup/'OC/Kexts/AirportItlwm.kext')
    old_config = (oc/'config.plist').read_bytes()
    moved = False
    try:
        active.rename(saved)
        moved = True
        stage.rename(active)
        atomic(oc/'config.plist', (backup/'OC/config.plist').read_bytes())
        validate(oc/'config.plist')
        assert manifest(active) == manifest(backup/'OC/Kexts/AirportItlwm.kext')
        assert (oc/'config.plist').read_bytes() == (backup/'OC/config.plist').read_bytes()
        assert disk()[0] == efi
    except BaseException:
        if moved:
            if active.exists():
                shutil.rmtree(active)
            saved.rename(active)
        atomic(oc/'config.plist', old_config)
        raise
    shutil.rmtree(saved)
    subprocess.run(['/bin/sync'], check=True)
    print('Restored previous Wi-Fi and original config for the next reboot; Bluetooth and SMBIOS preserved.')

def main():
    mode = sys.argv[1] if len(sys.argv) == 2 else '--check'
    assert mode in ['--check', '--install', '--restore']
    assert subprocess.check_output(['sw_vers', '-buildVersion'], text=True).strip() == '24G824'
    assert subprocess.check_output(['uname', '-m'], text=True).strip() == 'x86_64'
    if mode == '--restore':
        return restore()
    efi, device, store = disk()
    oc = efi/'OC'
    cfg = oc/'config.plist'
    original = cfg.read_bytes()
    old = plistlib.loads(original)
    assert old['PlatformInfo']['Generic']['SystemProductName'] == 'MacBookPro16,2'
    active = oc/'Kexts/AirportItlwm.kext'
    recovery = oc/'Kexts'/RECOVERY
    stage = oc/'Kexts/AirportItlwm-stage.kext'
    retired = oc/'Kexts/AirportItlwm-recovery-old.kext'
    source = HERE/'AirportItlwm.kext'
    assert sha(source/'Contents/MacOS/AirportItlwm') == KIT['new_binary_sha256']
    now = sha(active/'Contents/MacOS/AirportItlwm')
    if now == KIT['new_binary_sha256']:
        print(f'{VER} is already in the EFI; nothing to do.')
        return
    assert now == KIT['old_binary_sha256'], f"The EFI driver is not {KIT['old_version']}, the one this kit replaces; package against it first"

    for p in [source, active]:
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(p)], check=True)
    assert not stage.exists() and not retired.exists()
    if recovery.exists():
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(recovery)], check=True)
    # Explicitly guard the working Bluetooth pair in addition to the full manifest.
    for name, digest in [
        ('BlueToolFixup', '8e9f2d5c18de0bb974d9f257e33441b11442f100d4c07bd2f719b0461a1b1a05'),
        ('IntelBTPatcher', '29cccca596800c1a80644feeb2efda558a895681b430df79c9239c29b1f8bc50')]:
        assert sha(oc/'Kexts'/(name+'.kext')/'Contents/MacOS'/name) == digest
    new = copy.deepcopy(old)
    row = bundle(new)
    old_comment = row.get('Comment', '')
    row['Comment'] = f"BE201 {VER}: {KIT['comment']}"
    orig_args = old['NVRAM']['Add'][GUID]['boot-args']
    args = ' '.join(a for a in orig_args.split() if not a.startswith('be201_awdl_'))
    assert FLAG in args.split()
    assert 'boot-args' in old['NVRAM']['Delete'][GUID]
    assert 'be201_awdl_probe' not in args
    assert 'be201_awdl_tx' not in args
    assert 'be201_awdl_ctx' not in args
    # Keep the order when ours are already there as wanted: another session appends its own arguments (1.1.86).
    wanted_awdl = ['be201_awdl_vif=1', 'be201_awdl_auto=1']
    have_awdl = [a for a in orig_args.split() if a.startswith('be201_awdl_')]
    new['NVRAM']['Add'][GUID]['boot-args'] = orig_args if have_awdl == wanted_awdl else args + ' ' + ' '.join(wanted_awdl)
    assert old['Misc']['Boot']['TakeoffDelay'] in (10000, 100000)
    new['Misc']['Boot']['TakeoffDelay'] = 100000
    audit = copy.deepcopy(new)
    bundle(audit)['Comment'] = old_comment
    audit['Misc']['Boot']['TakeoffDelay'] = old['Misc']['Boot']['TakeoffDelay']
    audit['NVRAM']['Add'][GUID]['boot-args'] = orig_args
    assert audit == old, 'Unexpected config mutation'
    rb, off = copy.deepcopy(old), copy.deepcopy(old)
    rb['NVRAM']['Add'][GUID]['boot-args'] = off['NVRAM']['Add'][GUID]['boot-args'] = args
    bundle(rb)['BundlePath'] = RECOVERY
    bundle(off)['Enabled'] = False
    probe_off = copy.deepcopy(new)
    probe_off['NVRAM']['Add'][GUID]['boot-args'] = args
    group_only = copy.deepcopy(new)
    group_only['NVRAM']['Add'][GUID]['boot-args'] = args + ' be201_awdl_vif=1 be201_awdl_if=1'
    rx_only = copy.deepcopy(new)
    rx_only['NVRAM']['Add'][GUID]['boot-args'] = args + ' be201_awdl_ctx=6'
    model_back = copy.deepcopy(new)
    model_back['PlatformInfo']['Generic']['SystemProductName'] = 'MacPro7,1'
    versions = {PREFIX+'macpro.plist': model_back, 'config.plist': new, ROLLBACK: rb, DISABLED: off, PREFIX+'off.plist': probe_off, PREFIX+'rxonly.plist': rx_only, PREFIX+'capability.plist': group_only}
    validation = {}
    for name, d in versions.items():
        p = HERE/('config.pending.plist' if name == 'config.plist' else name)
        p.write_bytes(plistlib.dumps(d, sort_keys=False))
        p.chmod(0o600)
        validation[name] = validate(p)
    validate(cfg)
    if mode == '--check':
        print(f"PASS: signed Wi-Fi {VER} over {KIT['old_version']}, working Bluetooth, same-disk EFI, surgical config and recovery configs. No EFI changes.")
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
    shutil.copytree(source, stage)
    assert manifest(stage) == manifest(source)
    expected = before | {str(p.relative_to(efi)): sha(p) for p in stage.rglob('*') if p.is_file()}
    moved = False
    had_recovery = recovery.exists()
    written = {}
    try:
        assert manifest(efi) == expected and cfg.read_bytes() == original and disk()[0] == efi
        if had_recovery:
            recovery.rename(retired)
        active.rename(recovery)
        moved = True
        stage.rename(active)
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
        assert all(k in ['OC/'+n for n in versions] or k.startswith(('OC/Kexts/AirportItlwm.kext/', 'OC/Kexts/'+RECOVERY+'/', 'OC/Kexts/'+retired.name+'/')) for k in changes)
        assert manifest(active) == manifest(source)
        assert manifest(recovery) == manifest(backup/'EFI/OC/Kexts/AirportItlwm.kext')
        assert cfg.read_bytes() == (HERE/'config.pending.plist').read_bytes() and disk()[0] == efi
        for name in versions:
            validate(oc/name)
    except BaseException:
        if moved:
            if active.exists():
                shutil.rmtree(active)
            recovery.rename(active)
        if had_recovery and retired.exists() and not recovery.exists():
            retired.rename(recovery)
        for p, data in written.items():
            if data is None:
                p.unlink(missing_ok=True)
            else:
                atomic(p, data)
        # Restore only our own write: a file another session wrote meanwhile stays.
        if cfg.read_bytes() == (HERE/'config.pending.plist').read_bytes() and cfg.read_bytes() != original:
            atomic(cfg, original)
        if stage.exists():
            shutil.rmtree(stage)
        raise
    if retired.exists():
        shutil.rmtree(retired)
        subprocess.run(['/bin/sync'], check=True)
        after = manifest(efi)
        changes = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    report = dict(version=VER, replaced=KIT['old_version'], time=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        efi_uuid=UUID, efi_device=device, macos_store=store, backup=str(backup),
        before_manifest=before, after_manifest=after, changed_paths=changes,
        validation=validation, config_changes=['Wi-Fi comment; AWDL RF probe/context/TX flags removed; AWDL starts by itself each boot through be201_awdl_auto=1, test switches off'],
        bluetooth_unchanged=True, smbios_unchanged=True, root_patches=False,
        live_nvram_write=False, driver_hotloaded=False, reboot_required=True)
    (RECORDS/('deployment-'+stamp+'.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ['before_manifest','after_manifest','validation','changed_paths']}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
