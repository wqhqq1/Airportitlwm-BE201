#include "LECommandProbe.hpp"
#include <cassert>
#include <cstring>
#include <vector>
#include <random>
#include <cstdio>
using namespace be201probe;
static std::vector<uint8_t> command(uint16_t opcode,size_t length){
 std::vector<uint8_t>b(3+length);b[0]=opcode;b[1]=opcode>>8;b[2]=length;return b;
}
int main(){
 Statistics s={};auto random=command(0x2005,6);random[8]=0x40;
 auto copy=random;submitted(s,random.data(),random.size());assert(random==copy);
 injectedRandomAddress(s);assert(s.nativeBeforePlaceholder==1 && s.nativeRandomSequence<s.placeholderSequence);
 auto connect=command(0x2043,42);connect[3]=1;connect[4]=1;connect[5]=0;connect[12]=3;
 submitted(s,connect.data(),connect.size());assert(s.connectCount==1 && s.connectOpcode==0x2043 && s.connectOwnAddressType==1 && s.connectPeerAddressType==0 && s.connectPHYMask==3 && s.nativeBeforeConnect==1);
 auto reset=command(0x0c03,0);submitted(s,reset.data(),reset.size());submitted(s,connect.data(),connect.size());assert(s.nativeBeforeConnect==0);
 injectedRandomAddress(s);assert(s.nativeBeforePlaceholder==0);
 auto legacy=command(0x200d,25);legacy[3+4]=1;legacy[3+5]=2;legacy[3+12]=3;submitted(s,legacy.data(),legacy.size());assert(s.connectOwnAddressType==3 && s.connectPeerAddressType==2 && s.connectFilterPolicy==1 && s.connectPHYMask==1);
 auto irk=command(0x2027,39),other=irk;
 for(size_t i=4;i<other.size();++i)other[i]=0x9d;
 Statistics a={},b={};submitted(a,irk.data(),irk.size());submitted(b,other.data(),other.size());assert(!memcmp(&a,&b,sizeof a)); // No address/key retained.
 other=random;for(size_t i=3;i<8;++i)other[i]=0xd5;other[8]=0x7f;
 a={};b={};submitted(a,random.data(),random.size());submitted(b,other.data(),other.size());assert(!memcmp(&a,&b,sizeof a));
 // Invalid extended-PHY lengths must not count as submitted connections.
 for(size_t n=0;n<43;++n){a={};submitted(a,connect.data(),n);if(n<43)assert(a.connectCount==0);}
 auto invalid=connect;invalid[12]=0x80;a={};submitted(a,invalid.data(),invalid.size());assert(a.connectCount==0 && a.malformedCount==1);
 std::mt19937 rng(201);unsigned cases=100000;
 for(unsigned i=0;i<cases;++i){std::vector<uint8_t>bytes(rng()%260);for(auto&x:bytes)x=rng();auto before=bytes;Statistics st={};submitted(st,bytes.data(),bytes.size());assert(bytes==before);}
 puts("PASS: command ABI fields, reset ordering, no address/key retention, immutable input, truncated/invalid PHY packets and 100000 randomized buffers (ASan/UBSan).");
}
