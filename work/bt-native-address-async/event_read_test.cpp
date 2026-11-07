#include <cstdint>
#include <cstddef>
#include <cassert>
#include <cstring>
#include <cstdio>
#include "LECommandProbe.hpp"
using IOReturn=int;static const int kIOReturnSuccess=0,kIODirectionIn=1;
static be201probe::Statistics be201ProbeStats={};
struct IOMemoryDescriptor {
 unsigned refs=1,prepared=0,completed=0,reads=0;int prepareStatus=0;
 uint8_t bytes[64]={0x0e,4,1,5,0x20,0};size_t size=6;
 size_t getLength(){return size;}
 int prepare(int){prepared++;return prepareStatus;}
 void complete(int){completed++;}
 size_t readBytes(size_t off,void*out,size_t n){assert(off==0&&n<=6&&n<=size);reads++;memcpy(out,bytes,n);return n;}
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
        uint8_t prefix[6] = {};
        const size_t wanted = bytes < sizeof(prefix) ? bytes : sizeof(prefix);
        if (buffer->prepare(kIODirectionIn) == kIOReturnSuccess) {
            const size_t count = buffer->readBytes(0, prefix, wanted);
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
 puts("PASS: actual production event read callback; descriptor lifetime, <=6-byte reads, transport and length bounds, prepare/complete balance, abort/submission failure cleanup (ASan/UBSan).");}
