from pathlib import Path
import subprocess,os,signal,time,datetime,json,shutil
from zoneinfo import ZoneInfo
w=Path(__file__).resolve().parent;root=w.parents[1];appdir=root/'outputs/BE201普通BLE链路测试';stamp=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S');out=w/('central-capture-'+stamp);out.mkdir(mode=0o700)
status=appdir/'普通BLE状态.json'
if status.exists():shutil.copy2(status,out/'before-app.json')
# Only metadata from listed non-authentication HCI operations; no pairing/key commands.
hci=' OR '.join('eventMessage CONTAINS[c] "'+op+'"' for op in ['0x2005','0x200b','0x200c','0x200d','0x200e','0x2016'])
predicate='process == "bluetoothd" AND (category == "Server.LE.Connection" OR (category == "Stack.LE" AND (eventMessage CONTAINS[c] "feature" OR eventMessage CONTAINS[c] "address" OR eventMessage CONTAINS[c] "connect")) OR (category == "Stack.HCI" AND ('+hci+')))'
f=(out/'trace-private.jsonl').open('w');child=subprocess.Popen(['/usr/bin/log','stream','--level','debug','--style','ndjson','--predicate',predicate],stdout=f,stderr=subprocess.DEVNULL)
try:
 for pid in subprocess.run(['pgrep','-u',str(os.getuid()),'-x','BE201BLEProbe'],capture_output=True,text=True).stdout.split():os.kill(int(pid),signal.SIGTERM)
 time.sleep(1)
 subprocess.run(['open','-n',str(appdir/'BE201BLEProbe.app'),'--args','--central'],check=True)
 subprocess.run(['python3',str(root/'outputs/BE201隐私换址广播暂停-2.7.8/collect_link.py')],stdout=(out/'before-hci.txt').open('w'),check=True)
 try:child.wait(timeout=55)
 except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=3)
finally:
 if child.poll() is None:child.terminate();child.wait(timeout=3)
 f.close();(out/'trace-private.jsonl').chmod(0o600)
 if status.exists():shutil.copy2(status,out/'after-app.json')
 subprocess.run(['python3',str(root/'outputs/BE201隐私换址广播暂停-2.7.8/collect_link.py')],stdout=(out/'after-hci.txt').open('w'),check=True)
(w/'central-capture-last').write_text(str(out));print(out)
