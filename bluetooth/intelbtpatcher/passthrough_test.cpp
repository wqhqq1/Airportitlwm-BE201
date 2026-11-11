
#include <cstdint>
#include <cstddef>
#include <cassert>
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include "LECommandProbe.hpp"
using IOReturn=int;
constexpr int kIODirectionInOut=3,kIOReturnSuccess=0;
enum KernelVersion {Sequoia=24};static int getKernelVersion(){return 24;}
static void *IOMalloc(size_t n){return malloc(n);}static void IOFree(void *p,size_t){free(p);}
struct IOMemoryDescriptor {
 uint8_t data[260]={};size_t length=260;unsigned refs=1,prepareCalls=0,completeCalls=0;
 size_t getLength(){return length;}int prepare(int){prepareCalls++;return 0;}void complete(int){completeCalls++;}
 size_t readBytes(size_t off,void *out,size_t n){assert(off+n<=length);memcpy(out,data+off,n);return n;}
 size_t writeBytes(size_t off,const void *p,size_t n){assert(off+n<=length);memcpy(data+off,p,n);return n;}
 void retain(){refs++;}void release(){assert(refs>1);refs--;}
};
using IOUSBHostCompletionAction=void(*)(void*,void*,IOReturn,uint32_t);
struct IOUSBHostCompletion {void *owner;IOUSBHostCompletionAction action;void *parameter;};
struct AsyncOwnerData {void *owner;IOMemoryDescriptor *dataBuffer;IOUSBHostCompletionAction action;};
struct __attribute__((packed)) HciEventHdr {uint8_t evt,len,data[0];};
static const unsigned HCI_EVT_LE_META=0x3e,HCI_EVT_LE_META_READ_REMOTE_FEATURES_COMPLETE=4;
static uint8_t fakePhyUpdateCompleteEvent[]={0x3e,6,0x0c,0,0,0,2,2};
static uint8_t fakeDataLengthChangeEvent[]={0x3e,0x0b,7,0,0,0x1b,0,0x48,1,0x1b,0,0x48,1};
static int remoteReadSCount=1000;
static bool be201LEBaselineEnabled=true,be201ProbeEnabled=false;
static uintptr_t be201EventPipe=1;
static be201probe::Statistics be201ProbeStats={};
struct BE201EventRead {IOMemoryDescriptor *buffer;uint32_t requested;};
static void eventUSBCompleted(uint64_t ticket,IOReturn,uint32_t,bool){auto *p=(BE201EventRead*)(uintptr_t)ticket;p->buffer->release();delete p;}
#include "AddressCompletion.hpp"
class CIntelBTPatcher {
public:
 static void *_hookPipeInstance;
 uintptr_t oldAsyncIO;
 static IOReturn newAsyncIO(void*,IOMemoryDescriptor*,uint32_t,IOUSBHostCompletion*,uint32_t);
};
void *CIntelBTPatcher::_hookPipeInstance=(void*)1;
static CIntelBTPatcher context;
static CIntelBTPatcher *callbackIBTPatcher=&context;
#define FunctionCast(fn, ptr) reinterpret_cast<decltype(&fn)>(ptr)
static uint32_t callbackBytes=0;static unsigned callbacks=0;static void *expectedOwner=(void*)0x1234,*expectedParameter=(void*)0x5678;
static void received(void *owner,void *parameter,IOReturn status,uint32_t n){assert(owner==expectedOwner&&parameter==expectedParameter&&status==0);callbacks++;callbackBytes=n;}
static IOReturn oldIO(void*,IOMemoryDescriptor*,uint32_t n,IOUSBHostCompletion *c,uint32_t){assert(c&&c->action);c->action(c->owner,c->parameter,0,n);return 0;}
static void asyncIOCompletion(void* owner, void* parameter, IOReturn status, uint32_t bytesTransferred)
{
    AsyncOwnerData *asyncOwner = (AsyncOwnerData *)owner;
    IOMemoryDescriptor* dataBuffer = asyncOwner->dataBuffer;
    // #514 3-stage rewrite of the repeated LE Read Remote Features Complete (0x04) events:
    //   stage 0 = the real one (pass through), 1 = rewrite to fake PHY Update Complete,
    //   2 = rewrite to fake LE Data Length Change (clears bluetoothd's LE_READY_WAIT_FOR_LENGTH).
    static int leMetaStage = 0;
    uint32_t allocLen = bytesTransferred;

    if (dataBuffer && bytesTransferred) {
        void *buffer = IOMalloc(allocLen);
        if (buffer) {
            if (dataBuffer->getLength() > 0 && (getKernelVersion() < KernelVersion::Sequoia || !dataBuffer->prepare(kIODirectionInOut))) {
                dataBuffer->readBytes(0, buffer, allocLen);
                HciEventHdr *hdr = (HciEventHdr *)buffer;
                if (hdr->evt == HCI_EVT_LE_META && hdr->data[0] == HCI_EVT_LE_META_READ_REMOTE_FEATURES_COMPLETE) {
                    if (leMetaStage == 0) {
                        leMetaStage = 1;            // real features complete -> pass through
                    } else if (leMetaStage == 1) {  // 1st duplicate -> fake PHY Update Complete
                        fakePhyUpdateCompleteEvent[4] = hdr->data[2];
                        fakePhyUpdateCompleteEvent[5] = hdr->data[3];
                        dataBuffer->writeBytes(0, fakePhyUpdateCompleteEvent, 8);
                        bytesTransferred = 8;
                        leMetaStage = 2;
                        remoteReadSCount--;
                    } else {                        // 2nd duplicate -> fake LE Data Length Change
                        fakeDataLengthChangeEvent[3] = hdr->data[2];
                        fakeDataLengthChangeEvent[4] = hdr->data[3];
                        dataBuffer->writeBytes(0, fakeDataLengthChangeEvent, 13);
                        bytesTransferred = 13;
                        leMetaStage = 0;
                        remoteReadSCount--;
                    }
                }
                if (getKernelVersion() >= KernelVersion::Sequoia) dataBuffer->complete(kIODirectionInOut);
            }
            IOFree(buffer, allocLen);
        }
    }
    if (asyncOwner->action)
        asyncOwner->action(asyncOwner->owner, parameter, status, bytesTransferred);
    delete asyncOwner;
}

IOReturn CIntelBTPatcher::
newAsyncIO(void *that, IOMemoryDescriptor* dataBuffer, uint32_t bytesTransferred, IOUSBHostCompletion* completion, uint32_t completionTimeoutMs)
{
    // On the opt-in BE201 fallback, preserve every real event. In particular,
    // never carry the legacy global rewrite stage into the next connection.
    if (remoteReadSCount > 0 && that == _hookPipeInstance && completion &&
        !(be201LEBaselineEnabled && reinterpret_cast<uintptr_t>(that)==
          __atomic_load_n(&be201EventPipe,__ATOMIC_RELAXED))) {
        AsyncOwnerData *ownerData = new AsyncOwnerData;
        ownerData->action = completion->action;
        ownerData->owner = completion->owner;
        ownerData->dataBuffer = dataBuffer;
        completion->action = asyncIOCompletion;
        completion->owner = ownerData;
    }
    BE201AddressCompletion *observer = nullptr;
    IOUSBHostCompletion wrapped = {};
    if (be201ProbeEnabled && reinterpret_cast<uintptr_t>(that) ==
        __atomic_load_n(&be201EventPipe, __ATOMIC_RELAXED) && dataBuffer &&
        completion && completion->action) {
        auto *context = new BE201EventRead;
        if (context) {
            observer = new BE201AddressCompletion;
            if (observer) {
                dataBuffer->retain(); context->buffer = dataBuffer; context->requested = bytesTransferred;
                observer->original = *completion;
                observer->ticket = reinterpret_cast<uintptr_t>(context);
                observer->finished = eventUSBCompleted;
                wrapped = observer->wrapped();
            } else delete context;
        }
        if (!observer) {
            be201probe::increment(be201ProbeStats.eventObserverAllocationFailures);
            be201probe::increment(be201ProbeStats.sequence);
        }
    }
    const IOReturn result = FunctionCast(newAsyncIO, callbackIBTPatcher->oldAsyncIO)(that, dataBuffer, bytesTransferred, observer ? &wrapped : completion, completionTimeoutMs);
    if (observer) observer->submitted(result);
    return result;
}


int main(){
 context.oldAsyncIO=reinterpret_cast<uintptr_t>(oldIO);
 // The real production wrapper must pass through every first feature event,
 // even with a stale global legacy counter and the controller reusing handles.
 for(unsigned probe=0;probe<2;probe++)for(unsigned round=0;round<300;round++){
  be201ProbeEnabled=probe;IOMemoryDescriptor b;b.data[0]=0x3e;b.data[1]=12;b.data[2]=4;b.data[3]=0;b.data[4]=round&1;b.data[5]=8;
  memset(b.data+6,0xa5,8);uint8_t before[14];memcpy(before,b.data,14);
  IOUSBHostCompletion c={expectedOwner,received,expectedParameter};const auto original=c;unsigned calls=callbacks;
  assert(CIntelBTPatcher::newAsyncIO((void*)1,&b,14,&c,0)==0);
  assert(callbacks==calls+1 && callbackBytes==14 && !memcmp(before,b.data,14));
  assert(c.owner==original.owner && c.action==original.action && c.parameter==original.parameter && b.refs==1);
 }
 // Arbitrary/truncated input cannot reach the legacy unbounded rewriter on
 // the BE201 baseline path. No buffer byte or callback length changes.
 be201ProbeEnabled=false;
 for(unsigned n=0;n<260;n++){
  IOMemoryDescriptor b;memset(b.data,0xcc,sizeof b.data);uint8_t before[260];memcpy(before,b.data,260);
  IOUSBHostCompletion c={expectedOwner,received,expectedParameter};CIntelBTPatcher::newAsyncIO((void*)1,&b,n,&c,0);
  assert(callbackBytes==n && !memcmp(before,b.data,260));
 }
 // With the opt-in fallback off, reproduce the inherited cross-connection
 // stage drift as a control; each record represents a new connection.
 be201LEBaselineEnabled=false;
 for(unsigned round=0;round<3;round++){
  IOMemoryDescriptor b;b.data[0]=0x3e;b.data[1]=12;b.data[2]=4;b.data[4]=round;b.data[5]=8;
  IOUSBHostCompletion c={expectedOwner,received,expectedParameter};CIntelBTPatcher::newAsyncIO((void*)1,&b,14,&c,0);
  assert(b.data[2]==(round==0?4:round==1?0x0c:7));assert(callbackBytes==(round==0?14:round==1?8:13));
 }
 // Other Intel pipes retain their pre-existing path even if the flag is on.
 be201LEBaselineEnabled=true;CIntelBTPatcher::_hookPipeInstance=(void*)2;
 for(unsigned round=0;round<3;round++){
  IOMemoryDescriptor b;b.data[0]=0x3e;b.data[1]=12;b.data[2]=4;b.data[4]=round;b.data[5]=8;
  IOUSBHostCompletion c={expectedOwner,received,expectedParameter};CIntelBTPatcher::newAsyncIO((void*)2,&b,14,&c,0);
  assert(b.data[2]==(round==0?4:round==1?0x0c:7));
 }
 puts("PASS: actual production USB completion path: 600 reconnects preserve every real feature event, reused handles/stale global counter, probe on/off, 260 bounded callback lengths; legacy cross-connection drift reproduced, other Intel path unchanged (ASan/UBSan).");
}
