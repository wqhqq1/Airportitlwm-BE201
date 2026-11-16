"""Compile-only Tahoe (25G342) AWDL ABI fixture. Never link/load this fixture as a kext.

Compiles AirportItlwmAWDLInterface.cpp for __IO80211_TARGET 260000 with clang's vtable dump and checks:
- every one of the 568 IO80211AWDLProtocol slots in AirportItlwmAWDLInterface against the 25G342 boot KC
  (tests/abi/tahoe-25G342-awdl.json): native overrides by name, the 63 AWDL handlers by their 24G824
  order moved 5 slots, slot 488 as setMacAddress;
- the 505 IO80211VirtualInterface slots of AirportItlwmLowLatencyInterface the same way;
- every undefined symbol of the object against the 25G342 boot KC exports.
Usage: MAC_KERNEL_SDK=... NATIVE_KERNEL_SYMBOLS=outputs/tahoe-wifi/kc-symbols-25G342.txt python3 ..."""
from pathlib import Path
import os, json, re, subprocess, hashlib
root = Path(__file__).resolve().parents[1]
out = root / 'build/awdl-vif-abi-tahoe'; out.mkdir(parents=True, exist_ok=True)
native = json.loads((root / 'tests/abi/tahoe-25G342-awdl.json').read_text())
sdk = Path(os.environ['MAC_KERNEL_SDK'])
source = out / 'fixture.cpp'; source.write_text('#include "AirportItlwmAWDLInterface.cpp"\n')
flags = ['-target', 'x86_64-apple-macos26.0', '-mkernel', '-fapple-kext',
         '-fno-sized-deallocation', '-fno-use-cxa-atexit', '-fno-exceptions', '-fno-rtti',
         '-mno-red-zone', '-mcmodel=kernel', '-nostdinc', '-std=gnu++14', '-D__PRIVATE_SPI__',
         '-DKERNEL', '-DKERNEL_PRIVATE', '-DDRIVER_PRIVATE', '-DIEEE80211_STA_ONLY',
         '-DAIRPORT', '-DAIRPORT_WCL', '-DAIRPORT_VTD', '-DIO80211FAMILY_V2', '-D__IO80211_TARGET=260000',
         '-isystem', str(sdk / 'Headers'),
         '-isystem', subprocess.check_output(['clang', '-print-resource-dir'], text=True).strip() + '/include']
for p in ['.', 'itlwm', 'itlwm/hal_iwx', 'itl80211', 'itl80211/openbsd', 'itl80211/linux', 'include', 'include/Airport', 'AirportItlwm']:
    flags += ['-I', str(root / p)]
flags += ['-include', str(root / 'itlwm/PrivateSPI.pch'), '-Wno-deprecated-register', '-Wno-multichar']
with (out / 'clang-vtables.txt').open('w') as f:
    rc = subprocess.run(['clang++', *flags, '-Xclang', '-fdump-vtable-layouts', '-c', str(source), '-o', str(out / 'fixture.o')],
                        stdout=f, stderr=subprocess.STDOUT)
text = (out / 'clang-vtables.txt').read_text()
if rc.returncode:
    print(text[-10000:]); raise SystemExit(rc.returncode)

def table(cls):
    start = text.index(f"Vtable for '{cls}'"); end = text.find('\nVtable for ', start + 1)
    return text[start:end if end >= 0 else len(text)]
headers = '\n'.join(p.read_text() for p in (root / 'include/Airport/macOS26').glob('*.h'))
alias_pairs = re.findall(r'void (\w+)\(\) __asm__\("([^"]+)"\)', headers)
alias_names = subprocess.check_output(['c++filt', '-n'], input='\n'.join(m[1:] for _, m in alias_pairs) + '\n', text=True).splitlines()
aliases = {a: d.split('::', 1)[1].split('(')[0] for (a, _), d in zip(alias_pairs, alias_names)}
handlers = {m['slot']: m['name'] for m in native['methods']}

def check(cls, slots):
    t = table(cls)
    demangled = subprocess.check_output(['c++filt', '-n'], input='\n'.join(r['symbol'][1:] for r in slots) + '\n', text=True).splitlines()
    # Slots after the native ones are the concrete class's own virtuals; native code never calls them.
    for i, (r, d) in enumerate(zip(slots, demangled)):
        line = re.search(r'^\s*' + str(i + 2) + r' \| (.*)$', t, re.M)
        assert line, (cls, i, r)
        got = line[1].split('::', 1)[1].split('(')[0]; got = aliases.get(got, got)
        if r['symbol'] == '___cxa_pure_virtual':
            expected = 'setMacAddress' if i == 488 else handlers[i]
        else:
            expected = d.split('::', 1)[1].split('(')[0]
        if got.startswith('~'): got = '~destructor'
        if expected.startswith('~'): expected = '~destructor'
        assert got == expected, (cls, i, hex(i * 8), got, expected)
    return len(slots)

n_awdl = check('AirportItlwmAWDLInterface', native['slots'])
n_llw = check('AirportItlwmLowLatencyInterface', native['virtual_interface_slots'])
# 1.4.2: IO80211Buffer is virtual on 25G342 and the management pool hands out IO80211MallocBuffer, so the calls the
# receive path makes must be virtual and sit at the native slots (1.4.1 called the base directly and panicked).
calls = {35: 'returnBuffer', 38: 'getLength', 39: 'setLength', 40: 'getCapacity', 47: 'writeBytes'}
bt = text[text.index("Vtable for 'IO80211Buffer'"):]
bt = bt[:bt.find('\nVtable for ', 1)] if bt.find('\nVtable for ', 1) > 0 else bt
for slot, name in calls.items():
    line = re.search(r'^\s*' + str(slot + 2) + r' \| (.*)$', bt, re.M)
    assert line and ('IO80211Buffer::' + name) in line[1], ('IO80211Buffer', slot, line and line[1])
    for key in ('buffer_slots', 'malloc_buffer_slots'):
        native_name = subprocess.check_output(['c++filt', '-n', native[key][slot]['symbol'][1:]], text=True)
        assert '::' + name + '(' in native_name, (key, slot, native_name)
symbols_path = Path(os.environ.get('NATIVE_KERNEL_SYMBOLS', str(root.parents[1] / 'outputs/tahoe-wifi/kc-symbols-25G342.txt')))
available = {fields[-1] for line in symbols_path.read_text().splitlines() if len(fields := line.split()) >= 3 and fields[-2] != 'U'}
required = set(subprocess.check_output(['nm', '-u', str(out / 'fixture.o')], text=True).split())
missing = sorted(x for x in required - available if not x.startswith('__ZN12AirportItlwm'))
assert not missing, ('AWDL symbols absent from the 25G342 boot KC', missing)
report = {'os_build': native['os_build'], 'object_size': native['object_size'], 'awdl_slots_checked': n_awdl,
          'low_latency_slots_checked': n_llw, 'typed_awdl_handlers': len(native['methods']),
          'handlers_confirmed_by_dispatcher': sum(m['dispatcher_seen'] for m in native['methods']),
          'native_imports_checked': len(required), 'missing_native_imports': missing,
          'kernel_symbols_sha256': hashlib.sha256(symbols_path.read_bytes()).hexdigest(), 'fixture_loaded': False}
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS:', n_awdl, 'AWDL and', n_llw, 'low-latency 25G342 dispatch slots,', len(native['methods']),
      'typed AWDL handlers and', len(required), 'native imports; compiled, not loaded.')
