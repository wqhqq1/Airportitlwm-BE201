"""1.1.88 / BlueToolFixup 2.7.12 / IntelBTPatcher 2.5.10: the switches this machine used are on without boot arguments.

Wi-Fi: be201_awdl_vif, be201_awdl_auto (verified kernel only) and be201_tlc_diag default on, =0 turns them off.
1.2.15: be201_awdl_xchan (cross-channel AirDrop: second channel automatic, ROC mode 4) is on too, =0 turns it off;
the other test switches stay off. Bluetooth: eight switches default on, -be201btstock turns them off."""
import re, subprocess, tempfile
from pathlib import Path

R = Path(__file__).resolve().parents[1]
BT = R.parents[1]/'bluetooth'
hdr = (R/'include/ItlStartupDiagnostics.hpp').read_text()

def body(src, start):
    a = src.index(start)
    b = src.index('{', a)
    depth, i = 1, b+1
    while depth:
        depth += {'{': 1, '}': -1}.get(src[i], 0)
        i += 1
    return src[a:i]

helpers = '\n'.join(body(hdr, 'inline bool '+n) for n in ['ItlAwdlLayoutVerified()', 'ItlDefaultOnFlag(', 'ItlAwdlFlag('])
test = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
static std::map<std::string,int> args;
static const char *version = "";
static bool PE_parse_boot_argn(const char *n, void *v, int) {
    auto it = args.find(n); if (it == args.end()) return false; *(int *)v = it->second; return true; }
''' + helpers + r'''
int main() {
    const char *ok = "Darwin Kernel Version 24.6.0: Tue Jul 21 20:50:07 PDT 2026; root:xnu-11417.140.69.711.44~1/RELEASE_X86_64";
    const char *other = "Darwin Kernel Version 24.5.0: Tue Apr 22 19:48:46 PDT 2025; root:xnu-11417.121.6~2/RELEASE_X86_64";
    version = ok;
    assert(ItlAwdlLayoutVerified());
    assert(ItlDefaultOnFlag("be201_tlc_diag") && ItlAwdlFlag("be201_awdl_vif") && ItlAwdlFlag("be201_awdl_auto"));
    args["be201_awdl_vif"] = 0; args["be201_tlc_diag"] = 0;
    assert(!ItlAwdlFlag("be201_awdl_vif") && !ItlDefaultOnFlag("be201_tlc_diag") && ItlAwdlFlag("be201_awdl_auto"));
    args["be201_awdl_vif"] = 2; assert(!ItlAwdlFlag("be201_awdl_vif"));
    args.clear(); version = other;
    assert(!ItlAwdlLayoutVerified() && !ItlAwdlFlag("be201_awdl_vif") && !ItlAwdlFlag("be201_awdl_auto"));
    assert(ItlDefaultOnFlag("be201_tlc_diag"));
    args["be201_awdl_vif"] = 1; args["be201_awdl_auto"] = 1;
    assert(ItlAwdlFlag("be201_awdl_vif") && ItlAwdlFlag("be201_awdl_auto"));
    version = "root:xnu-11417.140.69.711.4"; args.clear(); assert(!ItlAwdlLayoutVerified());
    /* 1.1.93: 24H241 (macOS 15.8.3) is verified too */
    version = "Darwin Kernel Version 24.6.0: Sun Oct 11 23:36:58 PDT 2026; root:xnu-11417.140.69.713.47~2/RELEASE_X86_64";
    assert(ItlAwdlLayoutVerified() && ItlAwdlFlag("be201_awdl_vif") && ItlAwdlFlag("be201_awdl_auto"));
    args["be201_awdl_vif"] = 0; assert(!ItlAwdlFlag("be201_awdl_vif") && ItlAwdlFlag("be201_awdl_auto")); args.clear();
    version = "root:xnu-11417.140.69.713.47~3/RELEASE_X86_64"; assert(!ItlAwdlLayoutVerified());
    version = "root:xnu-11417.140.69.713.4"; assert(!ItlAwdlLayoutVerified());
    puts("helpers ok");
}
'''
with tempfile.TemporaryDirectory() as td:
    p = Path(td)
    (p/'t.cpp').write_text(test)
    subprocess.run(['clang++', '-std=c++17', '-fsanitize=address,undefined', '-O1', str(p/'t.cpp'), '-o', str(p/'t')], check=True)
    subprocess.run([str(p/'t')], check=True)

# Every reader of the three Wi-Fi switches goes through the default-on helpers.
srcs = {f: (R/f).read_text() for f in ['AirportItlwm/AirportItlwmV2.cpp', 'AirportItlwm/AirportItlwmSkywalkInterface.cpp',
                                       'itlwm/hal_iwx/ItlIwx.cpp', 'AirportItlwm/WCL/WCL.cpp']}
allsrc = '\n'.join(srcs.values())
for name in ['be201_awdl_vif', 'be201_awdl_auto', 'be201_tlc_diag']:
    assert f'ItlDiagnosticFlag("{name}")' not in allsrc, name
    assert f'PE_parse_boot_argn("{name}"' not in allsrc, name
assert allsrc.count('ItlAwdlFlag("be201_awdl_vif")') == 6 and allsrc.count('ItlAwdlFlag("be201_awdl_auto")') == 1
assert allsrc.count('ItlDefaultOnFlag("be201_tlc_diag")') == 2
assert 'ItlDiagnosticFlag("be201_awdl_if")' in allsrc, 'be201_awdl_if stays opt-in'

# Auto start must not turn on the ROC or the second-channel experiments.
v2 = srcs['AirportItlwm/AirportItlwmV2.cpp']
auto = body(v2, 'void AirportItlwm::startAWDLAuto()')
for var in ['be201AwdlRocValue', 'be201AwdlPhy2Value', 'be201AwdlPhy2TeValue', 'be201AwdlAmsduValue']:
    assert var not in auto, var
assert re.search(r'static int be201AwdlRocValue;', v2), 'ROC switch starts at 0'
reg = v2[v2.index('sysctl_register_oid(&sysctl__debug_be201_awdl_roc);'):]
reg = reg[:reg.index('awdlArmRegistered = true;')]
assert 'ItlAwdlFlag("be201_awdl_xchan")' in reg and 'be201AwdlRocValue, 0x390024' in reg and 'be201AwdlPhy2Value, 1' in reg, 'cross-channel on at boot, only after the switches exist (1.2.15)'
assert allsrc.count('ItlAwdlFlag("be201_awdl_xchan")') == 1 and 'PE_parse_boot_argn("be201_awdl_xchan"' not in allsrc
assert 'be201AwdlLlwValue, 0' in auto, 'llw0 stays off'
assert 'pciNub->setProperty("ItlwmAwdlLayoutVerified", ItlAwdlLayoutVerified());' in v2

# Bluetooth: the eight switches use be201Switch; the experimental ones still need their argument.
ON = ['-btlfxa2dpcheck', '-be201identity', '-be201leadv', '-be201addrpause', '-be201lebaseline', '-be201nativeaddr',
      '-be201btprobe', '-be201rparoute']
bt = {f: (BT/f).read_text() for f in ['bluetoolfixup/BlueToolFixup.cpp', 'intelbtpatcher/IntelBTPatcher.cpp',
                                      'intelbtpatcher/ProbeReporter.hpp']}
for f, s in bt.items():
    for a in ON:
        assert f'checkKernelArgument("{a}")' not in s, (f, a)
    assert '#include "BE201Defaults.hpp"' in s, f
fixup = bt['bluetoolfixup/BlueToolFixup.cpp']
for a in ['-btlfxa2dpcheck', '-be201identity', '-be201leadv', '-be201addrpause', '-be201lebaseline', '-be201btprobe', '-be201rparoute']:
    assert f'be201Switch("{a}")' in fixup, a
for a in ['-be201privacyprobe', '-be201peeraddr']:
    assert f'checkKernelArgument("{a}")' in fixup, a
patcher = bt['intelbtpatcher/IntelBTPatcher.cpp']
for a in ['-be201btprobe', '-be201nativeaddr', '-be201lebaseline']:
    assert f'be201Switch("{a}")' in patcher, a
for d in ['bluetoolfixup', 'intelbtpatcher']:
    h = (BT/d/'BE201Defaults.hpp').read_text()
    assert 'return checkKernelArgument(name) || !checkKernelArgument("-be201btstock");' in h, d
sw = body((BT/'bluetoolfixup/BE201Defaults.hpp').read_text(), 'static inline bool be201Switch(')
bt_test = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <set>
#include <string>
static std::set<std::string> args;
static bool checkKernelArgument(const char *n) { return args.count(n); }
''' + sw.replace('static inline ', 'static ') + r'''
int main() {
    assert(be201Switch("-be201rparoute") && be201Switch("-btlfxa2dpcheck"));
    args.insert("-be201btstock"); assert(!be201Switch("-be201rparoute") && !be201Switch("-btlfxa2dpcheck"));
    args.insert("-btlfxa2dpcheck"); assert(be201Switch("-btlfxa2dpcheck") && !be201Switch("-be201leadv"));
    puts("bt ok");
}
'''
with tempfile.TemporaryDirectory() as td:
    p = Path(td)
    (p/'b.cpp').write_text(bt_test)
    subprocess.run(['clang++', '-std=c++17', '-O1', str(p/'b.cpp'), '-o', str(p/'b')], check=True)
    subprocess.run([str(p/'b')], check=True)
print('PASS: default-on Wi-Fi switches (=0 off; AWDL default only on verified kernels (24G824, 24H241)), ROC/phy2/llw0 stay off, '
      'Bluetooth switches default on with -be201btstock, experimental Bluetooth switches still opt-in.')
