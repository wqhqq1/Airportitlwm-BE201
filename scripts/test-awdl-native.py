"""Actual native binding staging/worker: read-only RF path; ASan/UBSan and failed-gate cases."""
from pathlib import Path
import subprocess,tempfile
R=Path(__file__).resolve().parents[1];s=(R/'itlwm/hal_iwx/ItlIwx.cpp').read_text()
a=s.index('IOReturn ItlIwx::requestAwdlMonitor(');b=s.index('#endif',a);methods=s[a:b]
pre=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <sys/mman.h>
#include <unistd.h>
#include "iwx_awdl_native.h"
using IOReturn=int;constexpr int kIOReturnSuccess=0,kIOReturnNotPermitted=-90,kIOReturnNotReady=-91,kIOReturnBadArgument=-1,kIOReturnBusy=-2;
struct OSObject{};constexpr unsigned IEEE80211_S_RUN=4,IWX_FLAG_STA_ACTIVE=1,IWX_FLAG_SHUTDOWN=2,IWX_FLAG_HW_ERR=4;
struct Node{bool ni_port_valid=true;};struct iwx_node{Node in_ni;};
struct IC{Node *ic_bss=nullptr;bool ic_wcl_teardown_pending=false;unsigned ic_state=4;};
struct PCI{std::map<std::string,unsigned> n;void setProperty(const char*k,unsigned v,unsigned){n[k]=v;}void setProperty(const char*k,bool v){n[k]=v;}void setProperty(const char*,void*,unsigned){}};
struct iwx_softc{IC sc_ic;unsigned ns_nstate=4,sc_flags=1;bool sc_awdl_native_requested=false; iw 
};
'''.replace(' iw \n',' iwx_awdl_probe sc_awdl_probe={};PCI *sc_pcitag=nullptr;int awdl_native_task=0;\n')
pre+=r'''
struct Loop{bool gated=true;bool inGate(){return gated;}};
struct Gate{Loop *loop;unsigned calls=0;OSObject unrelatedOwner;int runAction(int(*fn)(OSObject*,void*,void*,void*,void*),void*a,void*b=nullptr){++calls;loop->gated=true;return fn(&unrelatedOwner,a,b,nullptr,nullptr);}};
constexpr int systq=1;
class ItlIwx{public:iwx_softc com;Loop loop;Gate gate{&loop};unsigned adds=0,queued=0;
 Loop *getMainWorkLoop(){return &loop;}Gate *getMainCommandGate(){return &gate;}
 void iwx_add_task(iwx_softc*,int,int*){++queued;}
 void iwx_awdl_ctx_add(iwx_softc*,iwx_node*){++adds;}
 IOReturn requestAwdlMonitor(const uint8_t*);IOReturn setAwdlNativeTemplate(bool,const uint8_t*,size_t);IOReturn enableAwdlNativeTx();static void iwx_awdl_native_task(void*);
};
#define container_of(p,T,m) ((T*)((char*)(p)-offsetof(T,m)))
'''
main=r'''
int main(){
 unsigned cases=0;uint8_t address[6]={2,3,4,5,6,7};
 for(unsigned bits=0;bits<512;++bits){iwx_awdl_probe p={};bool requested=false;p.ctx.mode=(bits&1)?2:0;p.ctx.stage=(bits&2)?3:0;p.tx.mode=(bits&4)?1:0;
  auto before=p;bool conflict=bits&7;int r=iwx_awdl_native_request(&p,&requested,address);
  if(conflict)assert(r==-2&&!requested&&!memcmp(&before,&p,sizeof(p)));else{assert(!r&&requested&&p.ctx.mode==6&&p.mode==3&&p.assoc_rx==1&&!p.tx.mode&&!memcmp(p.tx.self,address,6));auto same=p;assert(iwx_awdl_native_request(&p,&requested,address)==1&&!memcmp(&same,&p,sizeof(p)));auto wrong=address[2];address[2]^=1;assert(iwx_awdl_native_request(&p,&requested,address)==-2&&!memcmp(&same,&p,sizeof(p)));address[2]=wrong;}++cases;
 }
 for(unsigned bad=0;bad<3;++bad){iwx_awdl_probe p={};bool requested=false;uint8_t zero[6]={};uint8_t multi[6]={1,2,3,4,5,6};assert(iwx_awdl_native_request(&p,&requested,bad==0?nullptr:bad==1?zero:multi)==-1&&!requested);}
 // Exactly six readable address bytes before an unreadable page.
 auto pagesize=static_cast<size_t>(getpagesize());auto mem=static_cast<uint8_t*>(mmap(nullptr,pagesize*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0));assert(mem!=MAP_FAILED);assert(!mprotect(mem+pagesize,pagesize,PROT_NONE));memcpy(mem+pagesize-6,address,6);iwx_awdl_probe p={};bool requested=false;assert(!iwx_awdl_native_request(&p,&requested,mem+pagesize-6));munmap(mem,pagesize*2);
 for(unsigned test=0;test<16;++test){ItlIwx h;PCI pci;iwx_node node;h.com.sc_pcitag=&pci;h.com.sc_ic.ic_bss=&node.in_ni;h.loop.gated=false;
  assert(!h.requestAwdlMonitor(address)&&h.gate.calls==1&&h.queued==1&&h.adds==0); // Wrong gate owner must not be cast to HAL.
  switch(test){case 0:h.com.sc_awdl_native_requested=false;break;case 1:h.com.sc_ic.ic_bss=nullptr;break;case 2:node.in_ni.ni_port_valid=false;break;case 3:h.com.sc_ic.ic_wcl_teardown_pending=true;break;case 4:h.com.sc_ic.ic_state=0;break;case 5:h.com.ns_nstate=0;break;case 6:h.com.sc_flags=0;break;case 7:h.com.sc_flags|=IWX_FLAG_SHUTDOWN;break;case 8:h.com.sc_flags|=IWX_FLAG_HW_ERR;break;default:break;}
  h.loop.gated=test&1;ItlIwx::iwx_awdl_native_task(&h.com);assert(h.adds==(test>=9?1u:0u));++cases;
 }
 printf("PASS: %u actual native binding/worker cases; no AP mutation on conflicts, six-byte boundary, no TX enable, deferred firmware work, unrelated gate-owner safety\n",cases);
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);c=p/'t.cpp';c.write_text('#include <cstddef>\n'+pre+'\n'+methods+main)
 subprocess.run(['clang++','-std=c++17','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(R/'itlwm/hal_iwx'),str(c),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
assert 'iwx_del_task(sc, systq, &sc->awdl_native_task)' in s and 'task_set(&sc->awdl_native_task, iwx_awdl_native_task' in s
