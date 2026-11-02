"""Actual disconnect callbacks, legacy behavior, late link-up and key ACK tags."""
from pathlib import Path
import subprocess,tempfile,re
r=Path(__file__).resolve().parents[1];n=r/'itl80211/openbsd/net80211';s=(n/'ieee80211_input.c').read_text();proto=(n/'ieee80211_proto.c').read_text()
def block(s,sig):
 a=s.index(sig);b=s.index('{',a)+1;depth=1
 while depth:depth+=(s[b]=='{')-(s[b]=='}');b+=1
 return s[a:b]
methods='\n'.join(block(s,sig) for sig in ['static bool\nieee80211_wcl_peer_disconnect(', 'void\nieee80211_recv_deauth(', 'void\nieee80211_recv_disassoc('])
link=block(proto,'void\nieee80211_set_link_state(')
harness=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <sys/mman.h>
#include <unistd.h>
#define IEEE80211_STA_ONLY 1
#include "ieee80211_wcl_rsn_diag.h"
#include "iwx_boot_checks.h"
using u_int8_t=uint8_t;using u_int16_t=uint16_t;
enum{IEEE80211_M_STA=1,IEEE80211_M_MONITOR=2,IEEE80211_S_INIT=0,IEEE80211_S_AUTH=2,IEEE80211_S_ASSOC=3,IEEE80211_S_RUN=4,IEEE80211_F_BGSCAN=1,IEEE80211_F_DISABLE_BG_AUTO_CONNECT=2,IEEE80211_F_STAYAUTH=4,IEEE80211_EVT_STA_DEAUTH=2,IEEE80211_FC0_SUBTYPE_DEAUTH=0xc0,IEEE80211_FC0_SUBTYPE_DISASSOC=0xa0,LINK_STATE_DOWN=0,LINK_STATE_UP=1,kIONetworkLinkValid=1,kIONetworkLinkActive=2};
struct Controller{unsigned updates=0;void *getCurrentMedium(){return nullptr;}void setLinkStatus(unsigned,void *p=nullptr){(void)p;++updates;}};
struct _ifnet{int if_link_state=0;Controller *controller=nullptr;};
struct ieee80211_node{uint8_t ni_macaddr[6]={2,1,2,3,4,5},ni_bssid[6]={2,1,2,3,4,5};};
struct ieee80211com{
 int ic_opmode=1,ic_state=4;unsigned ic_flags=0,ic_userflags=0;uint16_t ic_deauth_reason=0;
 uint8_t ic_myaddr[6]={2,2,3,4,5,6};bool ic_wcl_teardown_pending=false;
 struct{unsigned is_rx_deauth=0,is_rx_disassoc=0;}ic_stats;
 wcl_rsn_trace ic_wcl_rsn_trace={};_ifnet ic_if;
 void(*ic_event_handler)(ieee80211com *,int,void *)=nullptr;
 unsigned newstates=0,events=0,queued=999,attempted=999;bool immediateRetry=false,waitedForCleanup=false;
};
struct ieee80211_frame{uint8_t i_fc[2],pad[2],i_addr1[6],i_addr2[6],i_addr3[6],seq[2];};
struct Packet{unsigned length=26;alignas(8) uint8_t bytes[26]={};};using mbuf_t=Packet *;
#define mbuf_len(m) ((m)->length)
#define mtod(m,t) ((t)((m)->bytes))
#define LE_READ_2(p) (uint16_t((p)[0])|(uint16_t((p)[1])<<8))
template<typename...T>void XYLog(const char *,T...){ }
#define DPRINTF(...) ((void)0)
#define IEEE80211_ADDR_EQ(a,b) (!memcmp(a,b,6))
void ieee80211_new_state(ieee80211com *ic,int state,int){++ic->newstates;ic->attempted=state;
#ifdef AIRPORT_WCL
 assert(iwx_wcl_state_transition_allowed(ic->ic_wcl_teardown_pending,state==0,ic->ic_state==0));
#endif
 ic->queued=state;
}
void event(ieee80211com *ic,int code,void *data){assert(code==2&&!data);++ic->events;
#ifdef AIRPORT_WCL
 assert(ic->queued==0 && ic->ic_wcl_teardown_pending);
 // A synchronous native retry must see the cleanup fence and defer.
 if(ic->immediateRetry){ic->waitedForCleanup=ic->ic_wcl_teardown_pending;assert(!iwx_wcl_state_transition_allowed(ic->ic_wcl_teardown_pending,false,false));}
#endif
}
''' + '#ifdef AIRPORT_WCL\n'+methods[:methods.index('void\nieee80211_recv_deauth(')]+'#endif\n'+methods[methods.index('void\nieee80211_recv_deauth('):]+ '\n'+link+r'''
int main(){
 for(unsigned type=0;type<2;++type)for(unsigned state=2;state<=4;++state)for(unsigned reason:{3u,8u,39u,311u})for(unsigned retry=0;retry<2;++retry){
  ieee80211com ic;ic.ic_state=state;ic.ic_event_handler=event;ic.immediateRetry=retry;
  ieee80211_node ni;Packet m;auto wh=reinterpret_cast<ieee80211_frame *>(m.bytes);
  memcpy(wh->i_addr1,ic.ic_myaddr,6);memcpy(wh->i_addr2,ni.ni_macaddr,6);memcpy(wh->i_addr3,ni.ni_bssid,6);
  m.bytes[24]=reason&255;m.bytes[25]=reason>>8;
  if(type)ieee80211_recv_disassoc(&ic,&m,&ni);else ieee80211_recv_deauth(&ic,&m,&ni);
#ifdef AIRPORT_WCL
  assert(ic.newstates==1&&ic.queued==0&&ic.events==1&&ic.ic_deauth_reason==reason);
  assert(ic.waitedForCleanup==bool(retry));
#else
  assert(ic.newstates==1&&ic.queued==(type?3u:2u)&&ic.events==unsigned(!type));
#endif
  assert(ic.ic_stats.is_rx_deauth==unsigned(!type)&&ic.ic_stats.is_rx_disassoc==type);
 }
 {ieee80211com ic;ieee80211_node ni;Packet p;p.length=25;ieee80211_recv_deauth(&ic,&p,&ni);ieee80211_recv_disassoc(&ic,&p,&ni);assert(!ic.newstates&&!ic.events);}
 {ieee80211com ic;Controller c;ic.ic_if.controller=&c;ic.ic_wcl_teardown_pending=true;
  ieee80211_set_link_state(&ic,1);
#ifdef AIRPORT_WCL
  assert(!c.updates&&!ic.ic_if.if_link_state);
#else
  assert(c.updates==1&&ic.ic_if.if_link_state==1);
#endif
  ic.ic_wcl_teardown_pending=false;ieee80211_set_link_state(&ic,1);assert(c.updates==1&&ic.ic_if.if_link_state==1);
  ieee80211_set_link_state(&ic,0);assert(c.updates==2&&ic.ic_if.if_link_state==0);
 }
 auto guard=(uint8_t *)mmap(nullptr,getpagesize(),PROT_NONE,MAP_ANON|MAP_PRIVATE,-1,0);assert(guard!=MAP_FAILED);
 for(unsigned size=0;size<160;++size)if(size!=80)assert(!wcl_key_command_tag(0x518,guard,size));
 assert(!wcl_key_command_tag(0x519,guard,80));
 // Only public fields occupy the readable page; secret bytes16..79 are unreadable.
 auto two=(uint8_t *)mmap(nullptr,getpagesize()*2,PROT_READ|PROT_WRITE,MAP_ANON|MAP_PRIVATE,-1,0);assert(two!=MAP_FAILED);
 assert(!mprotect(two+getpagesize(),getpagesize(),PROT_NONE));auto pub=two+getpagesize()-16;
 memset(pub,0,16);pub[0]=1;pub[8]=2;pub[12]=0x42;auto tag=wcl_key_command_tag(0x518,pub,80);assert(tag==0x01020042);
 for(unsigned i=0;i<256;++i){pub[0]=i;assert(bool(wcl_key_command_tag(0x518,pub,80))==(i==1||i==3));}
 for(unsigned failed=0;failed<2;++failed)for(unsigned cookie:{0u,1u,2u}){wcl_rsn_trace t={};t.enabled=1;wcl_key_command_completed(&t,cookie,1,tag,failed);assert(t.count==unsigned(cookie==1));if(t.count)assert(t.events[0].code==(failed?28u:27u));}
 munmap(guard,getpagesize());munmap(two,getpagesize()*2);
 puts("PASS: actual deauth/disassoc lifecycle48 schedules, early native retry sees INIT fence, truncated frames; actual link-state blocks late UP during cleanup; key observation never reads secret bytes and rejects stale cookies (ASan/UBSan).");
}
'''
harness=harness.replace('#include <cstdio>','#include <cstdio>\n#include <initializer_list>')
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.cpp').write_text(harness)
 for mode in ['wcl','legacy']:
  cmd=['clang++','-std=c++14','-fsanitize=address,undefined','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-I',str(n),'-I',str(r/'itlwm/hal_iwx')]
  if mode=='wcl':cmd+=['-DAIRPORT_WCL']
  subprocess.run(cmd+[str(p/'test.cpp'),'-o',str(p/mode)],check=True);subprocess.run([str(p/mode)],check=True)
# Actual command integration must mark before the doorbell and acknowledge
# only pending slots, without turning RX into a blocking key wait.
iwx=(r/'itlwm/hal_iwx/ItlIwx.cpp').read_text();send=block(iwx,'int ItlIwx::\niwx_send_cmd(');done=block(iwx,'void ItlIwx::\niwx_cmd_done(')
assert send.index('wcl_key_command_tag(')<send.index('IWX_WRITE(sc, IWX_HBUS_TARG_WRPTR')
assert done.index('if (!(data->flags & IWX_TXDATA_FLAG_CMD_PENDING))')<done.index('wcl_key_command_completed(')
key=block(iwx,'int ItlIwx::\niwx_mld_sec_key_cmd(');assert 'IWX_CMD_ASYNC' in key
print('PASS: legacy AUTH/ASSOC behavior retained; key transport remains asynchronous and command diagnostics are slot/pending/cookie scoped.')
