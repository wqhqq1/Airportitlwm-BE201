"""Strict reader for the fixed public numeric-only WCL join snapshot."""
import struct
FIELDS = 'magic version request starts status reason driver_status state node_flags assoc beacon port channel akm cipher proto eapol badmic replay deauth key_cipher rsn_length deferred'.split()
EVENTS = {1:'msg1_enter',2:'msg2_send_attempt',3:'msg2_call_returned',4:'msg3_enter',5:'msg3_mic_verified',6:'msg3_decrypted_or_plain',7:'msg4_send_attempt',8:'msg4_send_returned_zero',9:'ptk_install_attempt',10:'ptk_install_accepted_or_deferred',11:'gtk_install_attempt',13:'igtk_install_attempt',15:'port_valid',16:'local_msg3_deauth',17:'remote_deauth_reason',18:'remote_address_match_mask',19:'association_status',20:'link_change',21:'foreign_teardown_ignored',22:'msg2_submitted_to_firmware',23:'msg2_firmware_tx_status',24:'msg4_firmware_tx_status',25:'msg4_submitted_to_firmware'}
def decode_join_trace(blob):
    if not isinstance(blob,bytes) or len(blob)!=360:raise ValueError('Expected 360-byte join snapshot')
    values=struct.unpack('<90I',blob)
    out=dict(zip(FIELDS,values[:23]));enabled,count,nxt=values[23:26]
    if out.pop('magic')!=0x314e4f4a or out['version']!=1:raise ValueError('Unknown join snapshot ABI')
    if enabled!=1 or nxt>=32 or (count<0xffffffff and nxt!=count%32):raise ValueError('Invalid event ring')
    if any(out[k]>1 for k in ['assoc','beacon','port','deferred']):raise ValueError('Invalid boolean')
    if out['state']>4 or out['rsn_length']>257:raise ValueError('Invalid metadata')
    pairs=list(zip(values[26::2],values[27::2]));size=min(count,32)
    indices=range(size) if count<32 else [(nxt+i)%32 for i in range(32)]
    events=[]
    for i in indices:
        code,value=pairs[i]
        if code not in EVENTS:raise ValueError('Unknown numeric event')
        events.append(dict(code=code,event=EVENTS[code],value=value))
    if count<32 and any(c or v for c,v in pairs[size:]):raise ValueError('Nonzero unused ring entries')
    out.update(event_count=count,events=events)
    out['interpretation']='Message submission is not proof of airtime delivery or peer acceptance. Match mask: bit0 destination=current local MAC, bit1 sender=current peer MAC, bit2 BSSID=current peer BSSID. Deferred snapshots omit the previous peer trace. Counters are cumulative within this boot.'
    return out
