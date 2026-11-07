#include "NativeCommandQueue.hpp"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
using namespace be201privacy;
static unsigned allocations=0,releases=0,callbacks=0,queued=0;
static OIStatus returnStatus=0,callbackStatus=0;
static bool ready=true,oom=false,synchronous=false,checkWipe=false;
static uint8_t lastPacket[43];static size_t lastSize=0;static NativeRequest lastRequest;
static bool readyFn(){return ready;}
static void *allocFn(size_t n){if(oom)return nullptr;++allocations;lastSize=n;return malloc(n);}
static void releaseFn(void *p){if(checkWipe)for(size_t i=0;i<lastSize;i++)assert(static_cast<uint8_t*>(p)[i]==0);++releases;free(p);}
static void done(OIStatus s,void *ctx,NativeByteStream *stream){assert(ctx==&callbacks);++callbacks;callbackStatus=s;if(s==0)assert(!decodeStandard(s,lastRequest.opcode,stream).malformed);}
static OIStatus enqueueFn(uint8_t *p,uint16_t n,const NativeRequest *r){
 ++queued;assert(n<=43&&n>=4);assert(p[0]==1&&n==4+p[3]);
 assert(r->opcode==(p[1]|p[2]<<8)&&r->commandID==0x110&&r->expectedEvent==14);
 assert(r->expires==0&&r->alternateEvent==0&&r->reserved==0);
 memcpy(lastPacket,p,n);lastRequest=*r;
 if(returnStatus==0||returnStatus==0x263){releaseFn(p);}
 if(synchronous&&returnStatus==0){NativeByteStream stream={nullptr,0,0,0,1,0};r->completion(0x2c8,r->context,&stream);}
 return returnStatus;
}
int main(){
 NativeQueueAPI api={readyFn,allocFn,releaseFn,enqueueFn};ResolvingListCommand c;
 c.readCapacity();auto r=submitStandard(api,c,done,&callbacks);
 assert(r.result==Submission::Accepted&&queued==1&&allocations==releases);
 assert(lastPacket[1]==0x2a&&lastPacket[2]==0x20&&lastSize==4);
 uint8_t address[6]={1,2,3,4,5,0xc6},peer[16],local[16];
 for(unsigned i=0;i<16;i++){peer[i]=uint8_t(i+1);local[i]=uint8_t(i+31);}
 assert(c.add(1,{address,6},{peer,16},{local,16}));
 r=submitStandard(api,c,done,&callbacks);assert(r.result==Submission::Accepted);
 assert(lastSize==43&&lastPacket[3]==39&&memcmp(lastPacket+11,peer,16)==0&&memcmp(lastPacket+27,local,16)==0);
 c.clear();for(unsigned i=0;i<42;i++)assert(c.data()[i]==0);
 c.resolution(true);returnStatus=0x263;
 r=submitStandard(api,c,done,&callbacks);assert(r.result==Submission::NativeRejected&&r.nativeStatus==0x263&&allocations==releases);
 returnStatus=0xe7c;checkWipe=true;
 r=submitStandard(api,c,done,&callbacks);assert(r.result==Submission::NativeRejected&&allocations==releases);checkWipe=false;
 returnStatus=0;synchronous=true;r=submitStandard(api,c,done,&callbacks);
 assert(r.result==Submission::Accepted&&callbacks==1&&callbackStatus==712);synchronous=false;
 unsigned before=queued;ready=false;r=submitStandard(api,c,done,&callbacks);assert(r.result==Submission::Invalid&&queued==before);ready=true;
 oom=true;r=submitStandard(api,c,done,&callbacks);assert(r.result==Submission::NoMemory&&queued==before);oom=false;
 c.clear();r=submitStandard(api,c,done,&callbacks);assert(r.result==Submission::Invalid&&queued==before);
 uint8_t data[8]={0,0,0,0,0,0,16,255};
 NativeByteStream stream={data,8,7,6,1,0};
 auto result=decodeStandard(0,0x202a,&stream);assert(!result.malformed&&result.hasCapacity&&result.capacity==16);
 for(unsigned cap=0;cap<10;cap++)for(unsigned limit=0;limit<10;limit++)for(unsigned cursor=0;cursor<10;cursor++)for(unsigned mode=0;mode<4;mode++)for(unsigned err=0;err<2;err++){
  stream={data,uint16_t(cap),uint16_t(limit),uint16_t(cursor),uint8_t(mode),uint8_t(err)};
  // Avoid declaring a span beyond the actual synthetic allocation.
  if(cap>8)stream.data=nullptr;
  result=decodeStandard(0,0x202a,&stream);
  bool valid=err==0&&mode==1&&limit<=cap&&cursor<=limit&&limit-cursor==1&&stream.data;
  assert(result.malformed!=valid);
  result=decodeStandard(712,0x202a,&stream);assert(result.nativeStatus==712&&!result.hasCapacity&&!result.malformed);
 }
 assert(decodeStandard(0,0x202a,nullptr).malformed);
 assert(decodeStandard(0,0x9999,nullptr).malformed);
 assert(!decodeStandard(712,0x2027,nullptr).malformed);
 assert(allocations==releases);
 puts("PASS: native queue ABI, H4 payload, input lifetime, rejection ownership, synchronous error callback, genuine 32-bit OI status, bounded completion decoding (ASan/UBSan; offline adapter).");
}
