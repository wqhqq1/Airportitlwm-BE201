"""Compile the real command completion handler against pending-slot cases."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[1];s=(r/'itlwm/hal_iwx/ItlIwx.cpp').read_text();a=s.index('void ItlIwx::\niwx_cmd_done(');b=s.index('{',a)+1;depth=1
while depth:depth+=(s[b]=='{')-(s[b]=='}');b+=1
method=s[a:b]
harness=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#define AIRPORT_WCL 1
#include "ieee80211_wcl_rsn_diag.h"
#define IWX_DQA_CMD_QUEUE 0
#define IWX_TXDATA_FLAG_CMD_PENDING 2
#define IWX_DATA_PATH_GROUP 5
#define IWX_SEC_KEY_CMD 0x18
#define IWX_WIDE_ID(g,c) (((g)<<8)|(c))
#define DPRINTF(...) ((void)0)
unsigned frees=0;
void mbuf_freem(void *){++frees;}
struct Gate{unsigned wakes=0;void commandWakeup(void *){++wakes;}};
struct iwx_tx_data{unsigned flags=0,wcl_rsn_cookie=0,wcl_rsn_kind=0;void *m=nullptr;};
struct iwx_tx_ring{int ring_count=4;unsigned queued=1;iwx_tx_data data[4];int desc[4];};
struct iwx_softc{iwx_tx_ring txq[1];struct{wcl_rsn_trace ic_wcl_rsn_trace={};unsigned ic_wcl_rsn_cookie=1;}sc_ic;};
struct ItlIwx{Gate gate;Gate *getMainCommandGate(){return &gate;}void iwx_cmd_done(iwx_softc *,int,int,int);};
''' +method+r'''
int main(){
 for(int qid=-1;qid<2;++qid)for(int idx=-1;idx<5;++idx)for(unsigned pending=0;pending<2;++pending)for(unsigned cookie:{0u,1u,2u})for(unsigned code:{0x518u,0x519u}){
  iwx_softc sc;ItlIwx hal;auto &t=sc.sc_ic.ic_wcl_rsn_trace;t.enabled=1;auto &slot=sc.txq[0].data[1];
  slot.flags=pending?2:0;slot.wcl_rsn_cookie=cookie;slot.wcl_rsn_kind=0x01000002;slot.m=&sc;frees=0;
  hal.iwx_cmd_done(&sc,qid,idx,code);
  bool done=qid==0&&idx==1&&pending;bool observed=done&&cookie==1&&code==0x518;
  assert(t.count==unsigned(observed));if(observed)assert(t.events[0].code==27&&t.events[0].value==0x01000002);
  assert(frees==unsigned(done)&&hal.gate.wakes==unsigned(done));
  assert(sc.txq[0].queued==unsigned(!done));
  if(done)assert(!slot.m&&!slot.flags&&!slot.wcl_rsn_cookie&&!slot.wcl_rsn_kind);
 }
 puts("PASS: actual command completion across216 pending/index/queue/cookie/opcode cases; only matching key replies observed, stale/malformed callbacks safe, original wake/free/queue handling preserved (ASan/UBSan).");
}
'''
harness=harness.replace('#include <cstdio>','#include <cstdio>\n#include <initializer_list>')
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.cpp').write_text(harness)
 subprocess.run(['clang++','-std=c++14','-fsanitize=address,undefined','-Wall','-Wextra','-Werror','-I',str(r/'itl80211/openbsd/net80211'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
