"""Exercise production scan setup and final TLC capture under ASan/UBSan."""
from pathlib import Path
import subprocess, tempfile

root = Path(__file__).resolve().parents[1]
s = (root / 'AirportItlwm/WCL/WCL.cpp').read_text()
start = s.index('static void airport_wcl_prepare_join_scan(')
brace = s.index('{', start)
end, depth = brace + 1, 1
while depth:
    depth += (s[end] == '{') - (s[end] == '}')
    end += 1
function = s[start:end]
harness = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <sys/mman.h>
#include <unistd.h>
#include "iwx_tlc_trace.h"
struct ieee80211com {
 bool ic_wcl_scan_active=false,ic_wcl_scan_requested=false;
 bool ic_wcl_scan_restricted=false,ic_wcl_join_requested=true;
 int ic_des_esslen=0;
 uint8_t ic_des_essid[32]={},ic_wcl_scan_ssid[32]={};
 uint8_t ic_wcl_scan_channels[32]={};
 uint8_t ic_wcl_scan_ssid_length=0;
 uint64_t untouched=0x123456789abcdef0ULL;
};
''' + function + r'''
int main() {
 // Prior passive/directed/wildcard state, shorter replacement and full SSID;
 // empty channel = unrestricted; channel 255 exercises final bitmap byte.
 for (unsigned active=0;active<2;++active)
 for (unsigned length=1;length<=32;++length)
 for (unsigned channel: {0u,1u,6u,36u,149u,255u}) {
  ieee80211com ic;
  memset(ic.ic_wcl_scan_ssid,0xee,32);
  memset(ic.ic_wcl_scan_channels,0xff,32);
  ic.ic_wcl_scan_active=active;ic.ic_wcl_scan_restricted=true;
  ic.ic_des_esslen=length;
  for(unsigned i=0;i<length;++i)ic.ic_des_essid[i]=uint8_t(i+1);
  airport_wcl_prepare_join_scan(&ic,channel);
  assert(ic.ic_wcl_scan_active && ic.ic_wcl_scan_requested);
  assert(ic.ic_wcl_scan_ssid_length==length);
  assert(!memcmp(ic.ic_des_essid,ic.ic_wcl_scan_ssid,length));
  for(unsigned i=length;i<32;++i)assert(ic.ic_wcl_scan_ssid[i]==0);
  for(unsigned bit=0;bit<256;++bit)
   assert(bool(ic.ic_wcl_scan_channels[bit>>3]&(1u<<(bit&7)))==bool(channel && channel==bit));
  assert(ic.ic_wcl_scan_restricted==bool(channel));
  assert(ic.ic_wcl_join_requested && ic.untouched==0x123456789abcdef0ULL);
 }
 iwx_tlc_trace trace={};uint8_t payload[28];memset(payload,0x31,sizeof(payload));
 size_t page=getpagesize();void *guard=mmap(nullptr,page,PROT_NONE,MAP_ANON|MAP_PRIVATE,-1,0);
 assert(guard!=MAP_FAILED);
 // No non-TLC, unknown ABI, truncated/long or null input can be captured/read.
 iwx_tlc_trace_append(trace,1,2,3,4,5,0x0518,4,guard,28);
 for(unsigned size=0;size<64;++size)if(size!=28)
  iwx_tlc_trace_append(trace,1,2,3,4,5,0x050f,4,guard,size);
 for(unsigned ver=0;ver<256;++ver)if(ver!=4)
  iwx_tlc_trace_append(trace,1,2,3,4,5,0x050f,ver,guard,28);
 iwx_tlc_trace_append(trace,1,2,3,4,5,0x050f,4,nullptr,28);
 iwx_tlc_trace empty={};assert(!memcmp(&trace,&empty,sizeof(trace)));
 for(unsigned i=0;i<21;++i) {
  payload[0]=i;
  iwx_tlc_trace_append(trace,i/3,2,3,4,5,0x050f|(i<<16),4,payload,28);
 }
 assert(trace.count==21 && trace.next==5);
 for(unsigned i=0;i<8;++i) {
  const auto &r=trace.records[(trace.next+i)%8];
  assert(r.ordinal==14+i && r.payload[0]==13+i);
  assert(r.command_header==(0x050f|((13+i)<<16)));
  assert(r.payload[27]==0x31 && r.payload_length==28 && r.command_version==4);
 }
 assert(!iwx_tlc_trace_freeze(trace,0,0,0,0));
 assert(iwx_tlc_trace_freeze(trace,0x20101a0d,3,0x14050f,6));
 auto frozen=trace;
 assert(!iwx_tlc_trace_freeze(trace,0x123,0,0,100));
 iwx_tlc_trace_append(trace,100,1,2,3,4,0x050f,4,guard,28);
 assert(!memcmp(&trace,&frozen,sizeof(trace)));
 assert(trace.error_command==trace.records[4].command_header);
 assert(trace.error_generation==trace.records[4].generation);
 trace={};trace.count=UINT32_MAX;
 for(unsigned i=0;i<16;++i)iwx_tlc_trace_append(trace,0,0,0,0,0,0x050f,4,payload,28);
 assert(trace.count==UINT32_MAX && trace.next==0);
 trace={};assert(iwx_tlc_trace_freeze(trace,1,2,3,4));
 assert(trace.count==0 && trace.magic==0x31434c54 && trace.version==1);
 munmap(guard,page);
 puts("PASS: 384 production cold-join scan cases; TLC wire filtering, unreadable input guards, ring wrap/generation/sequence, saturation, first-fault immutability, empty trace.");
}
'''
harness = harness.replace('#include <cstdio>', '#include <cstdio>\n#include <initializer_list>')
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    (p/'test.cpp').write_text(harness)
    subprocess.run(['clang++', '-std=c++14', '-fsanitize=address,undefined',
                    '-Wall', '-Wextra', '-Werror', '-I', str(root/'itlwm/hal_iwx'),
                    str(p/'test.cpp'), '-o', str(p/'test')], check=True)
    subprocess.run([str(p/'test')], check=True)
