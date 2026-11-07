// Experimental Sequoia AWDL object. A registered, DOWN interface is not an operational AWDL link.
#pragma once
#include <Airport/Apple80211.h>
#include <Airport/macOS15/IO80211AWDLProtocol.h>
#include "iwx_awdl_probe.h"
class AirportItlwm;
class IOSkywalkPacketQueue;
class IOSkywalkPacket;
class IOSkywalkTxSubmissionQueue;
class IOTimerEventSource;
class AirportItlwmLowLatencyInterface;
class AirportItlwmAWDLInterface : public IO80211AWDLProtocol {
    OSDeclareDefaultStructors(AirportItlwmAWDLInterface)
public:
    bool initForController(AirportItlwm *, const ether_addr &);
    bool attach(IOService *) override;
    void detach(IOService *) override;
    IO80211Controller *getController() override;
    bool start(IOService *) override;
    void stop(IOService *) override;
    void free() override;
    // After native init the controller and peer manager point at this object, so a failed
    // creation keeps it instead of freeing it. Only controller stop tears it down.
    bool holdsNativeState() const { return initialized; }
    // Called once the BSD client has attached, which needs the published service.
    void markDown();
    // Called on the controller workloop with a normalized, borrowed frame.
    void inputActionFrame(const uint8_t *, size_t, uint8_t, int, uint32_t);
    void txRoom();
    void peerCacheDone(const uint8_t *, bool);
    void umiDone(const uint8_t *, bool);
    // Frames for llw0 arrive here: the radio has one AWDL address and no way to tell them apart.
    void setCompanion(AirportItlwmLowLatencyInterface *interface) { companion = interface; }
    // Native returns "awdl" here; the base falls back to "en" until registration info exists.
    const char *getBSDNamePrefix() override;
    IOReturn enable(UInt) override;
    SInt32 setInterfaceEnable(bool) override;
    SInt32 setRunningState(bool) override;
    IO80211LinkState linkState() override;
    bool setLinkState(IO80211LinkState, unsigned) override;
    bool setLinkState(IO80211LinkState, unsigned, bool, unsigned) override;
    IOReturn setMacAddress(ether_addr &) override;
    IOReturn unsupported(unsigned);
    // Takes a set request without acting on it, only if the test turned that on.
    IOReturn acceptSet(unsigned);
    // Same, keeping a copy of what the native AWDL manager asked for.
    IOReturn acceptSet(unsigned, const void *, size_t);
    IOReturn getSSID(apple80211_ssid_data *) override;
    IOReturn getCHANNEL(apple80211_channel_data *) override;
    IOReturn getBSSID(apple80211_bssid_data *) override;
    IOReturn getSTATE(apple80211_state_data *) override;
    IOReturn getAWDL_SYNC_PARAMS(apple80211_awdl_sync_params *) override;
    IOReturn getAWDL_SYNC_ENABLED(apple80211_awdl_sync_enabled *) override;
    IOReturn getAWDL_EXTENSION_STATE_MACHINE_PARAMETERS(apple80211_awdl_extension_state_machine_parameter *) override;
    IOReturn getAWDL_ELECTION_ID(apple80211_awdl_election_id *) override;
    IOReturn getAWDL_ELECTION_METRIC(apple80211_awdl_election_metric *) override;
    IOReturn getAWDL_SYNCHRONIZATION_CHANNEL_SEQUENCE(apple80211_awdl_sync_channel_sequence *) override;
    IOReturn getPEER_CACHE_MAXIMUM_SIZE(apple80211_peer_cache_maximum_size *) override;
    IOReturn getAWDL_MASTER_CHANNEL(apple80211_awdl_master_channel *) override;
    IOReturn getAWDL_SYNC_STATE(apple80211_awdl_sync_state *) override;
    IOReturn getAWDL_ELECTION_RSSI_THRESHOLDS(apple80211_awdl_election_rssi_thresholds *) override;
    IOReturn getAWDL_PRESENCE_MODE(apple80211_awdl_presence_mode *) override;
    IOReturn getAWDL_ELECTION_PARAMS(apple80211_awdl_election_params *) override;
    IOReturn getAWDL_DEVICE_CAPABILITIES(apple80211_awdl_device_capabilities *) override;
    IOReturn getAWDL_SECONDARY_MASTER_CHANNEL(apple80211_awdl_secondary_master_channel *) override;
    IOReturn getAWDL_AF_TX_MODE(apple80211_awdl_af_tx_mode *) override;
    IOReturn getAWDL_MIN_RATE(apple80211_awdl_min_rate *) override;
    IOReturn getAWDL_ENCRYPTION_TYPE(apple80211_encrypt *) override;
    IOReturn getAWDL_TXCAL_PERIOD(apple80211_awdl_txcal_period *) override;
    IOReturn getAWDL_DEV_STATS(apple80211_awdl_dev_stats *) override;
    IOReturn getAWDL_DFSP_CONFIG(apple80211_awdl_dfsp_config *) override;
    IOReturn getAWDL_CCA(apple80211_awdl_cca *) override;
    IOReturn getAWDL_AF_SECONDARY_PAYLOAD_CAPABILITIES(apple80211_awdl_cap *) override;
    IOReturn getLLW_PARAMS(apple80211_llw_params *) override;
    IOReturn setSSID(apple80211_ssid_data *) override;
    IOReturn setCHANNEL(apple80211_channel_data *) override;
    IOReturn setAWDL_SYNC_PARAMS(apple80211_awdl_sync_params *) override;
    IOReturn setAWDL_SYNC_ENABLED(apple80211_awdl_sync_enabled *) override;
    IOReturn setAWDL_EXTENSION_STATE_MACHINE_PARAMETERS(apple80211_awdl_extension_state_machine_parameter *) override;
    IOReturn setAWDL_ELECTION_ID(apple80211_awdl_election_id *) override;
    IOReturn setAWDL_BSSID(apple80211_awdl_bssid *) override;
    IOReturn setAWDL_ELECTION_METRIC(apple80211_awdl_election_metric *) override;
    IOReturn setAWDL_SYNCHRONIZATION_CHANNEL_SEQUENCE(apple80211_awdl_sync_channel_sequence *) override;
    IOReturn setAWDL_MASTER_CHANNEL(apple80211_awdl_master_channel *) override;
    IOReturn setAWDL_SYNC_STATE(apple80211_awdl_sync_state *) override;
    IOReturn setAWDL_ELECTION_RSSI_THRESHOLDS(apple80211_awdl_election_rssi_thresholds *) override;
    IOReturn setAWDL_PRESENCE_MODE(apple80211_awdl_presence_mode *) override;
    IOReturn setPEER_CACHE_CONTROL(apple80211_peer_cache_control *) override;
    IOReturn setAWDL_OOB_REQUEST(apple80211_awdl_oob_request *) override;
    IOReturn setAWDL_SYNC_FRAME_TEMPLATE(apple80211_awdl_sync_frame_template *) override;
    IOReturn setAWDL_ELECTION_PARAMS(apple80211_awdl_election_params *) override;
    IOReturn setAWDL_PEER_TRAFFIC_REGISTRATION(apple80211_awdl_peer_traffic_registration *) override;
    IOReturn setAWDL_SECONDARY_MASTER_CHANNEL(apple80211_awdl_secondary_master_channel *) override;
    IOReturn setAWDL_AF_TX_MODE(apple80211_awdl_af_tx_mode *) override;
    IOReturn setAWDL_MIN_RATE(apple80211_awdl_min_rate *) override;
    IOReturn setAWDL_ENCRYPTION_KEYS(apple80211_key *) override;
    IOReturn setAWDL_ENCRYPTION_TYPE(apple80211_encrypt *) override;
    IOReturn setAWDL_OOB_AUTO_REQUEST(apple80211_awdl_oob_request *) override;
    IOReturn setAWDL_TXCAL_PERIOD(apple80211_awdl_txcal_period *) override;
    IOReturn setAWDL_AWDL_ADVERTISERS(awdl_peer_advert_add *) override;
    IOReturn setAWDL_DFSP_CONFIG(apple80211_awdl_dfsp_config *) override;
    IOReturn setAWDL_DFSP_UCSA_CONFIG(apple80211_awdl_dfsp_ucsa_config *) override;
    IOReturn setCOMPANION_SKYWALK_IF_CREATE(apple80211_companion_skywalk_if_create *) override;
    IOReturn setAWDL_OOB_SEC_PAYLOAD_REQUEST(apple80211_awdl_af_sec_payload_request *) override;
    IOReturn setLLW_PARAMS(apple80211_llw_params *) override;
    IOReturn setTX_RATE(apple80211_tx_rate *) override;
    IOReturn setP2P_COEX_PROTECTION(apple80211_p2p_coex_protection *) override;
    IOReturn setPSF_DWELL(apple80211_awdl_psf_dwell_params *) override;
    IOReturn setAWDL_CONFIG(apple80211_awdl_config *) override;
    IOReturn setAWDL_RTG_PEER_STATS_CONFIG(apple80211_rtg_peer_stats_cfg *) override;
private:
    void removeQueuesFromWorkLoop();
    void recordRequest(unsigned);
    void releaseQueueResources();
    IO80211Controller *ownerController = nullptr;
    bool initialized = false;
    bool started = false;
    bool attached = false;
    bool registered = false;
    ether_addr address = {};
    IOSkywalkPacketBufferPool *pool = nullptr;
    IOSkywalkPacketQueue *queues[4] = {};
    IOWorkLoop *queueLoop = nullptr;
    unsigned queuesOnLoop = 0;
    uint32_t unsupportedCount = 0;
    uint32_t requestCount = 0;
    uint32_t nativeRxSubmitted = 0;
    uint32_t nativeRxInvalid = 0;
    uint32_t nativeRxNoBuffer = 0;
    uint16_t requestLog[256] = {};
    uint32_t requestCounts[1024] = {};
    // Native link up runs the AWDL manager inline, so it cannot run on the ifnet ioctl thread.
    IOTimerEventSource *linkTimer = nullptr;
    bool linkRequested = false;
    bool linkActive = false;
    static void linkTimerFired(OSObject *, IOTimerEventSource *);
    // Stands in for firmware: the family's AWDL manager runs its timeline from these events.
    IOTimerEventSource *awTimer = nullptr;
    uint32_t awNumber = 0;
    uint32_t awChannels[16] = {};
    uint32_t awFlags[16] = {};
    static void awTimerFired(OSObject *, IOTimerEventSource *);
    uint32_t awSteps = 4;
    enum { kReadSyncParams, kReadSyncEnabled, kReadChannelSequence, kReadMasterChannel, kReadSyncState,
           kReadSecondaryMaster, kReadAfTxMode, kReadSlots };
    struct { uint16_t length; uint8_t bytes[0x190]; } readBack[kReadSlots] = {};
    void remember(unsigned, const void *, size_t);
    IOReturn recall(unsigned, void *, size_t, unsigned);
    uint32_t templateBad = 0;
    void takeTemplate(bool, const uint8_t *, size_t, size_t);
    // Data path, off unless the test allows it. Plain Skywalk queues, not the family's flow queues.
    bool dataActive = false;
    uint32_t awAligned = 0;
    bool peerMifSaved = false;
    uint32_t dataTx = 0, dataTxDropped = 0, dataTxOversize = 0, dataRx = 0, dataRxDropped = 0, dataRxBad = 0, dataRxRetry = 0;
    uint8_t rxEthernet[1600] = {};
    void enableData();
    void inputDataFrame(const uint8_t *, size_t);
    bool txWaiting = false;
    uint32_t dataTxCalls = 0;
    UInt32 transmit(IOSkywalkPacket *const *, UInt32);
    AirportItlwmLowLatencyInterface *companion = nullptr;
public:
    // Queue action, on the Wi-Fi work loop.
    static UInt32 txSubmitAction(OSObject *, IOSkywalkTxSubmissionQueue *, IOSkywalkPacket *const *, UInt32, void *);
private:
};

// llw0, the companion native AWDL creates for low latency traffic. Native derives from the infra class,
// but the family only asks for a Skywalk interface with role 2 and a parent, whose peer manager it borrows.
class AirportItlwmLowLatencyInterface : public IO80211VirtualInterface {
    OSDeclareDefaultStructors(AirportItlwmLowLatencyInterface)
public:
    bool initForParent(AirportItlwm *, AirportItlwmAWDLInterface *, const ether_addr &);
    bool holdsNativeState() const { return initialized; }
    bool attach(IOService *) override;
    void detach(IOService *) override;
    IO80211Controller *getController() override;
    bool start(IOService *) override;
    void stop(IOService *) override;
    void free() override;
    const char *getBSDNamePrefix() override;
    IOReturn enable(UInt) override;
    SInt32 setInterfaceEnable(bool) override;
    SInt32 setRunningState(bool) override;
    IOReturn setMacAddress(ether_addr &) override;
    // Native gives llw0 its own unique id: with awdl0's address as the id the stack answers busy (1.1.49).
    SInt32 initBSDInterfaceParameters(ifnet_init_eparams *, sockaddr_dl **) override;
    // Native llw0 takes the Skywalk flags (low latency 0x10000) without the virtual base's 0x10000000,
    // kFeatureOnDemandInterfaceEnable in IO80211SkywalkInterface::getFeatureFlags.
    UInt32 getFeatureFlags() override;
    void bringUp();
    void txRoom();
    // On the Wi-Fi work loop, with Ethernet framing from awdl0's receive path.
    void inputEthernet(const uint8_t *, size_t);
    iwx_awdl_llw_ports ports = {};
    static UInt32 txSubmitAction(OSObject *, IOSkywalkTxSubmissionQueue *, IOSkywalkPacket *const *, UInt32, void *);
private:
    UInt32 transmit(IOSkywalkPacket *const *, UInt32);
    void removeQueuesFromWorkLoop();
    void releaseQueueResources();
    static void linkTimerFired(OSObject *, IOTimerEventSource *);
    IO80211Controller *ownerController = nullptr;
    AirportItlwmAWDLInterface *parentInterface = nullptr;
    uint32_t attachPolls = 0;
    const void *uniqueId = nullptr;
    bool initialized = false, started = false, attached = false, registered = false, dataActive = false, txWaiting = false;
    ether_addr address = {};
    IOSkywalkPacketBufferPool *pool = nullptr;
    IOSkywalkPacketQueue *queues[4] = {};
    IOWorkLoop *queueLoop = nullptr;
    unsigned queuesOnLoop = 0;
    IOTimerEventSource *linkTimer = nullptr;
    uint32_t dataTx = 0, dataTxDropped = 0, dataRx = 0, dataRxDropped = 0, txCalls = 0;
};
