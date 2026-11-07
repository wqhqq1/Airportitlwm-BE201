// Factory-only declarations, pinned to 24G824 exported symbols.
// These opaque types must never be instantiated, sized, subclassed or virtually called.
// Native submission callbacks use unsigned return and Packet * const *, not SDK's const Packet **.
#pragma once
class IOSkywalkPacket;
class IOSkywalkTxSubmissionQueue;
class IOSkywalkTxCompletionQueue;
class IOSkywalkRxSubmissionQueue;
class IOSkywalkRxCompletionQueue;
// Direct calls to 24G824's exported implementations. IOSkywalkNetworkPacket overrides none of these.
extern "C" {
uint8_t *be201PacketBase(const IOSkywalkPacket *) __asm__("__ZNK15IOSkywalkPacket21getDataVirtualAddressEv");
UInt16 be201PacketOffset(const IOSkywalkPacket *) __asm__("__ZNK15IOSkywalkPacket13getDataOffsetEv");
UInt32 be201PacketLength(const IOSkywalkPacket *) __asm__("__ZNK15IOSkywalkPacket13getDataLengthEv");
IOReturn be201PacketSetLength(IOSkywalkPacket *, UInt32) __asm__("__ZN15IOSkywalkPacket13setDataLengthEj");
IOReturn be201PacketPrepare(IOSkywalkPacket *, void *, UInt32, UInt32) __asm__("__ZN15IOSkywalkPacket16prepareWithQueueEP20IOSkywalkPacketQueuejj");
IOReturn be201PoolAllocate(IOSkywalkPacketBufferPool *, IOSkywalkPacket **, UInt32) __asm__("__ZN25IOSkywalkPacketBufferPool14allocatePacketEPP15IOSkywalkPacketj");
void be201PoolDeallocate(IOSkywalkPacketBufferPool *, IOSkywalkPacket *) __asm__("__ZN25IOSkywalkPacketBufferPool16deallocatePacketEP15IOSkywalkPacket");
IOReturn be201TxCompEnqueue(void *, IOSkywalkPacket *const *, UInt32, UInt32) __asm__("__ZN26IOSkywalkTxCompletionQueue14enqueuePacketsEPKP15IOSkywalkPacketjj");
IOReturn be201RxCompEnqueue(void *, IOSkywalkPacket *const *, UInt32, UInt32) __asm__("__ZN26IOSkywalkRxCompletionQueue14enqueuePacketsEPKP15IOSkywalkPacketjj");
void be201TxSubEnable(void *) __asm__("__ZN26IOSkywalkTxSubmissionQueue6enableEv");
void be201TxCompEnable(void *) __asm__("__ZN26IOSkywalkTxCompletionQueue6enableEv");
void be201RxCompEnable(void *) __asm__("__ZN26IOSkywalkRxCompletionQueue6enableEv");
IOReturn be201TxSubRequestDequeue(void *, void *, UInt32) __asm__("__ZN26IOSkywalkTxSubmissionQueue14requestDequeueEPvj");
}
class IOSkywalkTxSubmissionQueue {
public:
    static IOSkywalkTxSubmissionQueue *withPool(IOSkywalkPacketBufferPool *, UInt32, UInt32, OSObject *,
        UInt32 (*)(OSObject *, IOSkywalkTxSubmissionQueue *, IOSkywalkPacket *const *, UInt32, void *), void *, IOOptionBits);
};
class IOSkywalkTxCompletionQueue {
public:
    static IOSkywalkTxCompletionQueue *withPool(IOSkywalkPacketBufferPool *, UInt32, UInt32, OSObject *,
        UInt32 (*)(OSObject *, IOSkywalkTxCompletionQueue *, IOSkywalkPacket **, UInt32, void *), void *, IOOptionBits);
};
class IOSkywalkRxSubmissionQueue {
public:
    static IOSkywalkRxSubmissionQueue *withPool(IOSkywalkPacketBufferPool *, UInt32, UInt32, UInt32, OSObject *,
        UInt32 (*)(OSObject *, IOSkywalkRxSubmissionQueue *, IOSkywalkPacket *const *, UInt32, void *), void *, IOOptionBits);
};
class IOSkywalkRxCompletionQueue {
public:
    static IOSkywalkRxCompletionQueue *withPool(IOSkywalkPacketBufferPool *, UInt32, UInt32, OSObject *,
        UInt32 (*)(OSObject *, IOSkywalkRxCompletionQueue *, IOSkywalkPacket **, UInt32, void *), void *, IOOptionBits);
};
