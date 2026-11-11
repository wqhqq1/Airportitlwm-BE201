"""Decode only the fixed 548-byte public-capability trace, never arbitrary data."""
import struct

def decode_trace(data):
    if not isinstance(data, bytes) or len(data) != 548:
        raise ValueError('Unknown TLC snapshot size/type')
    magic, version, count, nxt, frozen, eid, d1, cmd, generation = struct.unpack_from('<9I', data)
    if magic != 0x31434c54 or version not in (1, 2) or nxt >= 8 or frozen != 1 or not eid:
        raise ValueError('Unknown TLC snapshot header')
    if count < 8 and nxt != count:
        raise ValueError('Invalid ring position')
    records = []
    indices = [(nxt+i)%8 for i in range(8)] if count >= 8 else list(range(count))
    for i in indices:
        offset = 36 + i*64
        ordinal, gen, state, flags, width, nss, header, ver, length = struct.unpack_from('<9I', data, offset)
        tlc = ver == 4 and length == 28 and header & 0xffff == 0x050f
        link = version == 2 and ver == 2 and length == 208 and header & 0xffff == 0x0309
        if not (tlc or link):
            raise ValueError('Invalid TLC record')
        p = data[offset+36:offset+64]
        record = dict(ordinal=ordinal, generation=gen, state=state,
            node_flags=flags, node_width=width, rx_nss=nss, command_header=header,
            same_generation_as_fault=gen == generation,
            exact_fault_header=header == cmd and gen == generation)
        if link:
            record['kind'] = 'LINK_CONFIG v2 (seven numeric fields only)'
            record['link'] = dict(zip(['action','link_id','mac_id','phy_id','modify_mask','active','listen_lmac'], struct.unpack('<7I',p)))
            records.append(record)
            continue
        record.update(dict(kind='TLC_CONFIG v4',
            sta_id=p[0], max_width=p[4], mode=p[5], chains=p[6], sgi=p[7],
            flags=struct.unpack_from('<H', p, 8)[0],
            non_ht_rates=struct.unpack_from('<H', p, 10)[0],
            rates=[list(struct.unpack_from('<3H', p, 12)), list(struct.unpack_from('<3H', p, 18))],
            max_mpdu=struct.unpack_from('<H', p, 24)[0], max_tx_op=struct.unpack_from('<H', p, 26)[0]))
        records.append(record)
    return dict(schema=version, count=count, first_fault=dict(error_id=eid,
        data1=d1, command=cmd, generation=generation), records=records,
        note='Last host command is correlation evidence, not proof that its payload caused the assert.')
