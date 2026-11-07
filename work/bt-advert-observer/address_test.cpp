#include "NativeAddressGuard.hpp"
#include <cassert>
#include <cstring>
#include <random>
#include <vector>
#include <cstdio>
using namespace be201address;
int main() {
 Guard g={};assert(!g.bind(0));assert(g.bind(201));assert(!g.bind(202));assert(!g.preserve(201));
 uint8_t rpa[]={5,0x20,6,0x12,0x34,0x56,1,2,0x43},copy[9];memcpy(copy,rpa,9);
 assert(validRPACommand(rpa,9));assert(!memcmp(copy,rpa,9));
 for(size_t n=0;n<9;n++)assert(!validRPACommand(rpa,n));
 uint64_t ticket=g.invalidate();assert(!g.accepted(ticket,false,true,9));assert(!g.preserve(201));
 assert(!g.accepted(ticket,true,false,9));assert(!g.accepted(ticket,true,true,8));
 assert(g.accepted(ticket,true,true,9));assert(g.preserve(201));assert(!g.preserve(202));
 uint64_t old=g.invalidate();uint64_t newer=g.invalidate();assert(!g.accepted(old,true,true,9));assert(!g.preserve(201));assert(g.accepted(newer,true,true,9));
 ticket=g.invalidate();g.invalidate();assert(!g.accepted(ticket,true,true,9));assert(!g.preserve(201));
 rpa[6]=rpa[7]=0;rpa[8]=0x40;assert(!validRPACommand(rpa,9));
 rpa[6]=rpa[7]=255;rpa[8]=0x7f;assert(!validRPACommand(rpa,9));
 for(unsigned kind: {0,2,3}){rpa[8]=kind<<6;rpa[6]=1;assert(!validRPACommand(rpa,9));}
 std::mt19937 rng(201);for(unsigned i=0;i<100000;i++){std::vector<uint8_t>b(rng()%260);for(auto&v:b)v=rng();auto before=b;(void)validRPACommand(b.data(),b.size());assert(b==before);}
 puts("PASS: device scope, native RPA validation, synchronous USB/length/error guard, reset/late-return races, no input mutation, 100000 randomized buffers (ASan/UBSan).");
}
