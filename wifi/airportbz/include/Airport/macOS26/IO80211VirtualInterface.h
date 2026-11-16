// Tahoe 25G342 declarations, from the Sequoia 24G824 header. The 25G342 Boot KC vtable of
// IO80211VirtualInterface (505 slots) has the same 53 overrides; new are flushFlowQueues, a second
// p2pMulticastTx, signalMulticastPackets and the pure setMacAddress (slot 488, moved here from
// IO80211SkywalkInterface: IO80211MacAddressAgent::setMacAddress calls it with an ether_addr&).
// Checked by scripts/test-awdl-vif-abi-tahoe.py against tests/abi/tahoe-25G342-awdl.json.
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
    virtual void free() override;
    virtual IOReturn configureReport(IOReportChannelList*, unsigned int, void*, void*) override;
    virtual IOReturn updateReport(IOReportChannelList*, unsigned int, void*, void*) override;
    virtual bool start(IOService*) override;
    virtual void stop(IOService*) override;
    virtual bool terminate(
        IOOptionBits options = 0
    ) override;
    virtual bool attach(
        IOService *
    ) override;
    virtual void detach(
        IOService *
    ) override;
    virtual IOReturn newUserClient(task*, void*, unsigned int, OSDictionary*, IOUserClient**) override;
    virtual const char* stringFromReturn(int) override;
    virtual IOReturn enable(unsigned int) override;
    virtual IOReturn prepareBSDInterface(struct __ifnet*, unsigned int) override;
    virtual IOReturn processBSDCommand(struct __ifnet*, unsigned int, void*) override;
    virtual SInt32 setInterfaceEnable(bool) override;
    virtual UInt32 getFeatureFlags() override;
    virtual bool bpfTap(UInt,UInt) override;
    virtual bool setMulticastAddresses(ether_addr const*,UInt) override;
    virtual void * createPeerManager() override;
    virtual void postMessage(unsigned int, void*, unsigned long, bool) override;
    virtual void logTxPacket(IO80211NetworkPacket*, PacketSkywalkScratch*, apple80211_wme_ac, bool) override;
    virtual void logTxCompletionPacket(IO80211NetworkPacket*, PacketSkywalkScratch*, unsigned char*, apple80211_wme_ac, int, unsigned int, bool, bool) override;
    virtual IOReturn inputPacket(IO80211NetworkPacket*, packet_info_tag*, ether_header*, bool*, bool) override;
    virtual void logSkywalkTxReqPacket(IO80211NetworkPacket*, PacketSkywalkScratch*, unsigned char*, apple80211_wme_ac, bool) override;
    virtual SInt64 pendingPackets(unsigned char) override;
    virtual SInt64 packetSpace(unsigned char) override;
    virtual IO80211LinkState linkState() override;
    virtual void setScanningState(unsigned int, bool, apple80211_scan_data*, int) override;
    virtual void updateLinkParameters(apple80211_interface_availability*) override;
    virtual void updateInterfaceCoexRiskPct(unsigned long long) override;
    virtual void setInterfaceNF(apple80211_channel, long long) override;
    virtual void setDebugFlags(unsigned long long, unsigned int) override;
    virtual SInt64 debugFlags() override;
    virtual void setInterfaceChipCounters(apple80211_stat_report*, apple80211_chip_counters_tx*, apple80211_chip_error_counters_tx*, apple80211_chip_counters_rx*) override;
    virtual void setInterfaceMIBdot11(apple80211_stat_report*, apple80211_ManagementInformationBasedot11_counters*) override;
    virtual void setFrameStats(apple80211_stat_report*, apple80211_frame_counters*) override;
    virtual void setInfraSpecificFrameStats(apple80211_stat_report*, apple80211_infra_specific_stats*) override;
    virtual SInt64 getWmeTxCounters(unsigned long long*) override;
    virtual void setWoWEnabled(bool) override;
    virtual bool wowEnabled() override;
    virtual void printDataPath(userPrintCtx*) override;
    virtual void _abi_0c68() __asm__("__ZN23IO80211VirtualInterface21findOrCreateFlowQueueE20IO80211FlowQueueHash") override;
    virtual void _abi_0c70() __asm__("__ZN23IO80211VirtualInterface30findOrCreateFlowQueueWithCacheE20IO80211FlowQueueHashPb") override;
    virtual void _abi_0c78() __asm__("__ZN23IO80211VirtualInterface21findExistingFlowQueueE20IO80211FlowQueueHash") override;
    virtual void _abi_0c80() __asm__("__ZN23IO80211VirtualInterface17removePacketQueueEPK20IO80211FlowQueueHash") override;
    virtual void flushPacketQueues() override;
    virtual void cachePeer(ether_addr*, unsigned int*) override;
    virtual bool shouldLog(unsigned long long) override;
    virtual void vlogDebug(unsigned long long, char const*, va_list) override;
    virtual void vlogDebugBPF(unsigned long long, char const*, va_list) override;
    virtual void * getP2PSkywalkPeerMgr() override;
    virtual void _abi_0cd0() __asm__("__ZN23IO80211VirtualInterface8findPeerER10ether_addr") override;
    virtual int getEventPipeSize() override;
    virtual UInt64 createEventPipe(IO80211APIUserClient*) override;
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
    virtual void flushFlowQueues(ether_addr *);
    virtual unsigned configureAQMOutput();
    virtual bool attachToBpf();
    virtual bool configureIfnet();
    virtual void reset();
    virtual void dupAndTransmitMcastPacket(IO80211NetworkPacket *, unsigned char *, unsigned char *);
    virtual void freeMulticastPacket(IO80211NetworkPacket *);
    virtual void triggerAWDLMulticastTx(unsigned, unsigned char);
    virtual void p2pMulticastTx(IO80211NetworkPacket **, unsigned);
    virtual void p2pMulticastTx(unsigned, bool);
    virtual void signalMulticastPackets(unsigned, unsigned);
    virtual void sendPendingPacketsToStack(IO80211NetworkPacket **, unsigned);
    virtual void freePendingPackets(IO80211NetworkPacket **, unsigned);
    virtual IOReturn setMacAddress(ether_addr &) = 0;
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
static_assert(sizeof(IO80211VirtualInterface) == 0x130, "25G342 virtual interface layout");
