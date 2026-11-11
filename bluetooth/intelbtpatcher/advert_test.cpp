#include "LECommandProbe.hpp"
#include <cassert>
#include <cstring>
#include <vector>
#include <random>
#include <cstdio>
using namespace be201probe;
static std::vector<uint8_t> cmd(unsigned op,size_t n) {
    std::vector<uint8_t> b(n+3);b[0]=op;b[1]=op>>8;b[2]=n;return b;
}
int main() {
    // Synthetic AD with Handoff type 0x0c and Nearby type 0x10; no real user data.
    const uint8_t ad[]={2,1,6, 10,0xff,0x4c,0,0x0c,2,0x91,0x92,0x10,1,0x93};
    uint64_t mask=0;assert(appleTypeMask(ad,sizeof ad,mask));
    assert(mask==((1ULL<<0x0c)|(1ULL<<0x10)));
    auto a=cmd(0x2008,32);a[3]=sizeof ad;memcpy(a.data()+4,ad,sizeof ad);
    auto before=a;Statistics s={};submitted(s,a.data(),a.size());
    assert(a==before && s.handoffDataCommands==1 && s.advertisingDataTypeMask==mask && !s.advertisingMalformedAD);
    // Payload contents and unused padding must not affect any exported counter.
    auto b=a;b[4+9]^=0x55;b[4+10]^=0x55;b[4+13]^=0x55;
    for(size_t j=4+sizeof ad;j<b.size();j++)b[j]=0xe7;
    Statistics other={};submitted(other,b.data(),b.size());assert(!memcmp(&s,&other,sizeof s));
    auto rsp=a;rsp[0]=9;s={};submitted(s,rsp.data(),rsp.size());
    assert(s.scanResponseCommands==1 && s.scanResponseTypeMask==mask && !s.handoffDataCommands && s.handoffResponseCommands==1);
    auto par=cmd(0x2006,15);par[7]=0;par[8]=1;
    s={};submitted(s,par.data(),par.size());assert(s.advertisingParameters==1 && s.advertisingType==0 && s.advertisingOwnAddressType==1);
    auto altered=par;for(size_t j=10;j<16;j++)altered[j]=0xad;
    other={};submitted(other,altered.data(),altered.size());assert(!memcmp(&s,&other,sizeof s));
    for(unsigned opcode:{0x2006u,0x2008u,0x2009u,0x200au}) {
        uint8_t ev[]={0x0e,4,1,uint8_t(opcode),0x20,0};s={};eventPrefix(s,ev,6,6);
        uint64_t *ok=opcode==0x2006?&s.advertisingParameterCompletions:opcode==0x2008?&s.advertisingDataCompletions:opcode==0x2009?&s.scanResponseCompletions:&s.advertisingEnableCompletions;
        uint64_t *errors=opcode==0x2006?&s.advertisingParameterErrors:opcode==0x2008?&s.advertisingDataErrors:opcode==0x2009?&s.scanResponseErrors:&s.advertisingEnableErrors;
        assert(*ok==1 && !*errors);ev[5]=0x0c;eventPrefix(s,ev,6,6);assert(*ok==2 && *errors==1);
    }
    for(size_t n=0;n<a.size();n++){s={};submitted(s,a.data(),n);assert(!s.advertisingDataCommands);}
    for(unsigned n=0;n<256;n++) {
        auto bad=a;bad[3]=n;s={};submitted(s,bad.data(),bad.size());
        if(n>31)assert(s.malformedCount && !s.advertisingDataCommands);
    }
    auto bad=a;bad[4+3]=31;s={};submitted(s,bad.data(),bad.size());assert(s.advertisingMalformedAD==1 && !s.advertisingDataTypeMask && !s.handoffDataCommands);
    const uint8_t truncated[]={4,0xff,0x4c,0,0x0c};assert(!appleTypeMask(truncated,sizeof truncated,mask));
    const uint8_t oversized[]={5,0xff,0x4c,0,0x0c,255};assert(!appleTypeMask(oversized,sizeof oversized,mask));
    const uint8_t end[]={0,255,255};assert(appleTypeMask(end,sizeof end,mask)&&!mask);
    const uint8_t high[]={5,0xff,0x4c,0,255,0};assert(appleTypeMask(high,sizeof high,mask)&&!mask);
    uint8_t conn[]={0x3e,19,1,0,0,0,0,1};s={};eventPrefix(s,conn,8,21);
    assert(s.centralConnectionSuccesses==1 && !s.peripheralConnectionSuccesses && s.lastSuccessfulRole==0 && s.lastSuccessfulPeerAddressType==1);
    conn[1]=31;conn[2]=0x0a;conn[6]=1;eventPrefix(s,conn,8,33);assert(s.peripheralConnectionSuccesses==1);
    conn[3]=2;eventPrefix(s,conn,8,33);assert(s.peripheralConnectionSuccesses==1 && s.connectionCompleteFailures==1);
    conn[3]=0;eventPrefix(s,conn,6,33);assert(s.connectionRoleUnknown==1);
    std::mt19937 rng(201);
    for(unsigned i=0;i<200000;i++) {
        std::vector<uint8_t> bytes(rng()%40);for(auto &v:bytes)v=rng();auto copy=bytes;
        appleTypeMask(bytes.data(),bytes.size(),mask);s={};submitted(s,bytes.data(),bytes.size());assert(bytes==copy);
    }
    puts("PASS: actual production AD parser/HCI metadata; Handoff and mixed types, payload/address/padding invariance, malformed/truncated lengths, completion status, 200000 random buffers (ASan/UBSan).");
}
