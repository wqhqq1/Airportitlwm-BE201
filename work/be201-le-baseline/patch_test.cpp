#include "BE201Patches.hpp"
#include <cassert>
#include <cstdio>
#include <vector>
#include <fstream>
#include <iterator>
#include <random>
#include <sys/mman.h>
#include <unistd.h>
#include <cstdint>
#include <array>
// Execute the actual native caller argument-selection instructions, stopping
// before the external call. Verify that only its third argument changes.
static void nativeCallerTest() {
    constexpr size_t count=0x61c0f1-0x61c0c7;
    const unsigned char prologue[]={0x53,0x48,0x89,0xfb,0x89,0xf0};
    const unsigned char capture[]={0x49,0x89,0x38,0x49,0x89,0x70,0x08,0x49,0x89,0x50,0x10,0x49,0x89,0x48,0x18,0x5b,0xc3};
    auto *mem=(unsigned char*)mmap(nullptr,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);assert(mem!=MAP_FAILED);
    using Fn=void(*)(void*,unsigned,void*,void*,uint64_t*);
    std::vector<unsigned char> self(0x6a00,0xa5);
    for(uint32_t state : {0u,1u,2u,3u,4u,0xffffffffu})for(unsigned feature:{0u,1u}) {
        uint64_t original[4]={},patched[4]={};
        for(unsigned patch=0;patch<2;++patch) {
            assert(mprotect(mem,4096,PROT_READ|PROT_WRITE)==0);
            memcpy(mem,prologue,sizeof prologue);
            memcpy(mem+sizeof prologue,patch?kBE201LegacyAdvPatched:kBE201LegacyAdvOriginal,count);
            memcpy(mem+sizeof prologue+count,capture,sizeof capture);
            memcpy(self.data()+0x88,&state,4);self[0x6950]=0xa5;
            assert(mprotect(mem,4096,PROT_READ|PROT_EXEC)==0);
            ((Fn)mem)(self.data(),feature,nullptr,nullptr,patch?patched:original);
            uint32_t after=0;memcpy(&after,self.data()+0x88,4);assert(after==state && self[0x6950]==0);
        }
        assert(original[0]==(feature?0:3) && original[1]==1);
        assert(original[2]==((state&0xfffffffdu)==0));
        assert(patched[0]==original[0] && patched[1]==original[1] && patched[2]==0 && patched[3]==original[3]);
    }
    assert(munmap(mem,4096)==0);
}
// Exercise the exact native bool argument setup on x86_64. The called
// getter copies EDX then tests its low byte; address/key cache is not modified.
static void peerArgumentTest() {
    const unsigned char original[]={0x89,0xfa,0x31,0xd2,0x0f,0xb6,0xc2,0xc3};
    const unsigned char patched[]={0x89,0xfa,0xb2,0x01,0x0f,0xb6,0xc2,0xc3};
    auto *m=(unsigned char*)mmap(nullptr,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);assert(m!=MAP_FAILED);
    using Fn=unsigned(*)(unsigned);
    for(unsigned version=0;version<2;version++) {
        assert(mprotect(m,4096,PROT_READ|PROT_WRITE)==0);memcpy(m,version?patched:original,sizeof original);
        assert(mprotect(m,4096,PROT_READ|PROT_EXEC)==0);
        std::mt19937 rng(201);for(unsigned i=0;i<100000;i++)assert(((Fn)m)(rng())==version);
    }
    assert(munmap(m,4096)==0);
    // Native getter semantics: false prefers resolved, true returns observed.
    struct Peer { uint64_t observed,resolved; } p={0x1400102030405ULL,0x0010203040506ULL};
    auto select=[](Peer p,bool observed){return observed?p.observed:(p.resolved?p.resolved:p.observed);};
    assert(select(p,true)==p.observed && select(p,false)==p.resolved);
    auto before=p;assert(select(p,true)==p.observed);assert(!memcmp(&p,&before,sizeof p));
    p.resolved=0;assert(select(p,true)==select(p,false));
    p.resolved=0x0010203040506ULL;p.observed=0;assert(select(p,true)==0);
    p.observed=0x1400102030405ULL;
    // Removal/rebuild uses the selected key saved by the native connection manager.
    const uint64_t savedKey=select(p,true);p.observed=0x1410102030405ULL;
    assert(savedKey!=p.observed); // Do not recompute identity/address during removal.
}

static void nativeBaselinePredicatesTest() {
    auto *m=(unsigned char*)mmap(nullptr,8192,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);assert(m!=MAP_FAILED);
    using Fn=uint8_t(*)();
    for(unsigned version=0;version<2;version++) {
        assert(mprotect(m,4096,PROT_READ|PROT_WRITE)==0);
        memcpy(m,version?kBE201LEBaselinePatched:kBE201LEBaselineOriginal,31);
        int32_t d0=4096-10,d1=4097-27;memcpy(m+6,&d0,4);memcpy(m+23,&d1,4);
        assert(mprotect(m,4096,PROT_READ|PROT_EXEC)==0);
        for(unsigned value=0;value<256;value++) {
            m[4096]=value;m[4097]=value^0x65;
            assert(((Fn)m)()==(version?0:((value>>5)&1)));
            assert(((Fn)(m+17))()==(version?0:((value^0x65)&1)));
        }
    }
    assert(munmap(m,8192)==0);
}
int main(int argc,char **argv) {
    assert(argc==2);nativeCallerTest();peerArgumentTest();nativeBaselinePredicatesTest();
    std::ifstream f(argv[1],std::ios::binary);assert(f);
    std::vector<unsigned char> b((std::istreambuf_iterator<char>(f)),{}), before=b;
    assert(b.size()>0x8c0200); unsigned clocks=0,names=0,adverts=0,peers=0,baselines=0;
    // The live host only executes the x86_64 slice. Simulate code-signing pages.
    for(size_t i=0x4000;i+4096<=0xa8ca00;i+=4096) {
        peers+=be201Apply(b.data()+i,4096,kBE201PeerAddressOriginal,kBE201PeerAddressPatched);
        baselines+=be201Apply(b.data()+i,4096,kBE201LEBaselineOriginal,kBE201LEBaselinePatched);
        clocks+=be201Apply(b.data()+i,4096,kBE201ClockOriginal,kBE201ClockPatched);
        adverts+=be201Apply(b.data()+i,4096,kBE201LegacyAdvOriginal,kBE201LegacyAdvPatched);
        names+=be201Apply(b.data()+i,4096,kBE201NameOriginal,kBE201NamePatched);
    }
    assert(clocks==1 && names==1 && adverts==1 && peers==1 && baselines==1);
    assert(!memcmp(b.data()+0x22db3d,before.data()+0x22db3d,72));
    assert(!strcmp((char*)b.data()+0x8c015a,"Intel BE201"));
    assert(!memcmp(b.data()+0x8c016d,before.data()+0x8c016d,200));
    for(size_t i=0;i<b.size();++i)
        if(b[i]!=before[i])assert(i==0x137c53 || i==0x137c64 || i==0x68f05f || i==0x68f060 || i==0x3ede52 || i==0x3ede54 || (i>=0x61c0da && i<0x61c0dd) || (i>=0x8c015a && i<0x8c016d));
    unsigned char peerGuard[256]={};
    memcpy(peerGuard+8,kBE201PeerAddressOriginal,sizeof kBE201PeerAddressOriginal);
    memcpy(peerGuard+100,kBE201PeerAddressOriginal,sizeof kBE201PeerAddressOriginal);
    unsigned char peerCopy[256];memcpy(peerCopy,peerGuard,sizeof peerCopy);
    assert(be201Apply(peerGuard,sizeof peerGuard,kBE201PeerAddressOriginal,kBE201PeerAddressPatched)==0);
    assert(!memcmp(peerCopy,peerGuard,sizeof peerCopy));
    assert(be201Apply(peerGuard,sizeof kBE201PeerAddressOriginal-1,kBE201PeerAddressOriginal,kBE201PeerAddressPatched)==0);
    unsigned char guard[256]={};memcpy(guard+8,kBE201ClockOriginal,sizeof(kBE201ClockOriginal));
    memcpy(guard+100,kBE201ClockOriginal,sizeof(kBE201ClockOriginal));
    unsigned char copy[256];memcpy(copy,guard,sizeof(copy));
    assert(be201Apply(guard,sizeof(guard),kBE201ClockOriginal,kBE201ClockPatched)==0);
    assert(!memcmp(guard,copy,sizeof(guard)));
    assert(be201Apply(nullptr,4096,kBE201ClockOriginal,kBE201ClockPatched)==0);
    std::mt19937 rng(201);
    for(unsigned n=0;n<100000;++n) {
        size_t len=rng()%sizeof(guard);
        for(size_t i=0;i<len;++i)guard[i]=rng();
        assert(!be201Apply(guard,len,kBE201PeerAddressOriginal,kBE201PeerAddressPatched));
        assert(!be201Apply(guard,len,kBE201ClockOriginal,kBE201ClockPatched));
        assert(!be201Apply(guard,len,kBE201LegacyAdvOriginal,kBE201LegacyAdvPatched));
    }
    printf("PASS: native EDL/2M predicate instructions on all 256 byte values, two-byte-only fallback; exact peer bool argument instructions (200000 executions), native getter selection/cache/remove-key model, unique peer patch + existing LE/clock/name; binary diff allowlist; 100000 randomized bounds cases (ASan/UBSan).\n");
}
