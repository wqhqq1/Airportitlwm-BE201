"""Extract fixed public state labels only; never copy identities, QR data or payloads."""
import json, re, sys
from pathlib import Path

def analyze(path):
    events=[]
    for line in Path(path).open():
        try:r=json.loads(line)
        except ValueError:continue
        s=r.get('eventMessage','');value=None
        if 'refreshing PrivateAddressTimer' in s:
            scan=re.search(r'IsScanInProgress=(\d+)',s)
            connect=re.search(r'IsConnectionInProgress=(\d+)',s)
            value={'kind':'rotation_timer','scanning':int(scan[1]) if scan else None,'initiating':int(connect[1]) if connect else None}
        elif 'Advertising stopped due to address change' in s:
            value={'kind':'advertising_stop_notice'}
        elif 'Failed to rotate or change the Address' in s:
            status=re.search(r'STATUS\s+(\d+)',s)
            value={'kind':'rotation_error','native_status':int(status[1]) if status else None}
        elif 'Registering PrivateAddressTimer' in s:
            delay=re.search(r'nextRandomAddressChange=(\d+) seconds',s)
            value={'kind':'rotation_rescheduled','seconds':int(delay[1]) if delay else None}
        if value:
            value['time']=r.get('timestamp');events.append(value)
    return {'events':events,'radio_addresses_exported':False,'authentication_data_exported':False,'notice_is_not_HCI_acknowledgement':True}

if __name__=='__main__':print(json.dumps(analyze(sys.argv[1]),indent=2))
