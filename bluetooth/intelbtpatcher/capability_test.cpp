#include "PrivacyCapabilities.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
using namespace be201privacycap;
static std::vector<uint8_t> packet(unsigned op,size_t n){std::vector<uint8_t> p(n,0);p[0]=14;p[1]=uint8_t(n-2);p[2]=1;p[3]=op;p[4]=op>>8;return p;}
int main(){
 Stats s;uint8_t query[]={0x2a,0x20,0};submitted(s,query,3);assert(s.capacityRequests==1);
 auto commands=packet(0x1002,70);commands[6+34]=0xf8;commands[6+35]=7;event(s,commands.data(),70,70);
 assert(s.commandsSeen==1&&s.commandMask==255);
 for(unsigned bit=0;bit<512;bit++){
  memset(commands.data()+6,0,64);commands[6+bit/8]|=uint8_t(1U<<(bit%8));event(s,commands.data(),70,70);
  assert(s.commandMask==((bit>=275&&bit<=282)?1U<<(bit-275):0));
 }
 auto features=packet(0x2003,14);features[6]=0x40;event(s,features.data(),14,14);assert(s.featuresSeen&&s.llPrivacy);
 features[6]=0xbf;event(s,features.data(),14,14);assert(!s.llPrivacy);
 auto cap=packet(0x202a,7);cap[6]=16;event(s,cap.data(),7,7);assert(s.capacitySeen&&s.capacity==16&&s.capacityCompletions==1&&s.capacityStatus==0);
 auto err=packet(0x202a,6);err[5]=12;event(s,err.data(),6,6);assert(s.controllerErrors==1&&s.capacity==16&&s.capacityCompletions==2&&s.capacityStatus==12);
 features[5]=1;event(s,features.data(),14,14);assert(s.controllerErrors==2);
 auto reset=packet(0x0c03,6);event(s,reset.data(),6,6);assert(s.resetCount==1&&!s.commandsSeen&&!s.featuresSeen&&!s.capacitySeen&&!s.commandMask&&!s.capacity);
 unsigned random=19;
 for(unsigned round=0;round<100000;round++){
  random=random*1664525+1013904223;size_t n=random%80;std::vector<uint8_t> p(n);
  for(auto &b:p){random=random*1664525+1013904223;b=random>>24;}
  if(n>=6&&round%4==0){p[0]=14;p[3]=0x02;p[4]=0x10;}
  auto copy=p;event(s,p.data(),n,n);assert(p==copy);
 }
 for(auto *p:{&commands,&features,&cap,&reset})for(size_t n=0;n<p->size();n++){
  auto truncated=std::vector<uint8_t>(p->begin(),p->begin()+n);
  event(s,truncated.data(),n,p->size());
 }
 assert(required(nullptr,6,70)==0);
 auto secret=packet(0x2019,70);assert(required(secret.data(),6,70)==0);
 puts("PASS: all 512 command bits, LL Privacy bit, capacity/reset/error semantics, 100000 bounded immutable/truncated inputs; no secret command reads (ASan/UBSan).");
}
