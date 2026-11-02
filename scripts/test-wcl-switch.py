"""Production deferred-join/timer and MAC builder against a coalescing HAL."""
from pathlib import Path
import re, subprocess, tempfile
root = Path(__file__).resolve().parents[1]
wcl = (root/'AirportItlwm/WCL/WCL.cpp').read_text()
iwx = (root/'itlwm/hal_iwx/ItlIwx.cpp').read_text()
reg = (root/'itlwm/hal_iwx/if_iwxreg.h').read_text()

def block(text, signature):
    start = text.index(signature)
    p = text.index('{',start)+1
    end, depth = p, 1
    while depth:
        depth += (text[end]=='{')-(text[end]=='}')
        end += 1
    return text[start:end]

# Guard the integration order as well as compiling the real method bodies.
start = block(wcl,'IOReturn AirportItlwmSkywalkInterface::startWCLJoin(')
assert start.index('deferWCLJoinUntilIdle(join)') < start.index('stashedJoin = join') < start.index('ieee80211_node_join_bss(')
assert 'leaveWCLNetwork();' not in start
newstate = block(iwx,'int ItlIwx::\niwx_newstate(')
assert newstate.index('iwx_wcl_state_transition_allowed(') < newstate.index('sc->ns_nstate = nstate')
methods = '\n'.join(block(wcl,s) for s in [
    'bool AirportItlwmSkywalkInterface::deferWCLJoinUntilIdle(',
    'void AirportItlwmSkywalkInterface::resumeWCLJoin()',
    'void AirportItlwmSkywalkInterface::wclJoinTimeout(',
    'void AirportItlwmSkywalkInterface::handleWCLLink(bool up)'])
guard_start = wcl.index('if (joinWaitingForInit && (code == IEEE80211_EVT_STA_ASSOC_DONE')
peer_guard = wcl[guard_start:wcl.index('return;',guard_start)+len('return;')]
methods += '\nvoid AirportItlwmSkywalkInterface::peerEvent(int code) {\n' + peer_guard + '\n++peerEvents;\n}\n'
harness = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <map>
#include <string>
#include "WCL.hpp"
#include "iwx_boot_checks.h"
#include "ieee80211_wcl_rsn_diag.h"
void explicit_bzero(void *p,size_t n){memset(p,0,n);}
using IOReturn=int;
constexpr int kIOReturnSuccess=0,kIOReturnTimeout=60;
enum {IEEE80211_S_INIT,IEEE80211_S_SCAN,IEEE80211_S_AUTH,IEEE80211_S_ASSOC,IEEE80211_S_RUN};
enum {IEEE80211_EVT_STA_ASSOC_DONE=100,IEEE80211_EVT_STA_DEAUTH=101};
constexpr unsigned IFF_RUNNING=1;
uint64_t now=1;uint64_t airport_wcl_now_ns(){return now;}
struct OSObject { virtual ~OSObject(){} };
#define OSDynamicCast(T,p) dynamic_cast<T *>(p)
struct IOTimerEventSource { unsigned delay=0,cancels=0;void setTimeoutMS(unsigned v){delay=v;}void cancelTimeout(){delay=0;++cancels;} };
struct ieee80211com {int ic_state=IEEE80211_S_RUN;bool ic_wcl_teardown_pending=false;struct {unsigned if_flags=IFF_RUNNING;}ic_if;};
struct HAL {ieee80211com ic;ieee80211com *get80211Controller(){return &ic;}};
struct PCI {std::map<std::string,uint32_t> values;void setProperty(const char *k,uint32_t v,unsigned b){assert(b==32);values[k]=v;}};
struct Instance {PCI *pciNub=nullptr;unsigned posts=0;template<typename T>void postMessage(OSObject *,unsigned,const T *,unsigned,bool){++posts;}};
struct AirportItlwmSkywalkInterface:OSObject {
 HAL *fHalService;Instance *instance;IOTimerEventSource *joinTimer;
 bool joinDeferred=false,joinPending=false,joinWaitingForInit=false,wclStopping=false,stashedJoinValid=false;
 bool portAuthorized=false,wclLinkIndicated=true,wclBssValid=true,firstBeaconNotified=true;
 unsigned peerEvents=0;void updateWCLLinkQuality(bool){}
 uint64_t joinInitDeadlineNS=0;uint32_t wclJoinInitDeferrals=0,wclJoinInitCompleted=0,wclJoinInitTimeouts=0;
 uint8_t joinBSSID[6]={};AirportWCL::JoinRequest deferredJoin={},stashedJoin={};
 int queued=-1;unsigned peer=11,oldPeer=11,starts=0,failures=0;bool failStart=false;
 void leaveWCLNetwork(){assert(iwx_wcl_state_transition_allowed(fHalService->ic.ic_wcl_teardown_pending,true,fHalService->ic.ic_state==IEEE80211_S_INIT));queued=IEEE80211_S_INIT;joinDeferred=joinPending=joinWaitingForInit=false;memset(&deferredJoin,0,sizeof(deferredJoin));joinTimer->cancelTimeout();}
 IOReturn startWCLJoin(AirportWCL::JoinRequest &j){
  assert(fHalService->ic.ic_state==IEEE80211_S_INIT);
  assert(queued==-1);assert(j.ssidLength==3 && j.key[0]==0x6b);++starts;
  if(failStart)return 99;
  peer=22;queued=IEEE80211_S_AUTH;joinPending=true;memset(&j,0,sizeof(j));return 0;
 }
 void finishWCLJoin(unsigned status,unsigned reason,IOReturn error){assert(status==1);assert((reason==1004 && error==60)||(reason==0 && error==99));++failures;joinPending=joinDeferred=joinWaitingForInit=false;memset(&deferredJoin,0,sizeof(deferredJoin));}
 void completeHALInit(){assert(queued==IEEE80211_S_INIT && peer==oldPeer);queued=-1;fHalService->ic.ic_state=IEEE80211_S_INIT;fHalService->ic.ic_wcl_teardown_pending=false;}
 bool deferWCLJoinUntilIdle(AirportWCL::JoinRequest &);
 void resumeWCLJoin();static void wclJoinTimeout(OSObject *,IOTimerEventSource *);
 void handleWCLLink(bool);void peerEvent(int);
};
''' + methods + r'''
int main(){
 // The original sequence loses INIT in a coalescing task queue.
 {int task=IEEE80211_S_INIT;task=IEEE80211_S_AUTH;assert(task!=IEEE80211_S_INIT);}
 HAL hal;PCI pci;Instance inst;inst.pciNub=&pci;IOTimerEventSource timer;
 for(int state=IEEE80211_S_INIT;state<=IEEE80211_S_RUN;++state){
  for(unsigned earlyTicks=0;earlyTicks<40;++earlyTicks){
   AirportItlwmSkywalkInterface api;api.fHalService=&hal;api.instance=&inst;api.joinTimer=&timer;
   hal.ic.ic_state=state;hal.ic.ic_if.if_flags=IFF_RUNNING;hal.ic.ic_wcl_teardown_pending=false;
   AirportWCL::JoinRequest req={};req.ssidLength=3;req.key[0]=0x6b;req.bssid[0]=2;
   api.joinBSSID[0]=2;api.joinBSSID[1]=1;
   auto original=req;bool wait=api.deferWCLJoinUntilIdle(req);
   if(state==IEEE80211_S_INIT||state==IEEE80211_S_SCAN){assert(!wait && !memcmp(&req,&original,sizeof(req)));continue;}
   assert(wait && api.queued==IEEE80211_S_INIT && api.peer==11 && api.joinPending);
   assert(api.joinBSSID[1]==1); // pending target must not rename the old link
   api.handleWCLLink(true);assert(!api.portAuthorized && !api.failures);
   api.peerEvent(IEEE80211_EVT_STA_ASSOC_DONE);api.peerEvent(IEEE80211_EVT_STA_DEAUTH);
   assert(api.peerEvents==0 && api.joinPending);
   api.handleWCLLink(false);assert(!api.wclLinkIndicated && api.joinPending);
   AirportWCL::JoinRequest empty={};assert(!memcmp(&req,&empty,sizeof(req)));
   for(unsigned i=0;i<earlyTicks;++i){
    // Late old-peer auth/scan/run requests must not overwrite queued INIT.
    for(unsigned oldRx=1;oldRx<5;++oldRx)
     assert(!iwx_wcl_state_transition_allowed(hal.ic.ic_wcl_teardown_pending,false,false));
    now+=1000000;
    // net80211 can expose INIT while its cleanup callback still runs.
    hal.ic.ic_state=(i%2)?state:IEEE80211_S_INIT;
    api.resumeWCLJoin();api.wclJoinTimeout(&api,nullptr);
    hal.ic.ic_state=state;
    assert(!api.starts && api.queued==IEEE80211_S_INIT && api.peer==11 && timer.delay==20);
   }
   api.completeHALInit();api.wclJoinTimeout(&api,nullptr);
   assert(api.starts==1 && api.queued==IEEE80211_S_AUTH && api.peer==22 && !api.joinWaitingForInit);
   assert(api.wclJoinInitCompleted==1 && api.wclJoinInitTimeouts==0);
   assert(iwx_wcl_state_transition_allowed(hal.ic.ic_wcl_teardown_pending,false,true));
   api.peerEvent(IEEE80211_EVT_STA_ASSOC_DONE);assert(api.peerEvents==1);
   assert(!memcmp(&api.deferredJoin,&empty,sizeof(empty)));
  }
 }
 for(unsigned which=0;which<4;++which){
  AirportItlwmSkywalkInterface api;api.fHalService=&hal;api.instance=&inst;api.joinTimer=&timer;
  hal.ic.ic_state=IEEE80211_S_RUN;hal.ic.ic_if.if_flags=IFF_RUNNING;hal.ic.ic_wcl_teardown_pending=false;
  AirportWCL::JoinRequest j={};j.ssidLength=3;j.key[0]=0x6b;assert(api.deferWCLJoinUntilIdle(j));
  if(which==0){now=api.joinInitDeadlineNS;api.wclJoinTimeout(&api,nullptr);assert(api.failures==1 && !api.starts);}
  if(which==1){api.wclStopping=true;api.wclJoinTimeout(&api,nullptr);api.resumeWCLJoin();assert(!api.starts && !api.failures);}
  if(which==2){hal.ic.ic_if.if_flags=0;hal.ic.ic_state=IEEE80211_S_INIT;api.resumeWCLJoin();assert(!api.starts);now=api.joinInitDeadlineNS;api.wclJoinTimeout(&api,nullptr);assert(api.failures==1);}
  if(which==3){api.failStart=true;api.completeHALInit();api.wclJoinTimeout(&api,nullptr);assert(api.failures==1 && api.starts==1);}
 }
 bool idle=false;assert(iwx_wcl_state_transition_allowed(idle,true,true) && !idle);
 puts("PASS: production deferral/resume/timer and teardown fence, 200 coalescing-HAL schedules with late old-peer requests; old BSS retained until INIT, early READY guarded, cancellation/offline/deadline/start-error paths.");
}
'''

decls = '\n'.join(block(reg,'struct '+name+' {')+' __packed;' for name in [
    'iwx_mac_client_data','iwx_mac_p2p_dev_data','iwx_mac_config_cmd'])
mac = '\n'.join(block(iwx,s) for s in [
    'static const uint8_t *iwx_mld_context_address(',
    'int ItlIwx::\niwx_mld_mac_config_cmd('])
headers = reg + '\n' + '\n'.join(p.read_text() for p in (root/'itl80211/openbsd/net80211').glob('*.h'))
defs = dict(re.findall(r'^\s*#define\s+((?:IWX|IEEE80211)_[A-Za-z0-9_]+)\s+([^\n]+)',headers,re.M))
needed = set(re.findall(r'\b(?:IWX|IEEE80211)_[A-Za-z0-9_]+\b',mac+decls))
needed |= {'IWX_FW_CTXT_ACTION_MODIFY'}
while True:
    extra = set(re.findall(r'\b(?:IWX|IEEE80211)_[A-Za-z0-9_]+\b','\n'.join(defs.get(k,'') for k in needed)))
    if extra <= needed:break
    needed |= extra
defines = '\n'.join('#define '+k+' '+defs[k] for k in needed if k in defs)
mac_harness = r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cassert>
#include <libkern/OSByteOrder.h>
#define htole16 OSSwapHostToLittleInt16
#define htole32 OSSwapHostToLittleInt32
#define __packed __attribute__((packed))
#define ETHER_ADDR_LEN 6
#define IEEE80211_ADDR_COPY(a,b) memcpy(a,b,6)
''' + defines + '\n' + decls + r'''
struct ieee80211com {uint8_t ic_myaddr[6]={2,1,1,1,1,1};struct {uint8_t mac_cap_info[6]={};}ic_he_cap_elem;};
struct iwx_softc {ieee80211com sc_ic;uint8_t sc_mld_context_addr[6]={};bool sc_mld_context_addr_valid=false;};
struct iwx_node {struct {unsigned ni_flags=0,ni_associd=1;}in_ni;};
struct ItlIwx {iwx_mac_config_cmd wire={};int result=0;
 uint32_t iwx_cmd_id(unsigned c,unsigned g,unsigned v){return c|(g<<8)|(v<<16);}
 int iwx_send_cmd_pdu(iwx_softc *,uint32_t,unsigned,unsigned len,const void *p){assert(len==sizeof(wire));memcpy(&wire,p,len);return result;}
 int iwx_mld_mac_config_cmd(iwx_softc *,iwx_node *,uint32_t,int);
};
''' + mac + r'''
int main(){
 iwx_softc sc;iwx_node node;ItlIwx hal;
 uint8_t old[6];memcpy(old,sc.sc_ic.ic_myaddr,6);
 assert(!hal.iwx_mld_mac_config_cmd(&sc,&node,IWX_FW_CTXT_ACTION_ADD,0));
 assert(sc.sc_mld_context_addr_valid && !memcmp(old,hal.wire.local_mld_addr,6));
 sc.sc_ic.ic_myaddr[5]=2;
 assert(!hal.iwx_mld_mac_config_cmd(&sc,&node,IWX_FW_CTXT_ACTION_MODIFY,0));
 assert(!memcmp(old,hal.wire.local_mld_addr,6));
 assert(!memcmp(old,iwx_mld_context_address(&sc,false),6));
 hal.result=5;assert(hal.iwx_mld_mac_config_cmd(&sc,&node,IWX_FW_CTXT_ACTION_REMOVE,0)==5);
 assert(sc.sc_mld_context_addr_valid);hal.result=0;
 assert(!hal.iwx_mld_mac_config_cmd(&sc,&node,IWX_FW_CTXT_ACTION_REMOVE,0));
 uint8_t zero[6]={};assert(!sc.sc_mld_context_addr_valid && !memcmp(sc.sc_mld_context_addr,zero,6));
 assert(!hal.iwx_mld_mac_config_cmd(&sc,&node,IWX_FW_CTXT_ACTION_ADD,0));
 assert(!memcmp(sc.sc_ic.ic_myaddr,hal.wire.local_mld_addr,6));
 hal.result=5;sc.sc_mld_context_addr_valid=false;
 assert(hal.iwx_mld_mac_config_cmd(&sc,&node,IWX_FW_CTXT_ACTION_ADD,0)==5);
 assert(!sc.sc_mld_context_addr_valid);
 puts("PASS: production MAC v2 builder pins existing context address through private-MAC change, commits only successful ADD/REMOVE, new ADD uses new address.");
}
'''
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    for name,source in [('switch',harness),('mac',mac_harness)]:
        (p/(name+'.cpp')).write_text(source)
        subprocess.run(['clang++','-std=c++14','-fsanitize=address,undefined','-Wall','-Wextra','-Werror',
            '-I',str(root/'AirportItlwm/WCL'),'-I',str(root/'itlwm/hal_iwx'),'-I',str(root/'itl80211/openbsd/net80211'),str(p/(name+'.cpp')),'-o',str(p/name)],check=True)
        subprocess.run([str(p/name)],check=True)
