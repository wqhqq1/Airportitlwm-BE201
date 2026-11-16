"""Tahoe WCL scan request decoding: the SSID list fallback (1.3.2) under ASan/UBSan.

Builds 0x1550-byte requests the way 25G342 fills them (framework 0xaa fill, single SSID at 0x1c/0x20,
list count at 0x1318, entries of version/length/SSID 0x38 apart from 0x131c) and checks decodeScan:
the single field wins, the first valid list entry is used when it is empty, invalid or 0xaa entries
are skipped, the count is clamped to 10, and the buffer end is never read past (guard page)."""
from pathlib import Path
import subprocess, tempfile

root = Path(__file__).resolve().parents[1]
harness = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <sys/mman.h>
#include <unistd.h>
#include "WCL.hpp"
using namespace AirportWCL;
static void put32(uint8_t *p, uint32_t v) { memcpy(p, &v, 4); }
static uint8_t *guarded(size_t n) {
    size_t page = getpagesize(), total = (n + page - 1) / page * page + page;
    uint8_t *m = (uint8_t *)mmap(nullptr, total, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    assert(m != MAP_FAILED);
    assert(mprotect(m + total - page, page, PROT_NONE) == 0);
    return m + total - page - n;
}
static uint8_t *request(uint32_t singleLen, uint32_t listCount) {
    uint8_t *p = guarded(0x1550);
    memset(p, 0xaa, 0x1550);
    put32(p, 7);                 // identifier
    put32(p + 0x1c, singleLen);  // single SSID length
    memset(p + 0x20, 'S', 32);
    put32(p + 0x40, 1);          // active
    put32(p + 0x54, 1);          // one channel
    put32(p + 0x58, 1); put32(p + 0x5c, 149); put32(p + 0x60, 0x10);
    put32(p + kScanSsidListCount, listCount);
    return p;
}
static void entry(uint8_t *p, unsigned i, uint32_t version, uint32_t len, char fill) {
    uint8_t *e = p + kScanSsidList + i * kScanSsidListStride;
    put32(e, version); put32(e + 4, len); memset(e + 8, fill, 32);
}
int main() {
    ScanRequest s;
    // Single field set: used as before, list ignored.
    uint8_t *p = request(8, 2); entry(p, 0, 1, 19, 'L');
    assert(decodeScan(p, 0x1550, s) && s.ssidLength == 8 && s.ssid[0] == 'S' && s.ssidSource == 1);
    assert(s.channels[149 / 8] & (1 << (149 % 8)));
    // Empty single field: the first valid list entry, for every length 1..32 and count 1..12.
    for (uint32_t count = 1; count <= 12; ++count)
        for (uint32_t len = 1; len <= 32; ++len) {
            p = request(0, count);
            for (unsigned i = 0; i < kScanSsidListMax; ++i) entry(p, i, 1, len, 'A' + i);
            assert(decodeScan(p, 0x1550, s));
            assert(s.ssidSource == 2 && s.ssidLength == len && s.ssid[0] == 'A' && s.ssidListCount == count);
            for (unsigned k = len; k < 32; ++k) assert(s.ssid[k] == 0);
        }
    // Invalid entries are skipped: bad version, zero length, over 32, then the 0xaa fill.
    p = request(0, 10);
    entry(p, 0, 0, 5, 'x'); entry(p, 1, 1, 0, 'y'); entry(p, 2, 1, 33, 'z'); entry(p, 3, 1, 6, 'H');
    assert(decodeScan(p, 0x1550, s) && s.ssidSource == 2 && s.ssidLength == 6 && s.ssid[0] == 'H');
    // Nothing valid (only the framework fill, or count 0): broadcast, as before.
    p = request(0, 10);
    assert(decodeScan(p, 0x1550, s) && s.ssidLength == 0 && s.ssidSource == 0);
    p = request(0, 0); entry(p, 0, 1, 4, 'Q');
    assert(decodeScan(p, 0x1550, s) && s.ssidLength == 0 && s.ssidSource == 0);
    // Count beyond 10 reads only 10 entries: a valid 11th slot would sit past the list.
    p = request(0, 0xffffffff);
    assert(decodeScan(p, 0x1550, s) && s.ssidLength == 0);
    entry(p, 9, 1, 3, 'N');
    assert(decodeScan(p, 0x1550, s) && s.ssidLength == 3 && s.ssid[0] == 'N');
    // A short buffer (the Sequoia-sized request) never reaches the list.
    uint8_t *q = guarded(0x200); memcpy(q, request(0, 1), 0x200);
    assert(decodeScan(q, 0x200, s) && s.ssidLength == 0 && s.ssidSource == 0);
    puts("PASS wcl scan ssid list");
}
'''
def sanitizers(d):
    # ASan's runtime dies with SIGILL on this Tahoe host (even an empty program); the guard page
    # still catches any read past the request, so fall back to UBSan alone when ASan cannot run.
    probe = Path(d) / 'probe.cpp'; probe.write_text('int main(){return 0;}\n')
    exe = Path(d) / 'probe'
    ok = subprocess.run(['clang++', '-fsanitize=address', str(probe), '-o', str(exe)]).returncode == 0 and \
        subprocess.run([str(exe)]).returncode == 0
    return ('address,undefined' if ok else 'undefined'), ok

with tempfile.TemporaryDirectory() as d:
    src = Path(d) / 't.cpp'
    src.write_text(harness)
    exe = Path(d) / 't'
    san, asan = sanitizers(d)
    if not asan:
        print('note: ASan unavailable on this host, UBSan + guard page only')
    subprocess.run(['clang++', '-std=c++17', '-DAIRPORT_WCL_SCAN_LIST_TEST', '-fsanitize=' + san,
                    '-fno-sanitize-recover=all', '-Wall', '-Wextra', '-Werror', '-I', str(root / 'AirportItlwm/WCL'),
                    str(src), '-o', str(exe)], check=True)
    print(subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout.strip())
