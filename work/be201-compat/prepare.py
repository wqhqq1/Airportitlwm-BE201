from pathlib import Path
import hashlib,json
w=Path(__file__).resolve().parent
b=Path('/usr/sbin/bluetoothd').read_bytes()
gate_start=0x3ede39; gate=b[gate_start:gate_start+72];assert gate[24:29]==bytes.fromhex('45 85 f6 74 25')
gate_new=bytearray(gate);gate_new[25]=0x31;gate_new[27]=0xeb
name=b'\0THIRD_PARTY_DONGLE\0BCM_4350C2\0';name_new=b'\0'+b'Intel BE201'.ljust(len(b'THIRD_PARTY_DONGLE'),b'\0')+b'\0BCM_4350C2\0';assert len(name)==len(name_new)
assert b.count(gate)==1 and b[:11061744].count(name)==1
arrays=''
for k,v in [('kBE201ClockOriginal',gate),('kBE201ClockPatched',gate_new),('kBE201NameOriginal',name),('kBE201NamePatched',name_new)]:arrays+='static const unsigned char '+k+'[] = {'+','.join('0x%02x'%x for x in v)+'};\n'
(w/'BE201Patches.hpp').write_text('''// Local Sequoia 15.7.8 (24G824), x86_64-only compatibility patches.
// Clock gate mechanism: hexxyan, BrcmPatchRAM PR #38, GPL-2.0.
// Expanded exact context avoids a second, unrelated match in this build.
#pragma once
#ifdef KERNEL
#include <libkern/libkern.h>
#else
#include <cstddef>
#include <cstring>
#endif
'''+arrays+'''
template <size_t N> static unsigned be201Apply(unsigned char *page, size_t length,
    const unsigned char (&find)[N], const unsigned char (&replacement)[N]) {
    if (!page || length < N) return 0;
    size_t match = 0; unsigned count = 0;
    for (size_t i = 0; i <= length-N; ++i) {
        if (!memcmp(page+i, find, N)) { match = i; ++count; }
    }
    // Refuse ambiguous pages; never overwrite beyond the verified byte span.
    if (count == 1) memcpy(page+match, replacement, N);
    return count == 1 ? 1 : 0;
}
''')
s=Path('work/research/BlueToolFixup.cpp').read_text()
s=s.replace('#define MODULE_SHORT "btlfx"','#define MODULE_SHORT "btlfx"\n#include "BE201Patches.hpp"')
s=s.replace('static bool shouldPatchBoardId = false;','static bool shouldPatchBE201Name = false;\nstatic bool shouldPatchBE201Clock = false;\nstatic bool shouldPatchBoardId = false;')
needle='''        else if (strcmp(path + dirLength, "bluetoothd") == 0) {
'''
assert s.count(needle)==1
s=s.replace(needle,needle+'''            if (getKernelVersion() == KernelVersion::Sequoia) {
                auto page = static_cast<unsigned char *>(const_cast<void *>(data));
                if (shouldPatchBE201Name && be201Apply(page, PAGE_SIZE, kBE201NameOriginal, kBE201NamePatched))
                    SYSLOG(MODULE_SHORT, "[BE201] chipset display changed to Intel BE201; numeric identity unchanged");
                if (shouldPatchBE201Clock && be201Apply(page, PAGE_SIZE, kBE201ClockOriginal, kBE201ClockPatched))
                    SYSLOG(MODULE_SHORT, "[a2dpcheck] applied exact 24G824 A2DP BT-clock gate");
            }
''')
s=s.replace('''    lilu.onPatcherLoadForce([](void *user, KernelPatcher &patcher) {''','''    lilu.onPatcherLoadForce([](void *user, KernelPatcher &patcher) {
        shouldPatchBE201Name = checkKernelArgument("-be201identity");
        shouldPatchBE201Clock = checkKernelArgument("-btlfxa2dpcheck");
        SYSLOG(MODULE_SHORT, "BE201 local build: identity=%d A2DP=%d (exact 24G824 context)", shouldPatchBE201Name, shouldPatchBE201Clock);''')
s=s.replace('    KernelVersion::Tahoe,','    KernelVersion::Sequoia,')
(w/'BlueToolFixup.cpp').write_text(s)
report={'os_build':'24G824','bluetoothd_sha256':hashlib.sha256(b).hexdigest(),'upstream_pr':'https://github.com/acidanthera/BrcmPatchRAM/pull/38','upstream_commit':'d8bd62a781d04f5593d03258f4092ec9403e7805','exact_gate_file_offset':hex(gate_start),'instruction_file_offset':'0x3ede51','exact_gate_count':b.count(gate),'excluded_unrelated_offset':'0x22db3d','name_x86_offset':'0x8c0159','numeric_identity_modified':False,'vendor_display':'Apple (0x004C)','reboot_required':True}
(w/'patch-verification.json').write_text(json.dumps(report,indent=2))
