"""Read-only BE201 BLE submission counters; no addresses or credentials."""
from pathlib import Path
import subprocess,plistlib,json,datetime,os
from zoneinfo import ZoneInfo
def run(args):
 p=subprocess.run(args,capture_output=True,timeout=30);return p.stdout if p.returncode==0 else b''
def collect():
 nodes=plistlib.loads(run(['/usr/sbin/ioreg','-r','-c','IntelBTPatcher','-a']) or b'<?xml version="1.0"?><plist version="1.0"><array/></plist>')
 def walk(nodes):
  for n in nodes:
   yield n;yield from walk(n.get('IORegistryEntryChildren',[]))
 props={k:v for n in walk(nodes) for k,v in n.items() if k.startswith('BE201BLE') and isinstance(v,(str,bool,int))}
 loaded=[s.strip() for s in run(['/usr/bin/kmutil','showloaded','--list-only']).decode().splitlines() if any(x in s for x in ['IntelBTPatcher','BE201BluetoothFirmware','BlueToolFixup','AirportItlwm'])]
 return {'time':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'boot_uuid':run(['/usr/sbin/sysctl','-n','kern.bootsessionuuid']).decode().strip(),'loaded':loaded,'candidate_loaded':any('3F17F797-F283-3150-ABAF-16F80264E386' in s.upper() for s in loaded),'properties':props,'semantics':'Observed USB command submissions and transport return values, not HCI completion or actual RF success. Addresses, keys and payloads are not retained.','hotspot_fix_claimed':False}
if __name__=='__main__':
 os.umask(0o077);d=collect();p=Path(__file__).resolve().parent/('BLE状态-'+datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')+'.json');p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(str(p));print(json.dumps(d,ensure_ascii=False,indent=2))
