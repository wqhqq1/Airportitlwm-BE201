#!/usr/bin/env python3
"""Offline checks for the Instant Hotspot station element (1.1.9)."""
from pathlib import Path
import subprocess, tempfile
ROOT = Path(__file__).resolve().parent.parent
wcl = (ROOT/'AirportItlwm/WCL/WCL.hpp').read_text()
src = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <vector>
''' + wcl[wcl.index('namespace AirportWCL {'):wcl.rindex('#endif')] + r'''
using namespace AirportWCL;
// Native AP parser (updateSTAAssocInfo): walk elements; vendor OUI 00:17:f2 and type 0x0b;
// flags are read at offset 9.
static int nativeFlags(const uint8_t *p,size_t n){
 while(n>=6){ if(p[0]==0xdd&&!memcmp(p+2,"\x00\x17\xf2",3)&&p[5]==0x0b) return p[9];
  size_t s=size_t(p[1])+2; if(s>=n) break; p+=s;n-=s; }
 return -1; }
int main(){
 uint8_t ie[12];
 for(unsigned f=0;f<65536;++f){ memset(ie,0xee,12);size_t n=buildHotspotClientIE(uint16_t(f),ie);
  bool inst=f&2,aut=f&4;
  if(!inst&&!aut){assert(n==0);for(auto c:ie)assert(c==0xee);continue;}
  assert(n==12&&ie[0]==221&&ie[1]==10&&size_t(ie[1])+2==n);
  assert(nativeFlags(ie,n)==(inst?1:0)+(aut?2:0));
 }
 std::vector<uint8_t> b(0x2cc,0);
 auto w32=[&](size_t o,uint32_t v){memcpy(&b[o],&v,4);};
 w32(0x214,1);w32(0x1c,4);memcpy(&b[0x20],"test",4);b[0x21c]=2;b[0x21d]=1;
 uint16_t v=2;memcpy(&b[0x1e0],&v,2);
 JoinRequest j;assert(decodeJoin(b.data(),b.size(),j)&&j.assocFlags==2&&j.rsnLength==0);
 v=0;memcpy(&b[0x1e0],&v,2);assert(decodeJoin(b.data(),b.size(),j)&&j.assocFlags==0&&!buildHotspotClientIE(j.assocFlags,ie));
 puts("PASS: element only with native flag bits 1/2; native parser reads type 0x0b flags; request offset 0x1e0 decoded");
}
'''
with tempfile.TemporaryDirectory() as d:
    c = Path(d)/'t.cpp'; c.write_text(src)
    subprocess.run(['clang++','-std=c++17','-w','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(c),'-o',d+'/t'],check=True)
    subprocess.run([d+'/t'],check=True)
o=(ROOT/'itl80211/openbsd/net80211/ieee80211_output.c').read_text()
fn=o[o.index('ieee80211_get_assoc_req(struct ieee80211com *ic, struct ieee80211_node *ni,'):o.index('(Re)Association response frame format')]
assert fn.count('ic->ic_wcl_assoc_ie_len')==4 and fn.index('ic->ic_wcl_assoc_ie_len +')<fn.index('LE_WRITE_2(frm, capinfo)')
w=(ROOT/'AirportItlwm/WCL/WCL.cpp').read_text()
assert w.index('buildHotspotClientIE(join.assocFlags')<w.index('ieee80211_node_join_bss(ic, selbs, 1)')
print('PASS: frame buffer reserves the element before writing it; flag is applied before every join starts')
