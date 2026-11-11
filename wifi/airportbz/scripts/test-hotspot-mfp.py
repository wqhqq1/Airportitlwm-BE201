#!/usr/bin/env python3
"""Offline checks for the iPhone-hotspot-only MFP association (1.1.8)."""
from pathlib import Path
import re, subprocess, tempfile
ROOT = Path(__file__).resolve().parent.parent
wcl = (ROOT/'AirportItlwm/WCL/WCL.hpp').read_text()
out = (ROOT/'itl80211/openbsd/net80211/ieee80211_output.c').read_text()
def c_function(text, signature):
    start = text.index(signature)
    open_brace = text.index('{', start)
    depth = 0
    for i in range(open_brace, len(text)):
        depth += {'{': 1, '}': -1}.get(text[i], 0)
        if not depth:
            return text[start:i+1]
    raise AssertionError(signature)
add_rsn_body = c_function(out, 'ieee80211_add_rsn_body(u_int8_t *frm, struct ieee80211com *ic,\n    const struct ieee80211_node *ni, int wpa)')
add_rsn = c_function(out, 'ieee80211_add_rsn(u_int8_t *frm, struct ieee80211com *ic,')
src = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vector>
#define AIRPORT_WCL_TEST 1
''' + wcl[wcl.index('namespace AirportWCL {'):wcl.index('inline bool scanUsesProbes')] + r'''
}
typedef uint8_t u_int8_t_;
#define panic(x) abort()
#define IEEE80211_C_MFP 0x2000
#define IEEE80211_F_MFPR 0x01000000
#define IEEE80211_F_PBAR 0x08000000
#define IEEE80211_RSNCAP_PTKSA_RCNT_MASK 0x000c
#define IEEE80211_RSNCAP_GTKSA_RCNT_MASK 0x0030
#define IEEE80211_RSNCAP_MFPC 0x0080
#define IEEE80211_RSNCAP_MFPR 0x0040
#define IEEE80211_RSNCAP_PBAC 0x1000
#define IEEE80211_ELEMID_RSN 48
#define IEEE80211_NODE_PMKID 0x100
#define IEEE80211_PMKID_LEN 16
#define LE_WRITE_2(p,v) do{(p)[0]=uint8_t(v);(p)[1]=uint8_t((v)>>8);}while(0)
enum ieee80211_cipher{IEEE80211_CIPHER_NONE=0,IEEE80211_CIPHER_USEGROUP=1,IEEE80211_CIPHER_WEP40=2,IEEE80211_CIPHER_TKIP=4,IEEE80211_CIPHER_CCMP=8,IEEE80211_CIPHER_WEP104=16,IEEE80211_CIPHER_BIP=32};
#define IEEE80211_AKM_NONE 0
#define IEEE80211_AKM_8021X 1
#define IEEE80211_AKM_PSK 2
#define IEEE80211_AKM_SHA256_8021X 4
#define IEEE80211_AKM_SHA256_PSK 8
#define IEEE80211_AKM_SAE 16
struct ieee80211com{uint32_t ic_caps=0,ic_flags=0;int ic_rsngroupmgmtcipher=IEEE80211_CIPHER_BIP;};
struct ieee80211_node{uint32_t ni_flags=0;int ni_rsngroupcipher=IEEE80211_CIPHER_CCMP,ni_rsnciphers=IEEE80211_CIPHER_CCMP,ni_rsnakms=IEEE80211_AKM_PSK;uint16_t ni_rsncaps=0xbc;uint8_t ni_pmkid[16]={};};
static const uint8_t IEEE80211_OUI[3]={0,0x0f,0xac},MICROSOFT_OUI[3]={0,0x50,0xf2};
static uint8_t * ''' + add_rsn_body + r'''
static uint8_t * ''' + add_rsn + r'''
using namespace AirportWCL;
int main(){
 ieee80211com ic;ieee80211_node ni;uint8_t b[128];
 // Exact element the operating system requested for this hotspot (rsn_length 28).
 const uint8_t requested[28]={48,26,1,0,0,0x0f,0xac,4,1,0,0,0x0f,0xac,4,1,0,0,0x0f,0xac,2,0xbc,0,0,0,0,0x0f,0xac,6};
 ic.ic_caps=IEEE80211_C_MFP;
 uint8_t *e=ieee80211_add_rsn(b,&ic,&ni);
 assert(e-b==28&&!memcmp(b,requested,28));
 ic.ic_caps=0;
 e=ieee80211_add_rsn(b,&ic,&ni);
 const uint8_t plain[22]={48,20,1,0,0,0x0f,0xac,4,1,0,0,0x0f,0xac,4,1,0,0,0x0f,0xac,2,0x3c,0};
 assert(e-b==22&&!memcmp(b,plain,22));
 assert(rsnOffersBIP(requested,28));
 assert(!rsnOffersBIP(plain,22));
 auto modified=[&](unsigned i,uint8_t v){std::vector<uint8_t> x(requested,requested+28);x[i]=v;return x;};
 auto noMfpc=modified(20,0x3c);assert(!rsnOffersBIP(noMfpc.data(),28));
 auto otherMgmt=modified(27,0x0b);assert(!rsnOffersBIP(otherMgmt.data(),28));
 const uint8_t apple[]={221,10,0,0x17,0xf2,6,1,1,3,1,0,0};
 std::vector<uint8_t> beacon={0,4,'i','P','h','o'};beacon.insert(beacon.end(),apple,apple+sizeof(apple));
 assert(hasAppleVendorIE(beacon.data(),beacon.size()));
 auto fcs=beacon;fcs.insert(fcs.end(),{1,2,3,4});fcs.back()=0xff;
 assert(hasAppleVendorIE(fcs.data(),fcs.size()));
 assert(!hasAppleVendorIE(beacon.data(),6));assert(!hasAppleVendorIE(nullptr,0));
 const uint32_t psk=1u<<3;
 auto active=[](uint32_t s){return (s&HotspotMfpRequired)==HotspotMfpRequired;};
 assert(hotspotMfpScope(requested,28,psk,300,true,beacon.data(),beacon.size())==0x1f);
 assert(active(hotspotMfpScope(requested,28,psk,300,true,nullptr,0)));  // Apple bit is reported only.
 assert(!active(hotspotMfpScope(requested,28,psk,100,true,beacon.data(),beacon.size())));  // Ordinary router.
 assert(!active(hotspotMfpScope(plain,22,psk,300,true,beacon.data(),beacon.size())));
 assert(!active(hotspotMfpScope(requested,28,psk,300,false,beacon.data(),beacon.size())));
 assert(!active(hotspotMfpScope(requested,28,1u<<10,300,true,beacon.data(),beacon.size())));  // SHA256/SAE-style.
 // Parser and list walker never read outside adversarial input (ASan guards this).
 uint32_t seed=1;auto rnd=[&]{seed=seed*1664525+1013904223;return seed;};unsigned hits=0;
 for(unsigned i=0;i<500000;++i){unsigned n=rnd()%96;std::vector<uint8_t> m(n);for(auto &x:m)x=uint8_t(rnd()>>13);
  if(n>4&&(i&1)){m[0]=48;m[1]=uint8_t(n-2);m[2]=1;m[3]=0;}
  hits+=rsnOffersBIP(m.empty()?nullptr:m.data(),n);hits+=hasAppleVendorIE(m.empty()?nullptr:m.data(),n);}
 printf("PASS: exact 28-byte requested RSN built only with C_MFP; plain RSN unchanged; scope requires bi300+MFPC+BIP+PSK; 500000 malformed inputs (%u accepted)\n",hits);
}
'''
with tempfile.TemporaryDirectory() as d:
    c = Path(d)/'t.cpp'; c.write_text(src)
    subprocess.run(['clang++','-std=c++17','-w','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(c),'-o',d+'/t'],check=True)
    subprocess.run([d+'/t'],check=True)
ip = (ROOT/'itl80211/openbsd/net80211/ieee80211_input.c').read_text()
pa = (ROOT/'itl80211/openbsd/net80211/ieee80211_pae_input.c').read_text()
nd = (ROOT/'itl80211/openbsd/net80211/ieee80211_node.c').read_text()
iw = (ROOT/'itlwm/hal_iwx/ItlIwx.cpp').read_text()
wc = (ROOT/'AirportItlwm/WCL/WCL.cpp').read_text()
assert 'IEEE80211_C_MFP' not in re.sub(r'#ifdef AIRPORT_WCL.*?#endif','',iw,flags=re.S)
assert 'ic->ic_caps &= ~IEEE80211_C_MFP;' in wc and wc.count('ic->ic_caps |= IEEE80211_C_MFP;') == 1
assert pa.count('IEEE80211_NODE_RXMGMTPROT | IEEE80211_NODE_TXMGMTPROT') == 1
assert ip.count('m = ieee80211_input_hwdecrypt(ic, ni, m, rxi);') == 2
assert '&k->k_mgmt_rsc : &k->k_rsc[tid]' in iw
assert nd.count('IEEE80211_NODE_RXMGMTPROT | IEEE80211_NODE_TXMGMTPROT') == 2
print('PASS: scope gate is the only C_MFP writer; PTK enables both directions; firmware-decrypted unicast mgmt uses its own replay counter; teardown clears flags')
