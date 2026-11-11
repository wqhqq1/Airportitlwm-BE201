"""Offline Mach-O entry audit. Does not execute or load kernel code."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import uuid


class MachO:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        magic, cpu, subtype, typ, ncmds, size, flags, reserved = struct.unpack_from('<8I', self.data)
        if magic != 0xfeedfacf or cpu != 0x1000007 or typ != 11:
            raise ValueError('Expected a thin x86_64 MH_KEXT_BUNDLE')
        self.sections = []
        self.symbols = {}
        self.uuid = None
        pos = 32
        symtab = None
        for _ in range(ncmds):
            cmd, length = struct.unpack_from('<II', self.data, pos)
            if cmd == 0x19:
                seg = struct.unpack_from('<II16sQQQQIIII', self.data, pos)
                for i in range(seg[-2]):
                    sec = struct.unpack_from('<16s16sQQIIIIIIII', self.data, pos + 72 + 80 * i)
                    self.sections.append({'name': sec[0].rstrip(b'\0').decode(), 'addr': sec[2],
                                          'size': sec[3], 'offset': sec[4], 'type': sec[8] & 0xff})
            elif cmd == 2:
                symtab = struct.unpack_from('<6I', self.data, pos)[2:]
            elif cmd == 0x1b:
                self.uuid = str(uuid.UUID(bytes=self.data[pos + 8:pos + 24]))
            pos += length
        if not symtab:
            raise ValueError('Symbol table required for this audit')
        symoff, count, stroff, strsize = symtab
        for i in range(count):
            nameoff, typ, sec, desc, value = struct.unpack_from('<IBBHQ', self.data, symoff + 16 * i)
            if nameoff and (typ & 0x0e) == 0x0e:
                end = self.data.index(b'\0', stroff + nameoff, stroff + strsize)
                name = self.data[stroff + nameoff:end].decode()
                self.symbols[name] = value

    def pointer(self, name):
        addr = self.symbols[name]
        for s in self.sections:
            if s['addr'] <= addr and addr + 8 <= s['addr'] + s['size']:
                if s['type'] in (1, 0x0c, 0x12):
                    return 0
                return struct.unpack_from('<Q', self.data, s['offset'] + addr - s['addr'])[0]
        raise ValueError(f'No section for {name}')

    def audit(self):
        checks = []
        for pointer, entry in [('__realmain', '__start'), ('__antimain', '__stop')]:
            callback = self.pointer(pointer)
            address = self.symbols[entry]
            checks.append({'pointer': pointer, 'callback': hex(callback), 'entry': entry,
                           'entry_address': hex(address), 'self_reference': callback == address,
                           'null_callback': callback == 0})
        return {'binary': str(self.path.resolve()), 'uuid': self.uuid,
                'sha256': hashlib.sha256(self.data).hexdigest(), 'checks': checks,
                'entry_self_reference_absent': all(not c['self_reference'] for c in checks),
                'no_custom_callbacks': all(c['null_callback'] for c in checks)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('binary')
    ap.add_argument('--report', action='append', default=[])
    args = ap.parse_args()
    m = MachO(args.binary)
    result = m.audit()
    result['snapshot_matches'] = []
    for filename in args.report:
        d = json.loads(Path(filename).read_text().split('\n', 1)[1])
        st = d['stackshot']
        for tid, th in st['processByPid']['0']['threadById'].items():
            frames = th.get('kernelFrames', [])
            if not frames:
                continue
            image, offset = frames[0]
            if st['binaryImages'][image][0].lower() != m.uuid:
                continue
            entries = [c for c in result['checks'] if c['entry'] == '__start']
            start = int(entries[0]['entry_address'], 16)
            # The next defined symbol bounds the entry function in this binary.
            end = min(v for v in m.symbols.values() if v > start)
            waiters = [x for x in st['processByPid']['0'].get('waitInfo', [])
                       if x.endswith('owned by thread ' + tid)]
            result['snapshot_matches'].append({'report': Path(filename).name,
                'thread': tid, 'name': th.get('name'), 'state': th.get('state'),
                'kernel_cpu_seconds': th.get('systemTime'), 'offset': hex(offset),
                'inside_start': start <= offset < end, 'kernel_lock_waiters': len(waiters)})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['entry_self_reference_absent'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
