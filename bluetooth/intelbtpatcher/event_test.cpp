#include "LECommandProbe.hpp"
#include <cassert>
#include <cstring>
#include <vector>
#include <random>
#include <cstdio>
using namespace be201probe;
int main(){
 Statistics s={};uint8_t ok[]={0x0e,4,1,5,0x20,0};eventPrefix(s,ok,6,6);assert(s.randomAddressHCICompletions==1&&s.randomAddressHCIErrors==0);
 ok[5]=0x0c;eventPrefix(s,ok,6,6);assert(s.randomAddressHCIErrors==1);
 uint8_t status[]={0x0f,4,0,1,0x0d,0x20};eventPrefix(s,status,6,6);assert(s.connectCommandStatuses==1&&s.connectCommandLastStatus==0);
 status[2]=0x0c;eventPrefix(s,status,6,6);assert(s.connectCommandLastStatus==0x0c);
 uint8_t conn[]={0x3e,19,1,0,0,0};eventPrefix(s,conn,6,21);assert(s.connectionCompleteSuccesses==1);
 conn[1]=31;conn[2]=0x0a;conn[3]=0x3e;eventPrefix(s,conn,6,33);assert(s.connectionCompleteFailures==1&&s.connectionCompleteLastStatus==0x3e);
 Statistics a={},b={};uint8_t copy[6];memcpy(copy,conn,6);conn[4]=conn[5]=0xaa;eventPrefix(a,copy,6,33);eventPrefix(b,conn,6,33);assert(!memcmp(&a,&b,sizeof a));
 for(unsigned n=0;n<6;n++){a={};eventPrefix(a,ok,n,6);assert(!a.randomAddressHCICompletions);}
 a={};eventPrefix(a,conn,6,32);assert(a.eventMalformed==1&&!a.connectionCompleteCount);
 uint8_t list[]={0x11,0x20,7,1,1,2,3,4,5,6};a={};submitted(a,list,sizeof list);assert(a.acceptListAdds==1&&a.acceptListLastAddressType==1);
 for(unsigned i=4;i<10;i++)list[i]=0xfe;b={};submitted(b,list,sizeof list);assert(!memcmp(&a,&b,sizeof a));
 std::mt19937 rng(201);for(unsigned i=0;i<100000;i++){std::vector<uint8_t>p(rng()%7);for(auto&v:p)v=rng();auto before=p;Statistics st={};eventPrefix(st,p.data(),p.size(),rng()%260);assert(before==p);}
 puts("PASS: real HCI command/connection outcome prefixes, bounds, accept-list type, no handle/address/key retention, 100000 random prefixes (ASan/UBSan).");
}
