// Sequoia 24G824 declarations. Slot map derived from the installed Boot KC.
// ReAWDL (maddog860) supplied Sonoma comparison declarations, GPL-2.0.
// Private placeholder entries are vtable declarations only and are never called.
#pragma once
#include "IO80211SkywalkInterface.h"
#include "../apple_private_spi.h"
class IO80211Buffer;
class IO80211BufferPool;
class IO80211VirtualInterface : public IO80211SkywalkInterface {
    OSDeclareDefaultStructors(IO80211VirtualInterface)
public:
    // Nonvirtual native exports. These do not change the virtual dispatch table.
    IO80211BufferPool *getMgmtFramePool();
    void setCompanionLowLatencySkywalkInterface(IO80211SkywalkInterface *);
    void bpfTapInput(IO80211Buffer *, unsigned, void *, unsigned long);
    virtual void free() override; // slot 18
    virtual IOReturn configureReport(IOReportChannelList*, unsigned int, void*, void*) override; // slot 133
    virtual IOReturn updateReport(IOReportChannelList*, unsigned int, void*, void*) override; // slot 134
    virtual bool start(IOService*) override; // slot 184
    virtual void stop(IOService*) override; // slot 185
    virtual bool terminate(
        IOOptionBits options = 0
    ) override; // slot 192
    virtual bool attach(
        IOService *
    ) override; // slot 206
    virtual void detach(
        IOService *
    ) override; // slot 207
    virtual IOReturn newUserClient(task*, void*, unsigned int, OSDictionary*, IOUserClient**) override; // slot 238
    virtual const char* stringFromReturn(int) override; // slot 240
    virtual IOReturn enable(unsigned int) override; // slot 266
    virtual IOReturn prepareBSDInterface(struct __ifnet*, unsigned int) override; // slot 285
    virtual IOReturn processBSDCommand(struct __ifnet*, unsigned int, void*) override; // slot 290
    virtual SInt32 setInterfaceEnable(bool) override; // slot 293
    virtual UInt32 getFeatureFlags() override; // slot 310
    virtual bool bpfTap(UInt,UInt) override; // slot 315
    virtual bool setMulticastAddresses(ether_addr const*,UInt) override; // slot 336
    virtual void * createPeerManager() override; // slot 352
    virtual void postMessage(unsigned int, void*, unsigned long, bool) override; // slot 354
    virtual void logTxPacket(IO80211NetworkPacket*, PacketSkywalkScratch*, apple80211_wme_ac, bool) override; // slot 358
    virtual void logTxCompletionPacket(IO80211NetworkPacket*, PacketSkywalkScratch*, unsigned char*, apple80211_wme_ac, int, unsigned int, bool, bool) override; // slot 359
    virtual IOReturn inputPacket(IO80211NetworkPacket*, packet_info_tag*, ether_header*, bool*, bool) override; // slot 361
    virtual void logSkywalkTxReqPacket(IO80211NetworkPacket*, PacketSkywalkScratch*, unsigned char*, apple80211_wme_ac, bool) override; // slot 363
    virtual SInt64 pendingPackets(unsigned char) override; // slot 364
    virtual SInt64 packetSpace(unsigned char) override; // slot 365
    virtual IO80211LinkState linkState() override; // slot 369
    virtual void setScanningState(unsigned int, bool, apple80211_scan_data*, int) override; // slot 370
    virtual void updateLinkParameters(apple80211_interface_availability*) override; // slot 374
    virtual void updateInterfaceCoexRiskPct(unsigned long long) override; // slot 375
    virtual void setInterfaceNF(apple80211_channel, long long) override; // slot 381
    virtual void setDebugFlags(unsigned long long, unsigned int) override; // slot 384
    virtual SInt64 debugFlags() override; // slot 385
    virtual void setInterfaceChipCounters(apple80211_stat_report*, apple80211_chip_counters_tx*, apple80211_chip_error_counters_tx*, apple80211_chip_counters_rx*) override; // slot 386
    virtual void setInterfaceMIBdot11(apple80211_stat_report*, apple80211_ManagementInformationBasedot11_counters*) override; // slot 387
    virtual void setFrameStats(apple80211_stat_report*, apple80211_frame_counters*) override; // slot 388
    virtual void setInfraSpecificFrameStats(apple80211_stat_report*, apple80211_infra_specific_stats*) override; // slot 389
    virtual SInt64 getWmeTxCounters(unsigned long long*) override; // slot 390
    virtual void setWoWEnabled(bool) override; // slot 392
    virtual bool wowEnabled() override; // slot 393
    virtual void printDataPath(userPrintCtx*) override; // slot 394
    virtual void _abi_0c68() __asm__("__ZN23IO80211VirtualInterface21findOrCreateFlowQueueE20IO80211FlowQueueHash") override; // slot 396
    virtual void _abi_0c70() __asm__("__ZN23IO80211VirtualInterface30findOrCreateFlowQueueWithCacheE20IO80211FlowQueueHashPb") override; // slot 397
    virtual void _abi_0c78() __asm__("__ZN23IO80211VirtualInterface21findExistingFlowQueueE20IO80211FlowQueueHash") override; // slot 398
    virtual void _abi_0c80() __asm__("__ZN23IO80211VirtualInterface17removePacketQueueEPK20IO80211FlowQueueHash") override; // slot 399
    virtual void flushPacketQueues() override; // slot 400
    virtual void cachePeer(ether_addr*, unsigned int*) override; // slot 401
    virtual bool shouldLog(unsigned long long) override; // slot 402
    virtual void vlogDebug(unsigned long long, char const*, va_list) override; // slot 403
    virtual void vlogDebugBPF(unsigned long long, char const*, va_list) override; // slot 404
    virtual void * getP2PSkywalkPeerMgr() override; // slot 407
    virtual void _abi_0cd0() __asm__("__ZN23IO80211VirtualInterface8findPeerER10ether_addr") override; // slot 409
    virtual int getEventPipeSize() override; // slot 439
    virtual UInt64 createEventPipe(IO80211APIUserClient*) override; // slot 440
    virtual bool init(IO80211Controller *, ether_addr *, unsigned, const char *);
    virtual bool setLinkState(IO80211LinkState, unsigned);
    virtual void forwardPacket(IO80211NetworkPacket *);
    virtual void handleIoctl(ifnet_t, unsigned long, void *);
    virtual void addPeerToCache(unsigned char *);
    virtual void deletePeerFromCache(unsigned char *);
    virtual bool handleDebugCmd(apple80211_debug_command *);
    virtual void _abi_peer_slot_stats() __asm__("__ZN23IO80211VirtualInterface20getPeerSlotDataStatsEP10ether_addrbP17peerSlotDataStats");
    virtual void _abi_peer_stats() __asm__("__ZN23IO80211VirtualInterface16getPeerDataStatsEP10ether_addrbP16packetCounters_t");
    virtual void _abi_clear_peer_stats() __asm__("__ZN23IO80211VirtualInterface18clearPeerDataStatsEP10ether_addrb");
    virtual void setAwdlCurrentChannelSequenceIndex(unsigned);
    virtual bool isOutputFlowControlled();
    virtual void setOutputFlowControlled();
    virtual void clearOutputFlowControlled();
    virtual unsigned configureAQMOutput();
    virtual bool attachToBpf();
    virtual bool configureIfnet();
    virtual void reset();
    virtual void dupAndTransmitMcastPacket(IO80211NetworkPacket *, unsigned char *, unsigned char *);
    virtual void freeMulticastPacket(IO80211NetworkPacket *);
    virtual void triggerAWDLMulticastTx(unsigned, unsigned char);
    virtual void p2pMulticastTx(IO80211NetworkPacket **, unsigned);
    virtual void sendPendingPacketsToStack(IO80211NetworkPacket **, unsigned);
    virtual void freePendingPackets(IO80211NetworkPacket **, unsigned);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 0);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 1);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 2);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 3);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 4);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 5);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 6);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 7);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 8);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 9);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 10);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 11);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 12);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 13);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 14);
    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, 15);
protected:
    // Partial native init can already hold a controller open / PM interest and BPF list.
    // Only test pointer presence; cleanup remains in the native terminate/free methods.
    bool hasNativeVirtualState() const {
        void *state = nullptr;
        memcpy(&state, _virtualExpansion, sizeof(state));
        return state != nullptr;
    }
private:
    uint8_t _virtualExpansion[8];
};
static_assert(sizeof(IO80211VirtualInterface) == 0x120, "24G824 virtual interface layout");
