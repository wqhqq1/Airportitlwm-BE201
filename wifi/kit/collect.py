"""Read numeric diagnostics and a fixed public TLC snapshot. No system changes."""
from pathlib import Path
import datetime, json, plistlib, subprocess
from zoneinfo import ZoneInfo
from tlc_trace import decode_trace
from join_trace import decode_join_trace
from vif_report import report as vif_report

HERE = Path(__file__).resolve().parent
KIT = json.loads((HERE/'kit.json').read_text())
report = dict(time=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
    boot_uuid=subprocess.check_output(['sysctl','-n','kern.bootsessionuuid'],text=True).strip(),
    model=subprocess.check_output(['sysctl','-n','hw.model'],text=True).strip(),
    read_only=True)
rows = plistlib.loads(subprocess.check_output(['ioreg','-a','-r','-n','pci8086,7740','-l','-w0']))
assert len(rows) == 1
row = rows[0]
report['wifi'] = {k:v for k,v in row.items() if k.startswith(('Itlwm','BE201')) and isinstance(v,(int,bool))}
report['awdl_tx_addr'] = row.get('ItlwmAwdlTxAddr', b'').hex()
blob = row.get('ItlwmTlcFirstFaultTrace')
if blob is None:
    report['tlc'] = dict(present=False, note='No first UMAC error snapshot; this alone is not evidence of successful networking.')
else:
    report['tlc'] = dict(present=True, **decode_trace(blob))
report['join_traces'] = {}
for name in ['FirstFailure','LastFailure','LastSuccess']:
    data = row.get('ItlwmWclJoin'+name)
    if data is not None:
        report['join_traces'][name] = decode_join_trace(data)
for klass in ['BlueToolFixup','IntelBTPatcher']:
    bt = plistlib.loads(subprocess.check_output(['ioreg','-a','-r','-c',klass,'-l','-w0']))
    report[klass] = [{k:v for k,v in r.items() if k.startswith('BE201') and isinstance(v,(int,bool))} for r in bt]
loaded = subprocess.run(['kmutil','showloaded','--list-only'],capture_output=True,text=True)
report['loaded_drivers'] = [s.strip() for s in loaded.stdout.splitlines()
    if any(name+' (' in s for name in ['AirportItlwm','BlueToolFixup','IntelBTPatcher'])]
report['kit_version'] = KIT['version']
report['expected_loaded'] = any(f"AirportItlwm ({KIT['version']})" in s and
    KIT['uuid'].upper() in s.upper() for s in report['loaded_drivers'])
report['feature_results'] = 'Record hotspot activation and actual Wi-Fi joining separately; verify iPhone/iPad Handoff and Watch unlock independently.'
report['awdl_interfaces'] = []
for klass in ['AirportItlwm', 'AirportItlwmAWDLInterface']:
    r = subprocess.run(['ioreg','-a','-r','-c',klass,'-l','-w0'],capture_output=True)
    if r.returncode == 0 and r.stdout:
        for row in plistlib.loads(r.stdout):
            report['awdl_interfaces'].append(dict(klass=klass, properties={k:(v.hex() if isinstance(v,bytes) else v) for k,v in row.items() if k.startswith('ItlwmAwdl') and isinstance(v,(int,bool,str,bytes))}))
report['awdl0_present'] = 'awdl0' in subprocess.check_output(['ifconfig','-l'],text=True).split()
report['feature_results'] = 'Manual arm enables receive-only native AWDL actions. Submitted count is not peer acceptance; TX/data/ranging remain incomplete. Record hotspot/Handoff/Watch separately.'
report['vif_test'] = vif_report(HERE)
p = HERE/('runtime-'+datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')+'.json')
p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); p.chmod(0o600)
print(json.dumps(report,ensure_ascii=False,indent=2))
