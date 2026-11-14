"""Build the offline freestanding x86_64 routing module for one bluetoothd build; never installs or loads it.

2.7.13: `build(defines, payload_vm, state_vm, out)` takes the native addresses port.py located (AuthenticatedRPA.cpp's
BE201_* macros) and where the payload and state go. Without arguments it builds 24G824's, into this folder, as before."""
from pathlib import Path
import subprocess, struct, json, hashlib, sys
W = Path(__file__).resolve().parent
sys.path.insert(0, str(W.parents[1]/'deps/python'))  # capstone 5.0.9
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86_const import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP

FLAGS = ['-std=c++17', '-arch', 'x86_64', '-Oz', '-ffreestanding', '-fno-builtin',
         '-fno-stack-protector', '-fno-exceptions', '-fno-rtti', '-fvisibility=hidden',
         '-fvisibility-inlines-hidden', '-Wall', '-Wextra', '-Werror']
G824 = dict(payload_vm=0x1009d9a10, state_vm=0x100a69f00, defines={})
PAYLOAD_MAX = 0x5f0


def build(defines, payload_vm, state_vm, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    flags = FLAGS + [f'-D{k}={v:#x}' for k, v in sorted(defines.items())] + [f'-DBE201_STATE={state_vm:#x}']
    subprocess.run(['clang++', *flags, '-c', str(W/'AuthenticatedRPA.cpp'), '-o', str(out/'authenticated-rpa.o')], check=True)
    subprocess.run(['ld', '-static', '-arch', 'x86_64', '-e', '_BE201ResolveRPA', '-no_uuid',
                    '-o', str(out/'authenticated-rpa.macho'), str(out/'authenticated-rpa.o')], check=True)
    b = (out/'authenticated-rpa.macho').read_bytes(); at = 32; sections = []; symbols = {}; relocations = 0; dependencies = []
    for _ in range(struct.unpack_from('<I', b, 16)[0]):
        cmd, n = struct.unpack_from('<II', b, at)
        if cmd == 0x19:
            for i in range(struct.unpack_from('<I', b, at + 64)[0]):
                s = at + 72 + i * 80; name = b[s:s + 16].rstrip(b'\0').decode(); vm, size = struct.unpack_from('<QQ', b, s + 32)
                off = struct.unpack_from('<I', b, s + 48)[0]
                relocations += struct.unpack_from('<I', b, s + 60)[0]; sections.append({'name': name, 'vm': vm, 'size': size, 'offset': off})
        if cmd == 2: symoff, nsyms, stroff, strsize = struct.unpack_from('<IIII', b, at + 8)
        if cmd in (0xc, 0x80000018, 0x8000001f): dependencies.append(cmd)
        at += n
    for i in range(nsyms):
        strx, t, sect, desc, value = struct.unpack_from('<IBBHQ', b, symoff + 16 * i)
        name = b[stroff + strx:b.index(0, stroff + strx)].decode()
        assert not (t & 0xe == 0 and name), ('undefined', name)
        if name.startswith('_BE201'): symbols[name] = value
    text = next(x for x in sections if x['name'] == '__text'); assert relocations == 0 and not dependencies
    assert all(x['name'] == '__text' or x['size'] == 0 for x in sections), sections
    code = b[text['offset']:text['offset'] + text['size']]; md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True
    instructions = list(md.disasm(code, text['vm'])); assert sum(i.size for i in instructions) == len(code)
    for i in instructions:
        for op in i.operands:
            if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
                assert text['vm'] <= i.address + i.size + op.mem.disp < text['vm'] + len(code), 'external RIP-relative data'
        if (i.mnemonic == 'call' or i.mnemonic.startswith('j')) and i.operands[0].type == X86_OP_IMM:
            assert text['vm'] <= i.operands[0].imm < text['vm'] + len(code), 'external direct branch'
    marker = bytes(16)
    preferred = payload_vm + len(marker) + symbols['_BE201ResolveRPA'] - text['vm']
    sentinel = struct.pack('<Q', 0xBE201BE201BE201B); assert code.count(sentinel) == 1
    code = code.replace(sentinel, struct.pack('<Q', preferred))
    marker = hashlib.sha256(code).digest()[:8] + bytes(8)
    payload = marker + code
    assert len(payload) <= PAYLOAD_MAX, ('payload does not fit', len(payload))
    (out/'authenticated-rpa-code.bin').write_bytes(code)
    (out/'authenticated-rpa-payload.bin').write_bytes(payload)
    layout = {'text': text, 'entries': symbols, 'relocations': relocations, 'dependencies': dependencies,
              'code_sha256': hashlib.sha256(code).hexdigest(), 'preferred_entry': preferred, 'payload_vm': payload_vm,
              'payload_size': len(payload), 'state_vm': state_vm, 'state_size': 232,
              'defines': {k: hex(v) for k, v in sorted(defines.items())}}
    (out/'authenticated-rpa-layout.json').write_text(json.dumps(layout, indent=2) + '\n')
    manifest = {'clang': subprocess.check_output(['clang++', '--version'], text=True).splitlines()[0],
                'compiler_flags': flags, 'instructions': len(instructions), 'code_size': len(code), 'undefined_symbols': [],
                'all_direct_branches_internal': True, 'external_rip_data': False, 'deployment': False}
    (out/'authenticated-rpa-build.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return layout, payload


if __name__ == '__main__':
    layout, payload = build(G824['defines'], G824['payload_vm'], G824['state_vm'], W)
    print('PASS: authenticated recent RPA routing module (24G824);', layout['payload_size'] - 16,
          'bytes, no imports, dependencies, data sections, external RIP references or external direct branches.',
          'code', layout['code_sha256'][:16])
