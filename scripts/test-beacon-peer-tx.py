"""Peer-frame rejection and real single-frame TX completion diagnostics."""
from pathlib import Path
import re,subprocess,tempfile
r=Path(__file__).resolve().parents[1];n=r/'itl80211/openbsd/net80211';iwx=(r/'itlwm/hal_iwx/ItlIwx.cpp').read_text();inp=(n/'ieee80211_input.c').read_text()
a=inp.index('    /* BE201 peer-teardown filter BEGIN:');b=inp.index('    /* BE201 peer-teardown filter END */',a);gate=inp[a:b]
assert a<inp.index('    /* duplicate detection')
assert inp.index('if (mbuf_len(m) < hdrlen)')<a
start=iwx.index('void ItlIwx::\niwx_rx_tx_cmd_single(');end=iwx.index('{',start)+1;depth=1
while depth:depth+=(iwx[end]=='{')-(iwx[end]=='}');end+=1
single=iwx[start:end]
source=r'''
#include <cassert>
#include <cstring>
#include <cstdio>
#include <cstdint>
#include <sys/mman.h>
#include <unistd.h>
#define AIRPORT_WCL 1
#include "ieee80211_wcl_rsn_diag.h"
enum {IEEE80211_M_STA=1,IEEE80211_S_AUTH=2,IEEE80211_FC0_TYPE_MGT=0,IEEE80211_FC0_SUBTYPE_DEAUTH=0xc0,IEEE80211_FC0_SUBTYPE_DISASSOC=0xa0};
struct Node{uint8_t ni_macaddr[6]={2,1,2,3,4,5},ni_bssid[6]={2,1,2,3,4,5};};
struct Netstat{unsigned outputErrors=0;};struct _ifnet{Netstat *netStat;};
struct ieee80211com {
 int ic_opmode=IEEE80211_M_STA,ic_state=2;Node *ic_bss;uint8_t ic_myaddr[6]={2,9,8,7,6,5};
 struct{unsigned is_rx_wrongbss=0;}ic_stats;
 wcl_rsn_trace ic_wcl_rsn_trace={};uint32_t ic_wcl_rsn_cookie=1;_ifnet iface;
};
struct Frame{uint8_t i_addr1[6],i_addr2[6],i_addr3[6];};
bool receive(ieee80211com *ic,Frame *wh,unsigned type,unsigned subtype){
''' + gate + r'''
 return true;
out:return false;
}
#define IC2IFP(ic) (&(ic)->iface)
#define le16toh(x) (x)
#define KASSERT(c,m) assert(c)
#define DPRINTFN(...) ((void)0)
#define IWX_TX_STATUS_MSK 255
#define IWX_TX_STATUS_SUCCESS 1
struct iwx_tx_resp{unsigned frame_count;struct{uint16_t status;}status;uint8_t failure_frame=0;};
struct iwx_rx_packet {iwx_tx_resp data[1];};
struct iwx_tx_data{unsigned type=8,wcl_rsn_cookie=0,wcl_rsn_kind=0;uint8_t awdl_kind=0,awdl_umi=0,awdl_umi_peer[6]={};};
struct iwx_awdl_probe{ struct { unsigned own_ok,own_fail; } ctx;};static inline void iwx_awdl_umi_note(iwx_awdl_probe*,const uint8_t*,bool){}static int systq;static inline void iwx_add_task(void*,int,void*){}static inline void iwx_awdl_tx_note_presence(struct iwx_softc*){}static inline void iwx_awdl_amsdu_note_done(iwx_awdl_probe*,bool){}static inline void iwx_awdl_tx_note_done(iwx_awdl_probe*,bool,bool,uint32_t,uint32_t){}
struct iwx_softc{ieee80211com sc_ic;uint8_t sc_mgmt_last_antenna_idx=0;iwx_awdl_probe sc_awdl_probe;int awdl_umi_task=0;};
struct ItlIwx{unsigned toggles=0;void iwx_toggle_tx_ant(iwx_softc *,uint8_t *){++toggles;}void iwx_rx_tx_cmd_single(iwx_softc *,iwx_rx_packet *,iwx_tx_data *);};
''' + single + r'''
int main(){
 Node node;ieee80211com ic;ic.ic_bss=&node;ic.ic_wcl_rsn_trace.enabled=1;
 Frame good;memcpy(good.i_addr1,ic.ic_myaddr,6);memcpy(good.i_addr2,node.ni_macaddr,6);memcpy(good.i_addr3,node.ni_bssid,6);
 for(unsigned subtype:{0xc0u,0xa0u}){
  assert(receive(&ic,&good,0,subtype));
  for(unsigned field=0;field<3;++field)for(unsigned byte=0;byte<6;++byte)for(unsigned bit=0;bit<8;++bit){
   Frame bad=good;uint8_t *p=field==0?bad.i_addr1:field==1?bad.i_addr2:bad.i_addr3;p[byte]^=1u<<bit;
   assert(!receive(&ic,&bad,0,subtype));
  }
  Frame broadcast=good;memset(broadcast.i_addr1,255,6);assert(receive(&ic,&broadcast,0,subtype));
  Frame multicast=good;multicast.i_addr1[0]=1;assert(!receive(&ic,&multicast,0,subtype));
 }
 assert(!wcl_sta_teardown_matches(nullptr,good.i_addr2,good.i_addr3,ic.ic_myaddr,node.ni_macaddr,node.ni_bssid));
 Frame unrelated=good;unrelated.i_addr2[2]^=1;
 for(unsigned type=0;type<4;++type)for(unsigned subtype=0;subtype<256;++subtype){
  bool teardown=type==0&&(subtype==0xc0||subtype==0xa0);
  assert(receive(&ic,&unrelated,type,subtype)==!teardown);
 }
 ic.ic_state=1;assert(receive(&ic,&unrelated,0,0xc0));ic.ic_state=2;
 ic.ic_opmode=0;assert(receive(&ic,&unrelated,0,0xc0));
 auto guard=(uint8_t *)mmap(nullptr,getpagesize(),PROT_NONE,MAP_ANON|MAP_PRIVATE,-1,0);assert(guard!=MAP_FAILED);
 for(unsigned n=0;n<8;++n)assert(!wcl_rsn_tx_kind(guard,n,2,0,0));
 assert(!wcl_rsn_tx_kind(guard,8,2,1,0)&&!wcl_rsn_tx_kind(guard,8,2,0,1)&&!wcl_rsn_tx_kind(guard,8,3,0,0));
 uint8_t snap[8]={0xaa,0xaa,3,0,0,0,0x88,0x8e};
 for(unsigned k:{2u,4u}){assert(wcl_rsn_tx_kind(snap,8,k,0,0)==k);
  for(unsigned b=0;b<8;++b)for(unsigned bit=0;bit<8;++bit){snap[b]^=1u<<bit;assert(!wcl_rsn_tx_kind(snap,8,k,0,0));snap[b]^=1u<<bit;}}
 iwx_softc sc;Netstat stats;sc.sc_ic.iface.netStat=&stats;sc.sc_ic.ic_wcl_rsn_trace.enabled=1;ItlIwx hal;
 for(unsigned status=0;status<256;++status)for(unsigned kind:{0u,2u,4u})for(unsigned cookie:{0u,1u,2u}){
  sc.sc_ic.ic_wcl_rsn_trace={};sc.sc_ic.ic_wcl_rsn_trace.enabled=1;stats.outputErrors=0;
  iwx_tx_data txd;txd.wcl_rsn_cookie=cookie;txd.wcl_rsn_kind=kind;iwx_rx_packet pkt={};pkt.data[0].frame_count=1;pkt.data[0].status.status=status;
  hal.iwx_rx_tx_cmd_single(&sc,&pkt,&txd);
  assert(stats.outputErrors==unsigned(status!=1));
  auto &t=sc.sc_ic.ic_wcl_rsn_trace;bool match=cookie==1&&(kind==2||kind==4);
  assert(t.count==unsigned(match));if(match)assert(t.events[0].code==(kind==2?23u:24u)&&t.events[0].value==status);
 }
 munmap(guard,getpagesize());
 puts("PASS: actual pre-duplicate filter, 288 foreign-frame mutations, broadcast/other traffic/lifecycle preservation; unreadable SNAP guards; actual TX completion across2304 status/kind/cookie cases, no change to TX error handling (ASan/UBSan).");
}
'''
source=source.replace('#include <cstdio>','#include <cstdio>\n#include <initializer_list>')
# Integration: overwrite per-slot markers before data doorbell; observe only
# the already validated single-frame response, then clear on reclaim.
tx=iwx[iwx.index('int ItlIwx::\niwx_tx(struct'):iwx.index('int ItlIwx::\niwx_flush_sta_tids(')]
assert tx.index('data->wcl_rsn_kind = rsnKind')<tx.index('/* Kick TX ring. */')
assert 'txd->wcl_rsn_kind = txd->wcl_rsn_cookie = 0;' in iwx
rx=iwx[iwx.index('void ItlIwx::\niwx_rx_tx_cmd(struct'):iwx.index('void ItlIwx::\niwx_rx_bmiss(')]
assert rx.index('if (!itlTxCompletionValid(')<rx.index('iwx_rx_tx_cmd_single(sc, pkt, txd)')
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.cpp').write_text(source)
 subprocess.run(['clang++','-std=c++14','-fsanitize=address,undefined','-Wall','-Wextra','-Werror','-I',str(n),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
