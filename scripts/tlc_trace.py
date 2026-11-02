"""Decode only the fixed 548-byte public-capability trace, never arbitrary data."""
import struct

def decode_trace(data):
    if not isinstance(data, bytes) or len(data) != 548:
        raise ValueError('Unknown TLC snapshot size/type')
    magic, version, count, nxt, frozen, eid, d1, cmd, generation = struct.unpack_from('<9I', data)
    if magic != 0x31434c54 or version != 1 or nxt >= 8 or frozen != 1:
        raise ValueError('Unknown TLC snapshot header')
    records = []
    indices = [(nxt+i)%8 for i in range(8)] if count >= 8 else list(range(count))
    for i in indices:
        offset = 36 + i*64
        ordinal, gen, state, flags, width, nss, header, ver, length = struct.unpack_from('<9I', data, offset)
        if ver != 4 or length != 28 or header & 0xffff != 0x050f:
            raise ValueError('Invalid TLC record')
        p = data[offset+36:offset+64]
        records.append(dict(ordinal=ordinal, generation=gen, state=state,
            node_flags=flags, node_width=width, rx_nss=nss, command_header=header,
            same_generation_as_fault=gen == generation,
            exact_fault_header=header == cmd and gen == generation,
            sta_id=p[0], max_width=p[4], mode=p[5], chains=p[6], sgi=p[7],
            flags=struct.unpack_from('<H', p, 8)[0],
            non_ht_rates=struct.unpack_from('<H', p, 10)[0],
            rates=[list(struct.unpack_from('<3H', p, 12)), list(struct.unpack_from('<3H', p, 18))],
            max_mpdu=struct.unpack_from('<H', p, 24)[0], max_tx_op=struct.unpack_from('<H', p, 26)[0]))
    return dict(schema=version, count=count, first_fault=dict(error_id=eid,
        data1=d1, command=cmd, generation=generation), records=records,
        note='Last host command is correlation evidence, not proof that its payload caused the assert.')
