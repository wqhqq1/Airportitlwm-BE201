#!/usr/bin/env python3
"""Offline checks for the default-off AWDL receive probe (1.1.10)."""
from pathlib import Path
import subprocess, tempfile
ROOT = Path(__file__).resolve().parent.parent
src = r'''
#include <assert.h>
#include <stdio.h>
#include <vector>
#include "iwx_awdl_probe.h"
static const uint8_t BSS[6]={2,1,1,1,1,1},AWDL[6]={0,0x25,0,0xff,0x94,0x73},OTHER[6]={2,9,9,9,9,9};
typedef std::vector<uint8_t> V;
static V frame(uint8_t fc0,uint8_t fc1,const uint8_t*bssid,const uint8_t*sa,V body={}){V f(24,0);f[0]=fc0;f[1]=fc1;memset(&f[4],0xff,6);memcpy(&f[10],sa,6);memcpy(&f[16],bssid,6);f.insert(f.end(),body.begin(),body.end());return f;}
int main(){
 iwx_awdl_probe p={};p.mode=1;auto rx=[&](const V&f){return iwx_awdl_probe_rx(&p,f.data(),f.size(),BSS);};
 V psf={127,0,0x17,0xf2,8,1,0,0},mif={127,0,0x17,0xf2,8,1,3,0};
 uint8_t s1[6]={2,2,2,2,2,1},s2[6]={2,2,2,2,2,2};
 assert(rx(frame(0xd0,0,AWDL,s1,psf))==IWX_AWDL_PROBE_DROP&&p.awdl_psf==1&&p.awdl_action==1&&p.apple_action==1&&p.sender_count==1);
 assert(rx(frame(0xd0,0,AWDL,s1,mif))==IWX_AWDL_PROBE_DROP&&p.awdl_mif==1&&p.sender_count==1);
 assert(rx(frame(0xd0,0,AWDL,s2,psf))==IWX_AWDL_PROBE_DROP&&p.sender_count==2);
 assert(rx(frame(0x08,0,AWDL,s1))==IWX_AWDL_PROBE_DROP&&p.awdl_data==1);
 // Our own traffic and everything the stack used to see stay untouched.
 uint32_t d=p.dropped;
 for(uint8_t fc:{0x00,0x10,0x20,0x30,0xa0,0xb0,0xc0,0xd0}) assert(rx(frame(fc,0,BSS,OTHER,psf))==IWX_AWDL_PROBE_KEEP);
 assert(rx(frame(0x08,0x02,OTHER,BSS))==IWX_AWDL_PROBE_KEEP&&rx(frame(0x88,0x01,OTHER,BSS))==IWX_AWDL_PROBE_KEEP);
 assert(rx(frame(0x80,0,OTHER,OTHER))==IWX_AWDL_PROBE_KEEP&&rx(frame(0x50,0,OTHER,OTHER))==IWX_AWDL_PROBE_KEEP);
 assert(p.dropped==d);
 V bar(16,0);bar[0]=0x84;assert(rx(bar)==IWX_AWDL_PROBE_KEEP);V cts(10,0);cts[0]=0xc4;assert(rx(cts)==IWX_AWDL_PROBE_DROP);
 assert(rx(frame(0xb0,0,OTHER,OTHER))==IWX_AWDL_PROBE_DROP&&p.foreign_mgmt>0);
 uint32_t a=p.awdl_action;V trunc={127,0,0x17,0xf2,8};rx(frame(0xd0,0,AWDL,s1,trunc));assert(p.awdl_action==a);
 V type6={127,0,0x17,0xf2,6,1,0};rx(frame(0xd0,0,OTHER,s1,type6));assert(p.awdl_action==a);
 {
  // Counters for what reaches the driver; infrastructure data is left to the stack.
  iwx_awdl_probe z={};z.mode=3;memset(z.tx.self,0x22,6);auto rz=[&](const V&f){return iwx_awdl_probe_rx(&z,f.data(),f.size(),BSS);};
  V from(24,0);from[0]=0x88;from[1]=0x02;memcpy(&from[10],OTHER,6);assert(rz(from)==IWX_AWDL_PROBE_KEEP&&z.dropped==0);
  assert(rz(frame(0x08,0,OTHER,s1))==IWX_AWDL_PROBE_DROP&&z.foreign_data==1&&z.awdl_data==0);
  auto mine=frame(0x88,0,AWDL,s1);memset(&mine[4],0x22,6);assert(rz(mine)==IWX_AWDL_PROBE_DROP&&z.awdl_data==1&&z.awdl_data_self==1&&z.foreign_data==1);
  assert(rz(frame(0x08,0,AWDL,s1))==IWX_AWDL_PROBE_DROP&&z.awdl_data==2&&z.awdl_data_self==1);
  assert(rz(frame(0x08,0,BSS,s1))==IWX_AWDL_PROBE_KEEP);
  // Peer stations: nearby AWDL senders only, once each, up to the table size.
  iwx_awdl_probe y={};auto act=[&](uint8_t last,const uint8_t*bss=AWDL){uint8_t m[6]={2,3,3,3,3,last};return frame(0xd0,0,bss,m,psf);};
  auto a1=act(1);assert(!iwx_awdl_peer_note(&y,a1.data(),a1.size(),-40));y.assoc_rx=1;
  assert(iwx_awdl_peer_note(&y,a1.data(),a1.size(),-40)&&y.peer_count==1&&!memcmp(y.peer_addr[0],&a1[10],6));
  assert(!iwx_awdl_peer_note(&y,a1.data(),a1.size(),-40)&&y.peer_count==1);
  auto far=act(9);assert(!iwx_awdl_peer_note(&y,far.data(),far.size(),-66));assert(iwx_awdl_peer_note(&y,far.data(),far.size(),-65));
  auto other=act(7,OTHER);assert(!iwx_awdl_peer_note(&y,other.data(),other.size(),-40));
  auto dat=act(8);dat[0]=0x88;assert(!iwx_awdl_peer_note(&y,dat.data(),dat.size(),-40));
  auto grp=act(6);grp[10]|=1;assert(!iwx_awdl_peer_note(&y,grp.data(),grp.size(),-40));
  assert(!iwx_awdl_peer_note(&y,a1.data(),10,-40)&&!iwx_awdl_peer_note(&y,nullptr,30,-40));
  for(uint8_t l=20;l<30;++l){auto f=act(l);iwx_awdl_peer_note(&y,f.data(),f.size(),-40);}assert(y.peer_count==IWX_AWDL_PEER_STA_MAX);
  iwx_awdl_probe z2={};z2.assoc_rx=1;z2.peer_failed=1;assert(!iwx_awdl_peer_note(&z2,a1.data(),a1.size(),-40));
 }
 iwx_awdl_probe q={};for(unsigned i=0;i<500;++i){uint8_t m[6]={2,0,0,0,uint8_t(i>>8),uint8_t(i)};auto f=frame(0xd0,0,AWDL,m,psf);iwx_awdl_probe_rx(&q,f.data(),f.size(),BSS);}assert(q.sender_count<=32);
 uint32_t seed=1;auto r=[&]{seed=seed*1664525+1013904223;return seed>>9;};
 for(unsigned i=0;i<500000;++i){size_t n=r()%64;V f(n);for(auto&x:f)x=uint8_t(r());if(n>4&&(i&1))f[0]=0xd0;iwx_awdl_probe_rx(&p,n?f.data():nullptr,n,BSS);}
 puts("PASS: PSF/MIF/data counted; own-BSS, infrastructure, beacon, probe response and BAR kept; sender set bounded; 500000 malformed inputs");
}
'''
with tempfile.TemporaryDirectory() as d:
    c = Path(d)/'t.cpp'; c.write_text(src)
    subprocess.run(['clang++','-std=c++17','-w','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(ROOT/'itlwm/hal_iwx'),str(c),'-o',d+'/t'],check=True)
    subprocess.run([d+'/t'],check=True)
s=(ROOT/'itlwm/hal_iwx/ItlIwx.cpp').read_text()
i=s.index('iwx_mld_mac_config_cmd(struct iwx_softc *sc, struct iwx_node *in,');fn=s[i:s.index('iwx_mld_link_config_cmd(struct iwx_softc *sc',i)]
assert 'if (assoc && (sc->sc_awdl_probe.mode == 1 || sc->sc_awdl_probe.mode == 2))' in fn
h=s.index('sc->sc_awdl_probe.mode && (ic->ic_state == IEEE80211_S_RUN || sc->sc_awdl_probe.ctx.solo)');assert s.index('Account for padding following the frame header.')<h<s.index('memset(&rxi, 0, sizeof(rxi));',h)
assert 'sc->sc_awdl_probe.mode = awdlProbe <= 2 ? awdlProbe : 0;' in s
print('PASS: filter widens only with the boot argument after association; probe runs before the stack; invalid modes are off')
