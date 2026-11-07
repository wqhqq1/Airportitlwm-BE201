// Sequoia 24G824 x86_64 ABI adapter. Binding/injection and role arbitration are
// intentionally not supplied here. Invoke only on the serialized native stack
// queue with a binding verified against that exact binary. No USB side channel.
#pragma once
#include "ResolvingListCommand.hpp"
namespace be201privacy {
using OIStatus=uint32_t;
struct NativeByteStream {
    const uint8_t *data;
    uint16_t capacity,limit,position;
    uint8_t mode,error;
};
static_assert(sizeof(NativeByteStream)==16,"native byte stream ABI");
static_assert(offsetof(NativeByteStream,position)==12,"native cursor ABI");
using NativeCompletion=void(*)(OIStatus,void*,NativeByteStream*);
struct NativeRequest {
    uint32_t expires;
    uint16_t opcode,commandID;
    uint8_t expectedEvent,alternateEvent,subopcode0,subopcode1;
    uint32_t reserved;
    NativeCompletion completion;
    void *context;
};
static_assert(sizeof(NativeRequest)==32,"native request ABI");
static_assert(offsetof(NativeRequest,opcode)==4,"native opcode ABI");
static_assert(offsetof(NativeRequest,completion)==16,"native callback ABI");
static_assert(offsetof(NativeRequest,context)==24,"native context ABI");
struct NativeQueueAPI {
    // Must check native state AND stack queue ownership. This is a precondition,
    // not a replacement for the real scan/advertising/initiator pause barrier.
    bool (*stableReady)();
    void *(*allocate)(size_t);
    void (*release)(void*);
    OIStatus (*enqueue)(uint8_t*,uint16_t,const NativeRequest*);
};
enum class Submission { Accepted, NativeRejected, Invalid, NoMemory, UnexpectedStatus };
struct SubmitResult {Submission result;OIStatus nativeStatus;};
inline void wipe(void *buffer,size_t n) {
    volatile uint8_t *p=static_cast<volatile uint8_t*>(buffer);
    for(size_t i=0;i<n;i++)p[i]=0;
}
// The original native raw marshaller rejects opcodes below 0xfc00. Build the
// native queue's H4 packet instead; do not weaken that global marshaller guard.
inline SubmitResult submitStandard(const NativeQueueAPI &api,
        const ResolvingListCommand &command,NativeCompletion callback,void *context) {
    if(!api.stableReady||!api.allocate||!api.release||!api.enqueue||!callback||!context)
        return {Submission::Invalid,0};
    const uint8_t *wire=command.data();size_t n=command.size();
    if(n<3 || n!=size_t(3+wire[2]))return {Submission::Invalid,0};
    uint16_t op=uint16_t(wire[0])|uint16_t(wire[1])<<8;
    bool valid=(op==0x2027&&n==42)||(op==0x2028&&n==10)||
               (op==0x202a&&n==3)||(op==0x202d&&n==4);
    if(!valid||!api.stableReady())return {Submission::Invalid,0};
    uint8_t *packet=static_cast<uint8_t*>(api.allocate(n+1));
    if(!packet)return {Submission::NoMemory,0};
    packet[0]=1;for(size_t i=0;i<n;i++)packet[i+1]=wire[i];
    NativeRequest request={};request.opcode=op;request.commandID=0x110;
    request.expectedEvent=0x0e;request.completion=callback;request.context=context;
    // enqueue copies the 32-byte request synchronously. The packet is retained
    // until native transport submission. Context must outlive actual completion,
    // including synchronous error completion before enqueue returns.
    OIStatus status=api.enqueue(packet,uint16_t(n+1),&request);
    if(status==0)return {Submission::Accepted,status};
    if(status==0x263)return {Submission::NativeRejected,status}; // native freed packet
    if(status==0xe7c) { // startup restriction: native did NOT take/free packet
        wipe(packet,n+1);api.release(packet);
        return {Submission::NativeRejected,status};
    }
    // The pinned queue has only those three returns. Unknown ABI/state requires
    // quarantine; do not guess ownership and risk a second free or false success.
    return {Submission::UnexpectedStatus,status};
}
struct CompletionResult {OIStatus nativeStatus;bool malformed;bool hasCapacity;uint8_t capacity;};
inline CompletionResult decodeStandard(OIStatus status,uint16_t opcode,const NativeByteStream *s) {
    CompletionResult r={status,false,false,0};
    // Native event dispatch has already consumed and mapped the HCI status byte.
    // Cancellation/error paths may have no usable return-parameter stream.
    if(status)return r;
    size_t expected;
    if(opcode==0x202a)expected=1;
    else if(opcode==0x2027||opcode==0x2028||opcode==0x202d)expected=0;
    else {r.malformed=true;return r;}
    if(!s || s->error || s->mode!=1 || s->limit>s->capacity ||
       s->position>s->limit || size_t(s->limit-s->position)!=expected ||
       (expected&&!s->data)) {r.malformed=true;return r;}
    if(expected){r.hasCapacity=true;r.capacity=s->data[s->position];}
    return r;
}
}
