"""Read-only verification; no raw peer addresses, keys, activity or clipboard data."""
from pathlib import Path
import json,subprocess,re,collections,datetime,os
from zoneinfo import ZoneInfo
from read_system_bt import read_verified
W=Path(__file__).resolve().parent
UUID='c6100b60-4cd7-3c12-ad29-8891ee8868b3'
def run(args):
 r=subprocess.run(args,capture_output=True,text=True,timeout=55);return r.returncode,r.stdout

def collect():
 boot=run(['sysctl','-n','kern.bootsessionuuid'])[1].strip().upper()
 loaded=run(['kmutil','showloaded','--list-only'])[1]
 flags=run(['sysctl','-n','kern.bootargs'])[1].split()
 try:
  _,verification=read_verified(W/'BE201Patches.hpp');patch_seen='0x68f059' in verification['cache_patch_sites_restored']
 except Exception as e:verification={'error':str(e)};patch_seen=False
 pred='process == "bluetoothd" AND (eventMessage CONTAINS "Outgoing LE Connection complete" OR eventMessage CONTAINS "supportsVAPairing" OR eventMessage CONTAINS "VSC failed") OR ((process == "rapportd" OR process == "sharingd") AND eventMessage CONTAINS "com.sharing.hotspot.request")'
 status,raw=run(['/usr/bin/log','show','--last','boot','--info','--style','ndjson','--predicate',pred]);counts=collections.Counter();last=None
 for line in raw.splitlines():
  try:r=json.loads(line)
  except ValueError:continue
  if r.get('bootUUID','').upper()!=boot:continue
  m=r.get('eventMessage','');last=r.get('timestamp')
  if 'Outgoing LE Connection complete' in m:
   n=re.search(r'with status (\d+)',m)
   if n:counts['outgoing_completion_status_'+n[1]]+=1
  if 'supportsVAPairing:NO' in m:counts['single_address_lookup_candidates']+=1
  if 'supportsVAPairing:YES' in m:counts['multiple_address_lookup_candidates']+=1
  if 'VSC failed' in m:counts['vendor_command_failures']+=1
  if 'com.sharing.hotspot.request' in m:
   if 'BLE client connect timeout' in m:counts['hotspot_ble_timeout_records']+=1
   elif 'error:' in m or 'Abort' in m:counts['hotspot_error_records']+=1
 return {'time':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'boot_uuid':boot,'candidate_loaded':UUID.upper() in loaded.upper(),'loaded':[l.strip() for l in loaded.splitlines() if any(x in l for x in ['BlueToolFixup','IntelBTPatcher','AirportItlwm','BE201BluetoothFirmware'])],'peer_flag':'-be201peeraddr' in flags,'kernel_extra_probe_flag':'-be201btprobe' in flags,'peer_patch_in_code_cache':patch_seen,'verified_system_binary':verification,'log_status':status,'last_record':last,'counts':dict(counts),'limits':'Patch presence is not proof every request takes the fallback or that radio/authentication succeeds. Status702 follows cancellation in prior evidence. Hotspot and bidirectional Handoff require user verification.'}
if __name__=='__main__':
 os.umask(0o077);r=collect();p=W/('对端地址状态-'+datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')+'.json');p.write_text(json.dumps(r,ensure_ascii=False,indent=2));print(p);print(json.dumps(r,ensure_ascii=False,indent=2))
