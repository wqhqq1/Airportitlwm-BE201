#include "PeerReport.hpp"
#include <cassert>
#include <vector>
#include <cstring>
#include <random>
#include <cstdio>
using namespace be201peer;
static std::vector<uint8_t> report(unsigned type=0,unsigned addressType=1,bool test=true){
    std::vector<uint8_t> p={0x3e,0,2,1,uint8_t(type),uint8_t(addressType),1,2,3,4,5,6,18,17,7,
        3,0,0,0,0,0,0x12,0x8e,1,0x41,0x20,0xbe,0xd0,0xa1,0x8e,0x4d,0xc0};
    if(!test)p[15]=4;p[1]=p.size()-2;return p;
}
int main(){
    Observer o={};Stats s={};auto p=report();auto before=p;
    o.event(s,p.data(),p.size());assert(p==before && s.testReports==1 && s.testConnectable==1 && s.testAddressType==1 && s.testListMatch==0);
    uint8_t add[]={0x11,0x20,7,1,1,2,3,4,5,6};o.command(s,add,sizeof add);assert(s.testListMatch==1 && s.testListEntries==1);
    // Same address with public instead of random is not a valid exact match.
    uint8_t clear[]={0x10,0x20,0};o.command(s,clear,sizeof clear);add[3]=0;o.command(s,add,sizeof add);assert(s.testListMatch==0 && s.testListTypeMask==1);
    add[3]=1;o.command(s,add,sizeof add);assert(s.testListMatch==1 && s.testListEntries==2);
    add[0]=0x12;o.command(s,add,sizeof add);assert(s.testListMatch==0 && s.testListEntries==1);
    for(unsigned t=0;t<5;t++){p=report(t);o.event(s,p.data(),p.size());assert(s.testConnectable==(t<2?1:t<4?0:2));}
    p=report(0,1,false);auto n=s.testReports;o.event(s,p.data(),p.size());assert(s.testReports==n);
    p=report();for(size_t len=0;len<p.size();len++){Observer x={};Stats st={};x.event(st,p.data(),len);assert(st.testReports==0);}
    p[3]=2;o.event(s,p.data(),p.size());assert(s.testReports==n); // truncated second report must not consume first
    p=report();p[0]=0x0e;o.event(s,p.data(),p.size());assert(s.testReports==n);
    // Lock contention is nonblocking and cannot publish a made-up match.
    __atomic_store_n(&o.lock,1,__ATOMIC_RELEASE);p=report();o.event(s,p.data(),p.size());assert(s.contention==1);__atomic_store_n(&o.lock,0,__ATOMIC_RELEASE);
    uint8_t reset[]={3,0x0c,0};o.command(s,reset,sizeof reset);assert(s.comparisonKnown==0 && s.testListEntries==0);
    // No address is included in Stats; changing both compared raw addresses
    // changes neither the exported result nor other metadata.
    Observer a={},b={};Stats as={},bs={};p=report();auto q=p;
    uint8_t ca[]={0x11,0x20,7,1,1,2,3,4,5,6},cb[]={0x11,0x20,7,1,9,8,7,6,5,4};
    for(unsigned i=0;i<6;i++)q[6+i]=cb[4+i];a.command(as,ca,sizeof ca);b.command(bs,cb,sizeof cb);a.event(as,p.data(),p.size());b.event(bs,q.data(),q.size());assert(!memcmp(&as,&bs,sizeof as));
    std::mt19937 rng(201);for(unsigned i=0;i<100000;i++){
        std::vector<uint8_t> v(rng()%280);for(auto &z:v)z=rng();auto copy=v;Observer x={};Stats st={};x.event(st,v.data(),v.size());x.command(st,v.data(),v.size());assert(v==copy);
    }
    puts("PASS: exact public 128-bit test service, connectable/nonconnectable/scan-response states, address+type comparison, add/remove/reset, truncated multi-reports, contention, invariant numeric export, 100000 random packets (ASan/UBSan).");
}
