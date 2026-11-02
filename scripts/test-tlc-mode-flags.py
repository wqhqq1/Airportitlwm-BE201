"""Reproduce the hardware legacy-mode/LDPC mismatch with production methods."""
from pathlib import Path
import re, subprocess, tempfile, hashlib
root=Path(__file__).resolve().parents[1]
def block(text, signature):
    start=text.index(signature);end=text.index('{',start)+1;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]
signature='uint16_t ItlIwx::\niwx_rs_fw_get_config_flags('
current=block((root/'itlwm/hal_iwx/ItlIwx.cpp').read_text(),signature)
fixture=root/'tests/fixtures/tlc-flags-1.1.2.inc'
assert hashlib.sha256(fixture.read_bytes()).hexdigest()=='f91f4a3c1284871218ace4694ab6f18d40dd873156e937ff5d8991010eb0f1a1'
old_source=fixture.read_text()
old=block(old_source,signature).replace('iwx_rs_fw_get_config_flags(','old_flags(')
headers='\n'.join(p.read_text() for p in (root/'itl80211/openbsd/net80211').glob('*.h'))+'\n'+(root/'itlwm/hal_iwx/if_iwxreg.h').read_text()
defs=dict(re.findall(r'^\s*#define\s+((?:IWX|IEEE80211)_[A-Za-z0-9_]+)\s+([^\n]+)',headers,re.M))
needed=set(re.findall(r'\b(?:IWX|IEEE80211)_[A-Za-z0-9_]+\b',current))
while True:
    extra=set(re.findall(r'\b(?:IWX|IEEE80211)_[A-Za-z0-9_]+\b','\n'.join(defs.get(k,'') for k in needed)))
    if extra<=needed:break
    needed|=extra
defines='\n'.join('#define '+k+' '+defs[k] for k in sorted(needed) if k in defs)
src=r'''
#include <cstdint>
#include <cstdio>
#include <cassert>
''' + defines + r'''
constexpr int IEEE80211_S_ASSOC=3;
struct Cap { uint8_t phy_cap_info[11]={}; };
struct ieee80211_node {uint32_t ni_flags=0,ni_htcaps=0,ni_vhtcaps=0;Cap ni_he_cap_elem;};
struct ieee80211com {int ic_state=4;uint32_t ic_flags=IEEE80211_F_VHTON;ieee80211_node *ic_bss;Cap ic_he_cap_elem;};
struct iwx_softc {ieee80211com sc_ic;unsigned ant=3;};
struct ItlIwx {uint16_t iwx_rs_fw_get_config_flags(iwx_softc *);uint16_t old_flags(iwx_softc *);
 unsigned iwx_num_of_ant(unsigned a){return __builtin_popcount(a);}
 unsigned iwx_fw_valid_tx_ant(iwx_softc *sc){return sc->ant;}
};
''' + current + '\n' + old + r'''
int main(){
 iwx_softc sc;ieee80211_node ni;sc.sc_ic.ic_bss=&ni;ItlIwx hal;
 ni.ni_flags=12976408;ni.ni_htcaps=IEEE80211_HTCAP_LDPC;
 assert((ni.ni_flags&(IEEE80211_NODE_HT|IEEE80211_NODE_VHT|IEEE80211_NODE_HE))==0);
 assert(hal.old_flags(&sc)==2 && hal.iwx_rs_fw_get_config_flags(&sc)==0);
 uint32_t seed=0x20101a0d;unsigned changed=0;
 for(unsigned i=0;i<100000;++i){
  auto rnd=[&](){seed=seed*1664525u+1013904223u;return seed;};
  ni.ni_flags=rnd()&~(IEEE80211_NODE_HT|IEEE80211_NODE_VHT|IEEE80211_NODE_HE);
  unsigned mode=(i/5)%8;
  if(mode&1)ni.ni_flags|=IEEE80211_NODE_HT;
  if(mode&2)ni.ni_flags|=IEEE80211_NODE_VHT;
  if(mode&4)ni.ni_flags|=IEEE80211_NODE_HE;
  sc.sc_ic.ic_state=i%5;sc.ant=1+(i%3);
  ni.ni_htcaps=rnd();ni.ni_vhtcaps=rnd();sc.sc_ic.ic_flags=rnd();
  for(unsigned j=0;j<11;++j){ni.ni_he_cap_elem.phy_cap_info[j]=rnd()>>24;sc.sc_ic.ic_he_cap_elem.phy_cap_info[j]=rnd()>>24;}
  auto before=hal.old_flags(&sc),after=hal.iwx_rs_fw_get_config_flags(&sc);
  if(mode)assert(before==after);else {assert(after==0);changed+=before!=after;}
 }
 assert(changed>0);
 printf("PASS: actual 1.1.2 RUN/NON_HT+LDPC reproduction (2->0); 100000 production comparisons preserve all negotiated HT/VHT/HE cases, reject stale legacy coding flags (ASan/UBSan).\n");
}
'''
with tempfile.TemporaryDirectory() as d:
    p=Path(d);(p/'test.cpp').write_text(src)
    subprocess.run(['clang++','-std=c++14','-fsanitize=address,undefined','-Wall','-Wextra','-Werror',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
