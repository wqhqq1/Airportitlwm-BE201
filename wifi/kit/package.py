"""Packages build/wifi/AirportItlwm into the one Wi-Fi kit, outputs/BE201-WiFi (KIT_OUT overrides).

Version and config comment come from release.json. The kit's current driver moves to 上一版/ when the version
changes; the installer then expects exactly that driver in the EFI. EFI backups, deployment records and logs stay.
Run build.sh and run_checks.py first."""
from pathlib import Path
import hashlib, json, os, plistlib, shutil, subprocess, sys, tempfile, zipfile

KIT = Path(__file__).resolve().parent
BASE = KIT.parents[1]
REPO = BASE/'wifi/airportbz'
DEPS = BASE/'deps'
BUILD = Path(os.environ.get('BUILD_OUTPUT', BASE/'build/wifi'))
OUT = Path(os.environ.get('KIT_OUT', BASE/'outputs/BE201-WiFi'))
PREV = OUT/'上一版'
REL = json.loads((KIT/'release.json').read_text())
VER = REL['version']
TOOLS = ['audit_entry.py', 'install.py', 'collect.py', 'capture.py', 'conv.py', 'tv3.py', 'view.py', 'tlc_trace.py',
         'join_trace.py', 'vif_report.py', 'record.py', 'stall_history.py', 'roc_test.py',
         '卡顿记录.command', '开始ROC实验.command', '开始抓包.command', '开始记录.command', '采集手机日志.command', '采集重启结果.command',
         '使用与回退.md']
# Bluetooth and the OpenCore binary stay as they are; the installer checks them too.
INFO_NOTE = 'AWDL starts by itself with be201_awdl_auto; own queue with aggregation, solo AWDL and UMI on by default; llw0, second channel and ROC are RAM test switches'

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def kit_version(d):
    p = d/'kit.json'
    return json.loads(p.read_text())['version'] if p.exists() else None

def imports(p):
    return set(x.split()[-1] for x in subprocess.check_output(['nm', '-u', str(p)], text=True).splitlines() if x.strip())

def main():
    checks = json.loads((KIT/'checks.json').read_text())
    assert checks['all_passed'] and checks.get('version') == VER, 'Run run_checks.py for this version first; never package failing checks'
    binary = BUILD/'AirportItlwm'
    assert binary.is_file(), f'No build at {binary}: run build.sh'
    assert VER.encode() + b'\0' in binary.read_bytes(), f'{binary} was not built as {VER}: run build.sh'
    assert (DEPS/'ocvalidate').is_file(), 'deps/ocvalidate (OpenCore 1.0.8) is missing'

    OUT.mkdir(mode=0o700, exist_ok=True)
    current = kit_version(OUT)
    if current and current != VER:
        # A new version: the kit's driver (the one installed last) becomes the previous one.
        if PREV.exists():
            shutil.rmtree(PREV)
        PREV.mkdir(mode=0o700)
        shutil.move(OUT/'AirportItlwm.kext', PREV/'AirportItlwm.kext')
        shutil.move(OUT/'kit.json', PREV/'kit.json')
    assert (PREV/'AirportItlwm.kext').is_dir() and kit_version(PREV), f'{PREV} needs the previous driver and its kit.json'
    old_bin = PREV/'AirportItlwm.kext/Contents/MacOS/AirportItlwm'

    with tempfile.TemporaryDirectory(dir=OUT) as tmp:
        bundle = Path(tmp)/'AirportItlwm.kext'
        shutil.copytree(PREV/'AirportItlwm.kext', bundle)
        shutil.rmtree(bundle/'Contents/_CodeSignature', ignore_errors=True)
        p = bundle/'Contents/Info.plist'
        info = plistlib.loads(p.read_bytes())
        info['CFBundleVersion'] = info['CFBundleShortVersionString'] = VER
        info['BE201LocalBuild'] = INFO_NOTE
        p.write_bytes(plistlib.dumps(info, sort_keys=False))
        shutil.copy2(binary, bundle/'Contents/MacOS/AirportItlwm')
        subprocess.run(['codesign', '--force', '--sign', '-', '--timestamp=none', str(bundle)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
        new_bin = bundle/'Contents/MacOS/AirportItlwm'
        # 1.1.54 was skipped by OpenCore at boot (page gap before __LINKEDIT): never package a layout it rejects.
        subprocess.run([sys.executable, str(REPO/'scripts/oc_layout_check.py'), str(new_bin)], check=True)
        sys.path.insert(0, str(KIT))
        from audit_entry import MachO
        m = MachO(new_bin)
        a = m.audit()
        assert a['entry_self_reference_absent'] and a['no_custom_callbacks']
        sects = {s['name']: s['size'] for s in m.sections if s['name'] in ['__mod_init_func', '__mod_term_func']}
        assert sects == {'__mod_init_func': 64, '__mod_term_func': 64}, sects
        i, oldi = imports(new_bin), imports(old_bin)
        available = {v[-1] for line in (DEPS/'system-symbols-24G824.txt').read_text().splitlines()
                     if len(v := line.split()) >= 3 and v[-2] != 'U'}
        assert not i - available, sorted(i - available)
        assert not oldi - i, sorted(oldi - i)

        sdk = DEPS/'MacKernelSDK'
        manifest = {str(x.relative_to(sdk)): sha(x) for x in sorted(sdk.rglob('*')) if x.is_file()}
        digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        assert digest == (KIT/'sdk-manifest.sha256').read_text().split()[0], 'MacKernelSDK changed'

        # Uncommitted changes (if any) on top of the recorded commit, and every tracked driver file.
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
        patch = subprocess.check_output(['git', 'diff', 'HEAD', '--binary', '--relative'], cwd=REPO)
        archive = Path(tmp)/'对应源码与依赖.zip'
        files = [f for f in subprocess.check_output(['git', 'ls-files', '-z'], cwd=REPO).decode().split('\0') if f]
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in files:
                if (REPO/f).is_file():
                    z.write(REPO/f, 'airportbz/'+f)
            for x in sorted(sdk.rglob('*')):
                if x.is_file():
                    z.write(x, 'dependencies/MacKernelSDK/'+str(x.relative_to(sdk)))
        with zipfile.ZipFile(archive) as z:
            assert len(z.namelist()) == len(set(z.namelist())) and z.testzip() is None

        kit = dict(version=VER, comment=REL['comment'], uuid=a['uuid'],
                   new_binary_sha256=sha(new_bin), old_version=kit_version(PREV), old_binary_sha256=sha(old_bin))
        audit = dict(kit, source_commit=commit, uncommitted_patch_bytes=len(patch),
                     source_archive_sha256=sha(archive), compilation_units=58, constructors=8, destructors=8,
                     import_count=len(i), new_imports=sorted(i - oldi), removed_imports=sorted(oldi - i),
                     sdk_manifest_files=len(manifest), sdk_manifest_sha256=digest,
                     runtime_status='NOT_LOADED until installed and rebooted')

        # Swap in the new driver and regenerate everything else; backups, records and logs stay.
        if (OUT/'AirportItlwm.kext').exists():
            shutil.rmtree(OUT/'AirportItlwm.kext')
        shutil.move(bundle, OUT/'AirportItlwm.kext')
        shutil.move(archive, OUT/'对应源码与依赖.zip')
    (OUT/'source.patch').write_bytes(patch)
    for name, d in [('kit.json', kit), ('build-audit.json', audit), ('entry-audit.json', a)]:
        (OUT/name).write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')
    for n in TOOLS:
        shutil.copy2(KIT/n, OUT/n)
    shutil.copy2(DEPS/'ocvalidate', OUT/'ocvalidate')
    shutil.copy2(KIT/'checks.json', OUT/'checks.json')
    if (OUT/'test-logs').exists():
        shutil.rmtree(OUT/'test-logs')
    shutil.copytree(KIT/'tests', OUT/'test-logs')
    shutil.copy2(REPO/'build/awdl-vif-abi/validation.json', OUT/'awdl-vif-abi.json')
    note = BASE/'docs/wifi'/f'BE201-AWDL-VIF-{VER}.md'
    if note.exists():
        shutil.copy2(note, OUT/'开发与验证说明.md')
    # Configs from an earlier --check belong to the earlier version.
    for p in list(OUT.glob('config-BE201-wifi-*.plist')) + [OUT/'config.pending.plist']:
        p.unlink(missing_ok=True)
    print(json.dumps(dict(kit=str(OUT), **kit, new_imports=audit['new_imports']), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
