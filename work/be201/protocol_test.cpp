#include "src/BE201Protocol.h"
#include <vector>
#include <fstream>
#include <iterator>
#include <cassert>
#include <cstdio>
static std::vector<uint8_t> read(const char *name) {
    std::ifstream f(name,std::ios::binary);assert(f.good());return {std::istreambuf_iterator<char>(f),{}};
}
int main() {
    uint8_t dsbr[5]={0,0xf1,0,0,0},params[2]={};
    assert(beDSBRParams(dsbr,5,params) && params[0]==1 && params[1]==15);
    dsbr[1]=0xb1;assert(beDSBRParams(dsbr,5,params) && params[1]==11);
    dsbr[1]=0;assert(beDSBRParams(dsbr,5,params) && params[0]==0 && params[1]==0);
    dsbr[1]=0xff;assert(!beDSBRParams(dsbr,5,params) && params[0]==0 && params[1]==0);
    assert(!beDSBRParams(dsbr,4,params));
    auto boot=read("work/be201/bootloader-event.bin"),op=read("work/be201/operational-event.bin"),fw=read("work/be201/fw/ibt-0093-0291.sfi");
    assert(beTLVValid(boot.data()+5,boot.size()-5));assert(beTLVValid(op.data()+5,op.size()-5));
    uint32_t address=0;assert(beFirmwareValid(fw.data(),fw.size(),&address));assert(address==0x00100800);
    assert(!beTLVValid(nullptr,0));assert(!beFirmwareValid(nullptr,0,&address));
    for(size_t n=0;n<boot.size()-5;n++)(void)beTLVValid(boot.data()+5,n);
    for(size_t n=0;n<op.size()-5;n++)(void)beTLVValid(op.data()+5,n);
    auto bad=boot;bad[5]=1;assert(!beTLVValid(bad.data()+5,bad.size()-5));
    bad=boot;bad[7]=3;assert(!beTLVValid(bad.data()+5,bad.size()-5));
    bad=boot;bad.insert(bad.end(),boot.begin()+6,boot.begin()+12);assert(!beTLVValid(bad.data()+5,bad.size()-5));
    bad=boot;bad[7]=255;assert(!beTLVValid(bad.data()+5,bad.size()-5));
    auto damaged=fw;damaged[8]^=1;assert(!beFirmwareValid(damaged.data(),damaged.size(),&address));
    damaged=fw;damaged[644]=0;assert(!beFirmwareValid(damaged.data(),damaged.size(),&address));
    assert(!beFirmwareValid(fw.data(),fw.size()-1,&address));
    damaged=fw;damaged[985639]=255;assert(!beFirmwareValid(damaged.data(),damaged.size(),&address));
    // Fixed-seed malformed USB TLVs: exercise parser bounds under ASan/UBSan.
    uint32_t seed=0xBE201;std::vector<uint8_t> random(512);
    for(unsigned i=0;i<100000;i++) {
        for(auto &v:random){seed=seed*1664525+1013904223;v=(uint8_t)(seed>>24);}
        random[0]=0;(void)beTLVValid(random.data(),seed%random.size());
        auto mutated=boot;mutated[seed%mutated.size()]=(uint8_t)seed;
        (void)beTLVValid(mutated.data()+5,mutated.size()-5);
    }
    puts("PASS: real boot/operational TLVs, signed SFI boot address, malformed lengths, duplicate TLVs, truncation, 100000 deterministic fuzz cases (ASan/UBSan).");
}
