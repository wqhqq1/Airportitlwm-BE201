#include "BE201Patches.hpp"
#include <cassert>
#include <cstdio>
#include <vector>
#include <fstream>
#include <iterator>
#include <random>
int main() {
    std::ifstream f("/usr/sbin/bluetoothd",std::ios::binary);
    std::vector<unsigned char> b((std::istreambuf_iterator<char>(f)),{}), before=b;
    assert(b.size()>0x8c0200); unsigned clocks=0,names=0;
    // The live host only executes the x86_64 slice. Simulate code-signing pages.
    for(size_t i=0x4000;i+4096<=0xa8ca00;i+=4096) {
        clocks+=be201Apply(b.data()+i,4096,kBE201ClockOriginal,kBE201ClockPatched);
        names+=be201Apply(b.data()+i,4096,kBE201NameOriginal,kBE201NamePatched);
    }
    assert(clocks==1 && names==1);
    assert(!memcmp(b.data()+0x22db3d,before.data()+0x22db3d,72));
    assert(!strcmp((char*)b.data()+0x8c015a,"Intel BE201"));
    assert(!memcmp(b.data()+0x8c016d,before.data()+0x8c016d,200));
    for(size_t i=0;i<b.size();++i)
        if(b[i]!=before[i])assert(i==0x3ede52 || i==0x3ede54 || (i>=0x8c015a && i<0x8c016d));
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
        assert(!be201Apply(guard,len,kBE201ClockOriginal,kBE201ClockPatched));
    }
    printf("PASS: one clock gate, one model string; unrelated gate and vendor unchanged; ambiguous/short/null/random buffers refused (100000 cases).\n");
}
