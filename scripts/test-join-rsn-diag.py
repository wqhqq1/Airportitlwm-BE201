"""Verify the actual bounded ring/publisher and unchanged security decisions."""
from pathlib import Path
import subprocess,tempfile,re,json,hashlib,sys,struct
root=Path(__file__).resolve().parents[1];net=root/'itl80211/openbsd/net80211'
fixtures=root/'tests/fixtures'
for name,digest in json.loads((fixtures/'rsn-1.1.3-manifest.json').read_text()).items():
    p=fixtures/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
    current=(net/name.removeprefix('rsn-1.1.3-')).read_text()
    # Every non-diagnostic statement, including every validation/security
    # branch, original call and return remains byte-identical to 1.1.3.
    stripped=re.sub(r'^[ \t]*WCL_RSN_NOTE\([^\n]+\);\n','',current,flags=re.M)
    assert stripped==p.read_text(),name
s=(root/'AirportItlwm/WCL/WCL.cpp').read_text();sig='void AirportItlwmSkywalkInterface::publishWCLJoinDiagnostic('
a=s.index(sig);b=s.index('{',a)+1;depth=1
while depth:depth+=(s[b]=='{')-(s[b]=='}');b+=1
method=s[a:b]
source=r'''
#include <cassert>
#include <cstring>
#include <cstdio>
#include <map>
#include <string>
#include <vector>
#include "ieee80211_wcl_rsn_diag.h"
using IOReturn=int;
struct Node {unsigned ni_flags=0,ni_rsnakms=0,ni_rsncipher=0,ni_rsnprotos=0;unsigned *ni_chan=nullptr;};
struct ieee80211com {wcl_rsn_trace ic_wcl_rsn_trace={};Node *ic_bss=nullptr;unsigned ic_state=0;
 struct {unsigned is_rx_eapol_key=0,is_rx_eapol_badmic=0,is_rx_eapol_replay=0,is_rx_deauth=0;}ic_stats;
 unsigned ic_wcl_diag_key_cipher=0,ic_wcl_diag_rsn_length=0;};
unsigned ieee80211_chan2ieee(ieee80211com *,unsigned *p){return *p;}
struct PCI {std::map<std::string,std::vector<unsigned char>> props;void setProperty(const char *k,const void *p,unsigned n){auto a=static_cast<const unsigned char *>(p);props[k]=std::vector<unsigned char>(a,a+n);}};
struct Instance{PCI *pciNub;};struct HAL {ieee80211com ic;ieee80211com *get80211Controller(){return &ic;}};
struct AirportItlwmSkywalkInterface {
 HAL *fHalService;Instance *instance;bool wclJoinFirstFailurePublished=false;
 unsigned wclJoinRequests=1,wclJoinStarts=1;bool assocNotified=true,firstBeaconNotified=false,portAuthorized=false,joinDeferred=false;
 void publishWCLJoinDiagnostic(uint16_t,uint16_t,IOReturn);
};
''' + method + r'''
int main(int argc,char **argv){
 assert(argc==2);
 wcl_rsn_trace t={};auto zero=t;
 for(unsigned i=0;i<1000;++i)wcl_rsn_note(&t,1,i);
 assert(!memcmp(&t,&zero,sizeof(t)));
 t.enabled=1;
 for(unsigned i=0;i<100000;++i){wcl_rsn_note(&t,1,i);assert(t.next==(i+1)%32 && t.count==i+1);}
 for(unsigned i=0;i<32;++i)assert(t.events[(t.next+i)%32].value==100000-32+i);
 t.count=UINT32_MAX;unsigned old=t.next;wcl_rsn_note(&t,1,8);assert(t.count==UINT32_MAX&&t.next==(old+1)%32);
 HAL hal;PCI pci;Instance inst{&pci};AirportItlwmSkywalkInterface api;api.fHalService=&hal;api.instance=&inst;
 api.publishWCLJoinDiagnostic(1,3,-1);assert(pci.props.empty());
 auto &ic=hal.ic;ic.ic_wcl_rsn_trace.enabled=1;ic.ic_wcl_diag_key_cipher=7;ic.ic_wcl_diag_rsn_length=22;
 for(unsigned code: {1u,2u,3u,19u,17u,18u})wcl_rsn_note(&ic.ic_wcl_rsn_trace,code,code==17?3:0);
 api.publishWCLJoinDiagnostic(1,3,-1);
 auto first=pci.props["ItlwmWclJoinFirstFailure"];assert(first.size()==360);
 assert(first==pci.props["ItlwmWclJoinLastFailure"] && api.wclJoinFirstFailurePublished);
 ++api.wclJoinRequests;api.publishWCLJoinDiagnostic(1,4,-2);
 assert(first==pci.props["ItlwmWclJoinFirstFailure"] && first!=pci.props["ItlwmWclJoinLastFailure"]);
 api.publishWCLJoinDiagnostic(0,0,0);assert(pci.props.count("ItlwmWclJoinLastSuccess"));
 api.joinDeferred=true;api.publishWCLJoinDiagnostic(1,1004,60);
 wcl_join_snapshot out;memcpy(&out,pci.props["ItlwmWclJoinLastFailure"].data(),sizeof(out));
 assert(out.deferred && out.rsn.enabled && !out.rsn.count && !out.key_cipher && !out.rsn_length);
 FILE *f=fopen(argv[1],"wb");assert(f);assert(fwrite(first.data(),1,first.size(),f)==first.size());fclose(f);
 puts("PASS: disabled trace is inert; 100000 ring writes/wrap/saturation; actual publisher first failure freeze, last failure/success and deferred-peer isolation (ASan/UBSan).");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.cpp').write_text(source)
 subprocess.run(['clang++','-std=c++14','-fsanitize=address,undefined','-Wall','-Wextra','-Werror','-I',str(net),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test'),str(p/'sample.bin')],check=True)
 from join_trace import decode_join_trace
 blob=(p/'sample.bin').read_bytes();decoded=decode_join_trace(blob)
 assert decoded['reason']==3 and decoded['events'][-2]['event']=='remote_deauth_reason'
 for n in range(721):
  if n==360:continue
  try:decode_join_trace(bytes(n))
  except ValueError:pass
  else:raise AssertionError(n)
 for pos,val in [(0,0),(1,2),(9,2),(22,2),(23,0),(24,33),(25,32),(26,0)]:
  a=list(struct.unpack('<90I',blob));a[pos]=val
  try:decode_join_trace(struct.pack('<90I',*a))
  except ValueError:pass
  else:raise AssertionError((pos,val))
 print('PASS: production security branches/calls unchanged after scalar-note removal; strict 360-byte decoder rejects malformed ABI, length, booleans and ring entries.')
