#include <cstdint>
#include <cstddef>
#include <cassert>
#include <cstring>
#include <cstdio>
#include "LECommandProbe.hpp"
#include "PeerReport.hpp"
static be201peer::Stats be201PeerStats={};
static be201peer::Observer be201PeerObserver={};
using IOReturn=int;static const int kIOReturnSuccess=0,kIODirectionIn=1;
static be201probe::Statistics be201ProbeStats={};
struct IOMemoryDescriptor {
 unsigned refs=1,prepared=0,completed=0,reads=0;int prepareStatus=0;
 uint8_t bytes[300]={0x0e,4,1,5,0x20,0};size_t size=6;
 size_t getLength(){return size;}
 int prepare(int){prepared++;return prepareStatus;}
 void complete(int){completed++;}
 size_t readBytes(size_t off,void*out,size_t n){assert(off==0&&n<=257&&n<=size);reads++;memcpy(out,bytes,n);return n;}
 void retain(){refs++;}void release(){assert(refs>1);refs--;}
};
struct BE201EventRead { IOMemoryDescriptor *buffer; uint32_t requested; };
static void eventUSBCompleted(uint64_t cookie, IOReturn status, uint32_t bytes, bool fromCallback) {
    auto *context = reinterpret_cast<BE201EventRead *>(uintptr_t(cookie));
    auto *buffer = context->buffer;
    if (fromCallback) {
        be201probe::increment(be201ProbeStats.eventReadCallbacks);
        be201probe::increment(be201ProbeStats.sequence);
    }
    if (fromCallback && status == kIOReturnSuccess && bytes &&
        bytes <= context->requested && bytes <= buffer->getLength()) {
        uint8_t prefix[8] = {};
        const size_t wanted = bytes < 6 ? bytes : 6;
        if (buffer->prepare(kIODirectionIn) == kIOReturnSuccess) {
            size_t count = buffer->readBytes(0, prefix, wanted);
            // Only successful LE connection-complete events need role/type.
            // Byte 8 starts their peer address; no extra bytes are requested.
            if(count==6 && bytes>=8 && prefix[0]==0x3e && prefix[3]==0 &&
               (prefix[2]==1 || prefix[2]==0x0a))
                count=buffer->readBytes(0,prefix,sizeof(prefix));
            // Inspect only bounded LE legacy advertising reports for the fixed
            // public test UUID. All fields exported by the observer are numeric.
            if(count>=3 && prefix[0]==0x3e && prefix[2]==2 && bytes<=257) {
                uint8_t report[257]={};
                size_t got=buffer->readBytes(0,report,bytes);
                if(got==bytes)be201PeerObserver.event(be201PeerStats,report,got);
            }
            buffer->complete(kIODirectionIn);
            be201probe::eventPrefix(be201ProbeStats, prefix, count, bytes);
        } else {
            be201probe::increment(be201ProbeStats.eventReadFailures);
        }
    } else if (status != kIOReturnSuccess) {
        be201probe::increment(be201ProbeStats.eventUSBErrors);
        be201probe::increment(be201ProbeStats.sequence);
    }
    buffer->release(); delete context;
}
static void run(IOMemoryDescriptor &d,int status,unsigned bytes,bool callback,unsigned requested=64) {
 auto *c=new BE201EventRead;d.retain();c->buffer=&d;c->requested=requested;
 eventUSBCompleted(reinterpret_cast<uintptr_t>(c),status,bytes,callback);assert(d.refs==1);
}
int main(){IOMemoryDescriptor d;run(d,0,6,true);assert(d.reads==1&&d.prepared==1&&d.completed==1&&be201ProbeStats.randomAddressHCICompletions==1);
 run(d,-1,0,true);run(d,-1,0,false);run(d,0,0,true);run(d,0,7,true);run(d,0,6,true,5);assert(d.reads==1);
 d.prepareStatus=-1;run(d,0,6,true);assert(d.reads==1&&d.completed==1&&be201ProbeStats.eventReadFailures==1);
 IOMemoryDescriptor le;le.size=21;le.bytes[0]=0x3e;le.bytes[1]=19;le.bytes[2]=1;le.bytes[3]=0;le.bytes[6]=0;le.bytes[7]=1;le.bytes[8]=0xa5;
 run(le,0,21,true);assert(le.reads==2 && le.completed==1 && le.bytes[8]==0xa5 && be201ProbeStats.centralConnectionSuccesses==1);
 IOMemoryDescriptor ad;ad.size=32;const uint8_t pkt[]={0x3e,30,2,1,0,1,1,2,3,4,5,6,18,17,7,3,0,0,0,0,0,0x12,0x8e,1,0x41,0x20,0xbe,0xd0,0xa1,0x8e,0x4d,0xc0};memcpy(ad.bytes,pkt,sizeof pkt);run(ad,0,32,true);assert(ad.reads==2 && ad.completed==1 && be201PeerStats.testReports==1);assert(!memcmp(ad.bytes,pkt,sizeof pkt));
 puts("PASS: actual production event read callback; descriptor lifetime, bounded prefix/test-service reads; input unchanged, transport and length bounds, prepare/complete balance, abort/submission failure cleanup (ASan/UBSan).");}
