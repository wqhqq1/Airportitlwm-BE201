"""Actual STA builder and queued authorization update across lifecycle races."""
from pathlib import Path
import subprocess,tempfile,re,hashlib,struct
r=Path(__file__).resolve().parents[1];source=(r/'itlwm/hal_iwx/ItlIwx.cpp').read_text();reg=(r/'itlwm/hal_iwx/if_iwxreg.h').read_text()
def block(s,sig):
 a=s.index(sig);b=s.index('{',a)+1;depth=1
 while depth:depth+=(s[b]=='{')-(s[b]=='}');b+=1
 return s[a:b]
sig='int ItlIwx::\niwx_mld_sta_config_cmd('
fixture=r/'tests/fixtures/sta-config-1.1.6.inc'
assert hashlib.sha256(fixture.read_bytes()).hexdigest()==(r/'tests/fixtures/sta-config-1.1.6.sha256').read_text().strip()
old=fixture.read_text().replace('iwx_mld_sta_config_cmd(','old_sta_config(');new=block(source,sig)
decl=block(reg,'struct iwx_sta_cfg_cmd {')+' __attribute__((packed));'
headers=reg+'\n'+(r/'itlwm/hal_iwx/if_iwxvar.h').read_text()+'\n'+'\n'.join(p.read_text() for p in (r/'itl80211/openbsd/net80211').glob('*.h'))
headers=headers.replace('\\\n','')
defs=dict(re.findall(r'^\s*#define\s+((?:IWX|IEEE80211)_[A-Za-z0-9_]+)\s+([^\n]+)',headers,re.M))
need=set(re.findall(r'\b(?:IWX|IEEE80211)_[A-Za-z0-9_]+\b',old+new))
while True:
 extra=set(re.findall(r'\b(?:IWX|IEEE80211)_[A-Za-z0-9_]+\b','\n'.join(defs.get(k,'') for k in need)))
 if extra<=need:break
 need|=extra
defines='\n'.join('#define '+k+' '+defs[k] for k in sorted(need) if k in defs)
builder=r'''
#include <cassert>
#include <cstring>
#include <cstdint>
#include <cstdio>
#define ETHER_ADDR_LEN 6
#define htole32(x) (x)
#define isset(a,i) (((a)[(i)/8]&(1u<<((i)%8)))!=0)
#define IEEE80211_ADDR_COPY(a,b) memcpy(a,b,6)
''' +defines+'\n'+decl+r'''
static_assert(sizeof(iwx_sta_cfg_cmd)==96,"STA v1 actual96-byte ABI");
struct ieee80211_node{unsigned ni_flags=0,ni_associd=1,ni_rx_nss=2,ni_ampdu_param=0,ni_vhtcaps=0;int ni_port_valid=0;};
struct iwx_node{ieee80211_node in_ni;uint8_t in_macaddr[6]={2,1,2,3,4,5};};
struct iwx_softc{struct{unsigned ic_flags=IEEE80211_F_RSNON;}sc_ic;uint8_t sc_enabled_capa[128]={};};
void iwx_mld_fill_he_sta(ieee80211_node *,iwx_sta_cfg_cmd *p){p->pkt_ext[0][0][0]=0x7e;p->htc_flags=0x1234;}
struct ItlIwx{iwx_sta_cfg_cmd wire;unsigned calls=0;
 bool iwx_mimo_enabled(iwx_softc *){return true;}
 unsigned iwx_cmd_id(unsigned c,unsigned g,unsigned v){return c|(g<<8)|(v<<16);}
 int iwx_send_cmd_pdu(iwx_softc *,unsigned,unsigned flags,unsigned len,const void *p){assert(flags==0&&len==96);memcpy(&wire,p,len);++calls;return 0;}
 int iwx_mld_sta_config_cmd(iwx_softc *,iwx_node *,int);int old_sta_config(iwx_softc *,iwx_node *,int);
};
''' +old+'\n'+new+r'''
int main(){iwx_softc sc;iwx_node ni;ItlIwx hal;uint32_t seed=1;unsigned changes=0;
 for(unsigned i=0;i<100000;++i){auto rnd=[&](){seed=seed*1664525+1013904223;return seed;};
  unsigned cap=i&1,assoc=(i>>1)&1,valid=(i>>2)&1,rsn=(i>>3)&1;
  memset(sc.sc_enabled_capa,cap?255:0,sizeof(sc.sc_enabled_capa));sc.sc_ic.ic_flags=rsn?IEEE80211_F_RSNON:0;
  ni.in_ni.ni_port_valid=valid;ni.in_ni.ni_flags=rnd();ni.in_ni.ni_ampdu_param=rnd();ni.in_ni.ni_vhtcaps=rnd();ni.in_ni.ni_rx_nss=1+(rnd()%2);
  hal.old_sta_config(&sc,&ni,assoc);auto before=hal.wire;
  hal.iwx_mld_sta_config_cmd(&sc,&ni,assoc);auto after=hal.wire;
  bool mfp=ni.in_ni.ni_flags&IEEE80211_NODE_MFP;
  assert(after.mfp==unsigned(mfp||(cap&&!(assoc&&(valid||!rsn)))));
  if(mfp)assert(after.mfp==1);
  changes+=before.mfp!=after.mfp;before.mfp=after.mfp;assert(!memcmp(&before,&after,sizeof(before)));
 }
 assert(changes>0);puts("PASS:100000 actual96-byte STA command comparisons; only authorized non-MFP flag changes, negotiated MFP retained and all other command fields unchanged (ASan/UBSan).");}
'''
methods='\n'.join(block(source,sig) for sig in ['void ItlIwx::\niwx_wcl_port_authorized(', 'void ItlIwx::\niwx_mld_authorized_task('])
task=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <map>
#include <string>
#include <cstddef>
#define AIRPORT_WCL 1
#include "ieee80211_wcl_rsn_diag.h"
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
enum{IEEE80211_S_RUN=4,IEEE80211_F_RSNON=1,IWX_FLAG_SHUTDOWN=1,IWX_FLAG_STA_ACTIVE=2,IEEE80211_NODE_MFP=128};
using IOReturn=int;constexpr int kIOReturnSuccess=0;struct OSObject{};
struct Node{unsigned ni_flags=0,ni_port_valid=1;};struct iwx_node{Node in_ni;void *in_phyctxt=(void *)1;};
struct ieee80211com{void *ic_softc=nullptr;unsigned ic_state=4,ic_flags=1;bool ic_wcl_teardown_pending=false;Node *ic_bss=nullptr;wcl_rsn_trace ic_wcl_rsn_trace={};};
struct PCI{std::map<std::string,unsigned> values;void setProperty(const char *k,unsigned v,unsigned bits){assert(bits==32);values[k]=v;}};
struct iwx_softc{ieee80211com sc_ic;unsigned ns_nstate=4,sc_flags=2,sc_mld_assoc_epoch=1,sc_mld_authorized_epoch=0,sc_mld_authorized_done_epoch=0,sc_mld_authorized_updates=0;int sc_generation=1;PCI *sc_pcitag;int mld_authorized_task=0;};
void *systq=(void *)1;
struct Loop{bool gated=true;bool inGate(){return gated;}};
struct Gate{Loop *loop;template<typename F>int runAction(F f,void *p){assert(!loop->gated);loop->gated=true;auto ret=f(nullptr,p,nullptr,nullptr,nullptr);loop->gated=false;return ret;}};
struct ItlIwx{iwx_softc com;Loop loop;Gate gate{&loop};bool mld=true;unsigned queued=0,calls=0;int change=0,error=0;void iwx_awdl_ctx_add(iwx_softc *,iwx_node *){}
 bool iwx_use_mld_api(iwx_softc *){return mld;}Loop *getMainWorkLoop(){return &loop;}Gate *getMainCommandGate(){return &gate;}
 void iwx_add_task(iwx_softc *,void *,int *){++queued;}
 int iwx_mld_sta_config_cmd(iwx_softc *sc,iwx_node *,int assoc){assert(loop.gated&&assoc==1);++calls;
  if(change==1)++sc->sc_generation;if(change==2)++sc->sc_mld_assoc_epoch;if(change==3)sc->sc_ic.ic_wcl_teardown_pending=true;if(change==4)sc->ns_nstate=0;if(change==5)sc->sc_flags|=1;return error;}
 static void iwx_wcl_port_authorized(ieee80211com *);static void iwx_mld_authorized_task(void *);
};
''' + methods+r'''
int main(){for(unsigned which=0;which<15;++which){ItlIwx hal;auto &sc=hal.com;PCI pci;iwx_node node;sc.sc_pcitag=&pci;sc.sc_ic.ic_softc=&sc;sc.sc_ic.ic_bss=&node.in_ni;sc.sc_ic.ic_wcl_rsn_trace.enabled=1;
 hal.iwx_wcl_port_authorized(&sc.sc_ic);assert(hal.queued==1&&sc.sc_mld_authorized_epoch==1);
 if(which==1)++sc.sc_mld_assoc_epoch;if(which==2)sc.sc_flags|=1;if(which==3)sc.ns_nstate=0;if(which==4)sc.sc_ic.ic_wcl_teardown_pending=true;
 if(which==5)node.in_ni.ni_port_valid=0;if(which==6)node.in_phyctxt=nullptr;
 if(which>=7&&which<=11)hal.change=which-6;if(which==12)hal.error=5;if(which==13)hal.loop.gated=false;
 if(which==14){sc.sc_ic.ic_flags=0;node.in_ni.ni_port_valid=0;}
 hal.iwx_mld_authorized_task(&sc);
 bool rejected=which>=1&&which<=6,stale=which>=7&&which<=11;
 assert(hal.calls==unsigned(!rejected));
 if(rejected||stale){assert(!sc.sc_mld_authorized_updates&&!sc.sc_mld_authorized_done_epoch&&pci.values.empty());}
 else if(which==12){assert(!sc.sc_mld_authorized_updates&&!sc.sc_mld_authorized_done_epoch&&pci.values["ItlwmMldAuthorizedError"]==5);}
 else {assert(sc.sc_mld_authorized_updates==1&&sc.sc_mld_authorized_done_epoch==1);auto q=hal.queued;hal.iwx_wcl_port_authorized(&sc.sc_ic);assert(hal.queued==q);}
 }
 puts("PASS: actual authorization callback/task in15 lifecycle/error schedules: gate dispatch, stale epoch/reset/teardown during command wait rejected, errors not committed, duplicate done skipped, open/RSN handling.");}
'''
# The shipped API92 really enables this firmware capability.
f=(r/'firmware-bz92/iwlwifi-bz-b0-fm-c0-92.ucode').read_bytes();assert hashlib.sha256(f).hexdigest()=='820f9fb78e43b424befdc2d9253e2b56f9d2bb250d8a42217d9bb1d8b6d7957d'
pos=88;caps=[]
while pos+8<=len(f):
 typ,l=struct.unpack_from('<II',f,pos);pos+=8;assert l<=len(f)-pos
 if typ==30:
  idx,bits=struct.unpack_from('<II',f,pos);caps.extend(idx*32+i for i in range(32) if bits>>i&1)
 pos+=(l+3)&~3
assert pos==len(f) and 114 in caps
with tempfile.TemporaryDirectory() as d:
 p=Path(d)
 for name,text in [('builder',builder),('task',task)]:
  (p/(name+'.cpp')).write_text(text)
  subprocess.run(['clang++','-std=c++14','-fsanitize=address,undefined','-Wall','-Wextra','-Werror','-I',str(r/'itl80211/openbsd/net80211'),str(p/(name+'.cpp')),'-o',str(p/name)],check=True)
  subprocess.run([str(p/name)],check=True)
print('PASS: pinned API92 capability114 enabled; command96-byte ABI; kernel-entry path queues work instead of blocking RX.')
