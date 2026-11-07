"""Read-only LE advertiser evidence, without peer addresses or clipboard contents."""
from pathlib import Path
import subprocess,json,re,datetime,os,collections
from zoneinfo import ZoneInfo
def run(args,timeout=55):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout);return p.returncode,p.stdout.decode(errors='replace')
def collect():
 _,boot=run(['sysctl','-n','kern.bootsessionuuid']);boot=boot.strip().upper()
 _,loaded=run(['kmutil','showloaded','--list-only']);loaded=[s.strip() for s in loaded.splitlines() if any(n in s for n in ['BlueToolFixup','BE201BluetoothFirmware','IntelBTPatcher','AirportItlwm'])]
 _,args=run(['sysctl','-n','kern.bootargs']);flags=[s for s in args.split() if s in ['-be201leadv','-be201identity','-btlfxa2dpcheck']]
 predicate='process == "bluetoothd" AND (category == "Server.LE.Advertise" OR eventMessage CONTAINS "LE_InitMultipleAdvertising")'
 status,raw=run(['/usr/bin/log','show','--last','boot','--style','ndjson','--predicate',predicate]);counts=collections.Counter({k:0 for k in ['records_in_current_boot','initialization_failed','status_152','requests_waiting_for_stack','updates_before_stack_started','advertising_start_success','advertising_start_failed','handoff_payload_requests']});states=collections.Counter();failures=collections.Counter();instances=None;first=last=None
 for line in raw.splitlines():
  try:r=json.loads(line)
  except ValueError:continue
  if r.get('bootUUID','').upper()!=boot:continue
  counts['records_in_current_boot']+=1;first=first or r.get('timestamp');last=r.get('timestamp');s=r.get('eventMessage','')
  if 'Started advertising successfully status=0' in s:counts['advertising_start_success']+=1
  m=re.search(r'Failed to start advertising with result (\d+)',s)
  if m:counts['advertising_start_failed']+=1;failures[m[1]]+=1
  m=re.search(r'Stack supports (\d+) advertising instances',s)
  if m:instances=int(m[1])
  m=re.search(r'manufacturer data \[ ([0-9A-F ]+) \]',s)
  if m:
   payload=bytes.fromhex(m[1])
   if len(payload)>5 and payload[1:5]==bytes.fromhex('ff4c000c'):counts['handoff_payload_requests']+=1
  if 'LE_InitMultipleAdvertising failed' in s:counts['initialization_failed']+=1
  if 'status = 0x0098' in s:counts['status_152']+=1
  if 'Stack is not ready, waiting for the stack to start' in s:counts['requests_waiting_for_stack']+=1
  if 'Stack is not started' in s:counts['updates_before_stack_started']+=1
  m=re.search(r'Advertising state change:\s+(\w+)\((\d+)\)\s+-->\s+(\w+)\((\d+)\)\s+stack:(\w+)',s)
  if m:states['%s(%s) -> %s(%s), stack:%s'%m.groups()]+=1
 return {'time':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'boot_uuid':boot,'loaded':loaded,'local_flags':flags,'candidate_loaded':any('FF68E8F3-BED6-3A1E-B824-CD6A9F93ED40' in s.upper() for s in loaded),'log_command_status':status,'first_record':first,'last_record':last,'counts':dict(counts),'advertising_state_transitions':dict(states),'advertising_start_failure_statuses':dict(failures),'native_advertising_instances':instances,'interpretation':'Stack ON and active-state transitions indicate software progress; actual outgoing Handoff/Clipboard and Bluetooth/Music regression still require device tests. No AWDL/AirDrop completion is inferred.'}
if __name__=='__main__':
 os.umask(0o077);r=collect();p=Path(__file__).resolve().parent/('广播状态-'+datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')+'.json');p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(str(p));print(json.dumps(r,ensure_ascii=False,indent=2))
