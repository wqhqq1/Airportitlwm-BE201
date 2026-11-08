#include "AirportItlwmAWDLInterface.hpp"
#include "AirportItlwmV2.hpp"
#include "BE201SkywalkFactories.hpp"
#include "BE201ActionBuffer.hpp"
#include "iwx_awdl_rx.h"
// Use the repository's pool declaration; SDK queue headers include a conflicting copy.
#ifndef _IOSKYWALKPACKETBUFFERPOOL_H
#define _IOSKYWALKPACKETBUFFERPOOL_H
#endif
#include <skywalk/packet/os_packet.h>
#include <IOKit/skywalk/IOSkywalkPacketQueue.h>
#define super IO80211AWDLProtocol
OSDefineMetaClassAndStructors(AirportItlwmAWDLInterface, IO80211AWDLProtocol)

// The others take no ownership: completions go out through the queues, and receive buffers are this driver's.
static UInt32 txComplete(OSObject *, IOSkywalkTxCompletionQueue *, IOSkywalkPacket **, UInt32, void *) { return 0; }
static UInt32 rxSubmit(OSObject *, IOSkywalkRxSubmissionQueue *, IOSkywalkPacket *const *, UInt32, void *) { return 0; }
static UInt32 rxComplete(OSObject *, IOSkywalkRxCompletionQueue *, IOSkywalkPacket **, UInt32, void *) { return 0; }

// 16 TU, the availability window the AWDL manager programs through sync params.
static constexpr uint32_t kAwPeriodUs = 16384;
// reportDataPathEvents on 24G824 handles AW start as case 41; the SDK header's 42 is another event.
static constexpr unsigned kAwStartMessage = 41;
// 64 TU per channel slot: slot = (number mod slots * steps) / steps, and slot 0 is ignored
// if it comes within 64 ms of the last. Inferred from reportDataPathEvents; not seen natively.
static constexpr uint32_t kAwSlotUs = 65536;
// The manager calls slot 0 too soon under 64 ms.
static constexpr uint32_t kAwMinSlotUs = 64000;
static constexpr uint32_t kAwMaxSlotUs = 100000;

// Breadcrumb for the armed test: the pause lets the test tool save it before the next, possibly fatal, step.
static void vifStep(IOService *owner, const char *step)
{
    owner->setProperty("ItlwmAwdlVifStep", step);
    IOLog("BE201VIF step=%s\n", step);
    IOSleep(200);
}

bool AirportItlwmAWDLInterface::initForController(AirportItlwm *controller, const ether_addr &mac)
{
    ownerController = controller;
    address = mac;
    vifStep(ownerController, "native-init");
    const bool ok = IO80211VirtualInterface::init(controller, &address, APPLE80211_VIF_AWDL, "awdl");
    initialized = hasNativeVirtualState();
    if (!ok) return false;
    setInterfaceId(2); // Distinct from the infrastructure interface's OS ID, not a firmware MAC ID.
    setProperty("ItlwmAwdlVifStage", 1, 32);
    setProperty("ItlwmAwdlDataReady", false);
    setProperty("ItlwmAwdlNativeRxSubmitted", static_cast<uint64_t>(0), 32);
    setProperty("ItlwmAwdlNativeRxInvalid", static_cast<uint64_t>(0), 32);
    setProperty("ItlwmAwdlNativeRxNoBuffer", static_cast<uint64_t>(0), 32);
    return true;
}

bool AirportItlwmAWDLInterface::attach(IOService *provider)
{
    vifStep(ownerController, "attach");
    attached = IO80211VirtualInterface::attach(provider);
    return attached;
}

void AirportItlwmAWDLInterface::detach(IOService *provider)
{
    attached = false;
    IO80211VirtualInterface::detach(provider);
}

IO80211Controller *AirportItlwmAWDLInterface::getController()
{
    // Native VirtualInterface::terminate closes its controller even if start was never reached.
    return ownerController;
}

bool AirportItlwmAWDLInterface::start(IOService *provider)
{
    if (started || registered)
        return false;
    IOSkywalkEthernetInterface::RegistrationInfo info = {};
    if (!initRegistrationInfo(&info, 1, sizeof(info)))
        return false;
    // Fields verified in native createProxInterface / start on 24G824.
    uint8_t *raw = info.bytes;
    const uint32_t kind = 3, version = 2, capture = 0x80, unit = 0, options = 4, mtu = 1428;
    const uint16_t hwtype = 0x40;
    const char *prefix = "awdl";
    memcpy(raw + 0x0c, &kind, 4); memcpy(raw + 0x14, &version, 4);
    memcpy(raw + 0x24, &capture, 4); memcpy(raw + 0x28, &capture, 4);
    memcpy(raw + 0x30, &prefix, sizeof(prefix)); memcpy(raw + 0x38, &unit, 4);
    memcpy(raw + 0x3c, &hwtype, 2); memcpy(raw + 0x40, &options, 4);
    memcpy(raw + 0x48, &mtu, 4); memcpy(raw + 0x4c, &mtu, 4);
    memcpy(raw + 0x108, &address, sizeof(address));
    setProperty("ItlwmAwdlVifStage", 2, 32);
    vifStep(ownerController, "native-start");
    if (!IO80211VirtualInterface::start(provider))
        return false;
    started = true;
    setProperty("ItlwmAwdlVifStage", 3, 32);
    // Native BCM Wi-Fi uses type 1, and a netif nexus would not take the quantum pool of type 0
    // used by kernel pipe drivers. Native flags are unread: Apple's network pool leaves bit 0 clear,
    // reAWDL sets it, so the test picks one before arming.
    IOSkywalkPacketBufferPool::PoolOptions po = {};
    po.packetCount = 64; po.bufferCount = 64; po.bufferSize = 2048;
    po.maxBuffersPerPacket = 1;
    po.poolFlags = AirportItlwm::awdlVifPoolFlags();
    setProperty("ItlwmAwdlVifPoolFlags", po.poolFlags, 32);
    vifStep(ownerController, "pool");
    pool = IOSkywalkPacketBufferPool::withName("BE201AWDL", this, 1, &po);
    if (!pool) return false;
    // All queue objects come from native factories; only their OSObject/IOEventSource prefix is used.
    vifStep(ownerController, "queues");
    queues[0] = reinterpret_cast<IOSkywalkPacketQueue *>(IOSkywalkTxSubmissionQueue::withPool(pool,64,0,this,txSubmitAction,nullptr,0));
    queues[1] = reinterpret_cast<IOSkywalkPacketQueue *>(IOSkywalkTxCompletionQueue::withPool(pool,64,0,this,txComplete,nullptr,0));
    queues[2] = reinterpret_cast<IOSkywalkPacketQueue *>(IOSkywalkRxSubmissionQueue::withPool(pool,64,1,0,this,rxSubmit,nullptr,0));
    queues[3] = reinterpret_cast<IOSkywalkPacketQueue *>(IOSkywalkRxCompletionQueue::withPool(pool,64,0,this,rxComplete,nullptr,0));
    for (auto q : queues) if (!q) return false;
    // IOSkywalkTxSubmissionQueue::enable closes the source's gate unconditionally, so a queue
    // without a work loop panics on a null dereference. Native adds all of them before registering.
    vifStep(ownerController, "event-sources");
    queueLoop = ownerController->getWorkLoop();
    if (!queueLoop) return false;
    queueLoop->retain();
    for (auto q : queues) {
        if (queueLoop->addEventSource(reinterpret_cast<IOEventSource *>(q)) != kIOReturnSuccess)
            return false;
        ++queuesOnLoop;
    }
    linkTimer = IOTimerEventSource::timerEventSource(this, linkTimerFired);
    if (!linkTimer)
        return false;
    if (queueLoop->addEventSource(linkTimer) != kIOReturnSuccess) {
        OSSafeReleaseNULL(linkTimer);
        return false;
    }
    awTimer = IOTimerEventSource::timerEventSource(this, awTimerFired);
    if (!awTimer)
        return false;
    if (queueLoop->addEventSource(awTimer) != kIOReturnSuccess) {
        OSSafeReleaseNULL(awTimer);
        return false;
    }
    setProperty("ItlwmAwdlVifStage", 4, 32);
    vifStep(ownerController, "register");
    IOReturn result = registerEthernetInterface(&info, queues, 4, pool, pool, 0);
    setProperty("ItlwmAwdlVifRegistrationError", static_cast<uint32_t>(result), 32);
    IOLog("BE201VIF register result=0x%x\n", result);
    if (result != kIOReturnSuccess) return false;
    registered = true;
    setProperty("ItlwmAwdlVifStage", 5, 32);
    // IOSkywalkNetworkBSDClient matches on the published service, so the BSD interface
    // cannot exist before this. Native publishes here too, then sets the running state.
    vifStep(ownerController, "publish");
    registerService();
    return true;
}

void AirportItlwmAWDLInterface::markDown()
{
    vifStep(ownerController, "running-state");
    // Neither IFF_RUNNING nor a successful wireless link is advertised.
    IO80211VirtualInterface::setRunningState(false);
}

void AirportItlwmAWDLInterface::inputActionFrame(const uint8_t *frame, size_t length,
    uint8_t channel, int rssi, uint32_t device_us)
{
    if (!started || !registered || !linkActive || !queueLoop || !queueLoop->inGate() ||
        !AirportItlwm::awdlVifRxAllowed())
        return;
    if (frame && length && (frame[0] & 0x0c) == 0x08) {
        inputDataFrame(frame, length);
        return;
    }
    // The monitor also passes other management frames.
    if (!frame || !length || frame[0] != 0xd0)
        return;
    // One nearby peer's MIF, to compare its TLVs with this Mac's. May name services; stays in the registry.
    if (!peerMifSaved && rssi >= IWX_AWDL_PEER_MIN_RSSI && length > 24 + 7 && frame[24 + 6] == 3) {
        peerMifSaved = true;
        setProperty("ItlwmAwdlPeerMifSample", const_cast<uint8_t *>(frame), static_cast<unsigned>(length < 900 ? length : 900));
    }
    iwx_awdl_rx_header header;
    if (!iwx_awdl_rx_prepare(frame, length, channel, rssi, device_us, &header)) {
        setProperty("ItlwmAwdlNativeRxInvalid", ++nativeRxInvalid, 32);
        // Fixed action fields only: no addresses and no TLVs.
        if (length >= 24 + 8)
            setProperty("ItlwmAwdlNativeRxLastBad", const_cast<uint8_t *>(frame + 24), 8);
        return;
    }
    auto *nativePool = getMgmtFramePool();
    auto *buffer = nativePool ? nativePool->getBuffer() : nullptr;
    if (!buffer) {
        setProperty("ItlwmAwdlNativeRxNoBuffer", ++nativeRxNoBuffer, 32);
        return;
    }
    const size_t bodyLength = length - 24;
    if (buffer->getCapacity() < bodyLength ||
        buffer->writeBytes(0, frame + 24, bodyLength) != bodyLength) {
        buffer->returnBuffer();
        setProperty("ItlwmAwdlNativeRxNoBuffer", ++nativeRxNoBuffer, 32);
        return;
    }
    buffer->setLength(bodyLength);
    // Native bpfTapInput transfers buffer ownership to actionFrameInput (which can queue it).
    // It copies the 72-byte metadata when queuing. Never return/access buffer after this call.
    // Native peer processing can call back into the driver. Keep this object alive
    // even if a reentrant controller stop detaches the child while the native call runs.
    retain();
    bpfTapInput(buffer, 0xc, &header, sizeof(header));
    const auto submitted = ++nativeRxSubmitted;
    if (submitted == 1 || !(submitted & 31))
        setProperty("ItlwmAwdlNativeRxSubmitted", submitted, 32);
    release();
}

void AirportItlwmAWDLInterface::removeQueuesFromWorkLoop()
{
    if (awTimer) {
        awTimer->cancelTimeout();
        queueLoop->removeEventSource(awTimer);
        OSSafeReleaseNULL(awTimer);
    }
    if (linkTimer) {
        linkTimer->cancelTimeout();
        queueLoop->removeEventSource(linkTimer);
        OSSafeReleaseNULL(linkTimer);
    }
    while (queuesOnLoop) {
        --queuesOnLoop;
        queueLoop->removeEventSource(reinterpret_cast<IOEventSource *>(queues[queuesOnLoop]));
    }
    OSSafeReleaseNULL(queueLoop);
}

void AirportItlwmAWDLInterface::releaseQueueResources()
{
    for (int i = 3; i >= 0; --i) OSSafeReleaseNULL(queues[i]);
    OSSafeReleaseNULL(pool);
}

void AirportItlwmAWDLInterface::stop(IOService *provider)
{
    dataActive = false;
    if (linkTimer)
        linkTimer->cancelTimeout();
    if (awTimer)
        awTimer->cancelTimeout();
    // Delivered messages read this pointer from a timer, so it must not outlive the object.
    if (ownerController && ownerController->getAwdlInterface() == this)
        ownerController->setAwdlInterface(nullptr);
    // Native base stop deregisters the BSD/network interface and quiesces native queues.
    // Take them off the work loop and drop our references only after that.
    if (started) {
        started = false;
        IO80211VirtualInterface::stop(provider);
    }
    registered = false;
    removeQueuesFromWorkLoop();
    releaseQueueResources();
}

void AirportItlwmAWDLInterface::free()
{
    // Reached with native state only after controller stop terminated this object.
    removeQueuesFromWorkLoop();
    releaseQueueResources();
    super::free();
}

const char *AirportItlwmAWDLInterface::getBSDNamePrefix() { return "awdl"; }

void AirportItlwmAWDLInterface::recordRequest(unsigned id)
{
    // Polling the last id misses requests, and log lines from this driver do not reach the stream.
    const uint32_t count = __atomic_add_fetch(&requestCount, 1U, __ATOMIC_RELAXED);
    setProperty("ItlwmAwdlRequests", count, 32);
    if (id >= 500 && id - 500 < sizeof(requestCounts) / sizeof(requestCounts[0])) {
        const uint32_t seen = __atomic_add_fetch(&requestCounts[id - 500], 1U, __ATOMIC_RELAXED);
        // The manager repeats its requests; a new id or every 64th total keeps the registry current.
        if (seen == 1 || (count & 63) == 0)
            setProperty("ItlwmAwdlRequestCounts", requestCounts, sizeof(requestCounts));
    }
    if (count <= sizeof(requestLog) / sizeof(requestLog[0])) {
        requestLog[count - 1] = static_cast<uint16_t>(id);
        setProperty("ItlwmAwdlRequestLog", requestLog, static_cast<unsigned>(count * sizeof(requestLog[0])));
    }
}

IOReturn AirportItlwmAWDLInterface::unsupported(unsigned id)
{
    recordRequest(id);
    setProperty("ItlwmAwdlUnsupportedLast", id, 32);
    setProperty("ItlwmAwdlUnsupportedRequests", __atomic_add_fetch(&unsupportedCount, 1U, __ATOMIC_RELAXED), 32);
    return kIOReturnUnsupported;
}

IOReturn AirportItlwmAWDLInterface::acceptSet(unsigned id)
{
    if (!AirportItlwm::awdlVifAcceptSets())
        return unsupported(id);
    recordRequest(id);
    return kIOReturnSuccess;
}

IOReturn AirportItlwmAWDLInterface::acceptSet(unsigned id, const void *data, size_t length)
{
    const IOReturn result = acceptSet(id);
    if (result == kIOReturnSuccess && data && length) {
        char name[32];
        snprintf(name, sizeof(name), "ItlwmAwdlPayload%u", id);
        setProperty(name, const_cast<void *>(data), static_cast<unsigned>(length));
    }
    return result;
}

UInt32 AirportItlwmAWDLInterface::txSubmitAction(OSObject *owner, IOSkywalkTxSubmissionQueue *, IOSkywalkPacket *const *packets, UInt32 count, void *)
{
    auto *self = OSDynamicCast(AirportItlwmAWDLInterface, owner);
    return self ? self->transmit(packets, count) : 0;
}

// The return value is how many packets were taken; 0 stalls the queue until the next dequeue request.
UInt32 AirportItlwmAWDLInterface::transmit(IOSkywalkPacket *const *packets, UInt32 count)
{
    if (!dataActive || !started || !registered || !packets || !count)
        return 0;
    auto *controller = static_cast<AirportItlwm *>(ownerController);
    UInt32 taken = 0;
    for (; taken < count; ++taken) {
        const uint8_t *eth = be201PacketBase(packets[taken]) + be201PacketOffset(packets[taken]);
        if (be201PacketLength(packets[taken]) > 1514) {
            // Segmentation offload is off; a larger packet means it did not stay off.
            ++dataTxDropped;
            setProperty("ItlwmAwdlDataTxOversize", ++dataTxOversize, 32);
            continue;
        }
        // A run of packets to one peer goes out as one frame when the peer can take that.
        if (taken + 1 < count && be201PacketLength(packets[taken]) >= 14 && controller->awdlAmsduReady(eth)) {
            const uint8_t *eths[IWX_AWDL_AMSDU_MAX_FRAMES];
            size_t lengths[IWX_AWDL_AMSDU_MAX_FRAMES];
            unsigned run = 0;
            size_t bytes = 26;
            while (run < IWX_AWDL_AMSDU_MAX_FRAMES && taken + run < count) {
                IOSkywalkPacket *next = packets[taken + run];
                const size_t length = be201PacketLength(next);
                const uint8_t *data = be201PacketBase(next) + be201PacketOffset(next);
                bytes = ((bytes - 26 + 3) & ~size_t(3)) + 26 + 16 + length;
                if (length < 14 || length > 1514 || bytes > IWX_AWDL_AMSDU_MAX_BYTES || memcmp(data, eth, 6))
                    break;
                eths[run] = data;
                lengths[run] = length;
                ++run;
            }
            if (run >= 2) {
                const IOReturn grouped = controller->sendAWDLAmsdu(eths, lengths, run);
                if (grouped == kIOReturnBusy) {
                    txWaiting = true;
                    break;
                }
                if (grouped == kIOReturnSuccess) {
                    dataTx += run;
                    taken += run - 1;
                    continue;
                }
            }
        }
        const IOReturn sent = controller->sendAWDLData(eth, be201PacketLength(packets[taken]));
        if (sent == kIOReturnBusy) {
            // The rest stay in the ring (legacyDequeue on 24G824 advances by the count returned).
            txWaiting = true;
            break;
        }
        if (sent == kIOReturnSuccess)
            ++dataTx;
        else
            ++dataTxDropped;
    }
    if (taken)
        be201TxCompEnqueue(queues[1], packets, taken, 0);
    if (!(++dataTxCalls & 63)) {
        setProperty("ItlwmAwdlDataTx", dataTx, 32);
        setProperty("ItlwmAwdlDataTxDropped", dataTxDropped, 32);
    }
    return taken;
}

// Option bit 0 only signals the queue's event source, so this is safe from a completion.
void AirportItlwmAWDLInterface::txRoom()
{
    if (!dataActive || !started || !registered || !txWaiting)
        return;
    txWaiting = false;
    be201TxSubRequestDequeue(queues[0], nullptr, 1);
}

void AirportItlwmAWDLInterface::inputDataFrame(const uint8_t *frame, size_t length)
{
    if (!dataActive || !started || !registered || !pool)
        return;
    const size_t n = iwx_awdl_data_to_ether(frame, length, address.octet, rxEthernet, sizeof(rxEthernet));
    if (!n) {
        // The first few, headers and LLC only, tell a framing mismatch from anything else.
        if (++dataRxBad <= 16)
            setProperty("ItlwmAwdlDataRxLastBad", const_cast<uint8_t *>(frame), static_cast<unsigned>(length < 48 ? length : 48));
        setProperty("ItlwmAwdlDataRxBad", dataRxBad, 32);
        return;
    }
    // A high share of retries means the peer is not hearing an ACK from this address.
    if (frame[1] & 0x08)
        ++dataRxRetry;
    if (companion) {
        const iwx_awdl_llw_route route = iwx_awdl_llw_input(&companion->ports, rxEthernet, n);
        if (route != IWX_AWDL_ROUTE_AWDL)
            companion->inputEthernet(rxEthernet, n);
        if (route == IWX_AWDL_ROUTE_LLW)
            return;
    }
    IOSkywalkPacket *packet = nullptr;
    // Option bit 0 is no sleep: this runs holding the Wi-Fi work loop.
    if (be201PoolAllocate(pool, &packet, 1) != kIOReturnSuccess || !packet) {
        setProperty("ItlwmAwdlDataRxDropped", ++dataRxDropped, 32);
        return;
    }
    // A pool packet has no buffer until prepared (1.1.32 panicked here). Direction 2, as refillRxRing.
    // No source queue: completion would call its packetCompletion, which panics on these queues.
    if (be201PacketPrepare(packet, nullptr, 2, 0) != kIOReturnSuccess) {
        be201PoolDeallocate(pool, packet);
        setProperty("ItlwmAwdlDataRxDropped", ++dataRxDropped, 32);
        return;
    }
    memcpy(be201PacketBase(packet) + be201PacketOffset(packet), rxEthernet, n);
    if (be201PacketSetLength(packet, static_cast<UInt32>(n)) != kIOReturnSuccess) {
        be201PoolDeallocate(pool, packet);
        setProperty("ItlwmAwdlDataRxDropped", ++dataRxDropped, 32);
        return;
    }
    const IOReturn enqueued = be201RxCompEnqueue(queues[3], &packet, 1, 0);
    if (enqueued != kIOReturnSuccess) {
        be201PoolDeallocate(pool, packet);
        setProperty("ItlwmAwdlDataRxEnqueueResult", static_cast<unsigned long long>(enqueued), 32);
        setProperty("ItlwmAwdlDataRxDropped", ++dataRxDropped, 32);
        return;
    }
    if (++dataRx <= 64 || !(dataRx & 63)) {
        setProperty("ItlwmAwdlDataRx", dataRx, 32);
        setProperty("ItlwmAwdlDataRxRetry", dataRxRetry, 32);
    }
}

// Native enableDatapath enables its completion queues and transmit queue, requests a dequeue, and
// leaves receive submission alone: a netif nexus takes packets this driver allocates.
void AirportItlwmAWDLInterface::enableData()
{
    if (dataActive || !queues[0] || !queues[1] || !queues[3])
        return;
    // Firmware finishes what the family advertises on native hardware; nothing does here.
    setProperty("ItlwmAwdlOffloadResult", static_cast<unsigned long long>(
        ifnet_set_offload(reinterpret_cast<ifnet_t>(getBSDInterface()), static_cast<ifnet_offload_t>(0))), 32);
    be201TxCompEnable(queues[1]);
    be201RxCompEnable(queues[3]);
    be201TxSubEnable(queues[0]);
    dataActive = true;
    be201TxSubRequestDequeue(queues[0], nullptr, 0);
    reportLinkStatus(3, 0x80);
    ifnet_set_flags(reinterpret_cast<ifnet_t>(getBSDInterface()), IFF_RUNNING, IFF_RUNNING);
    IO80211VirtualInterface::setRunningState(true);
    setProperty("ItlwmAwdlDataReady", true);
}

void AirportItlwmAWDLInterface::takeTemplate(bool mif, const uint8_t *request, size_t lengthOffset, size_t pointerOffset)
{
    uint32_t length = 0;
    const uint8_t *payload = nullptr;
    memcpy(&length, request + lengthOffset, sizeof(length));
    memcpy(&payload, request + pointerOffset, sizeof(payload));
    // The length field is 16 bits on the MI request.
    if (mif)
        length &= 0xffff;
    if (!payload || !length || length > 2048) {
        setProperty("ItlwmAwdlTemplateBad", ++templateBad, 32);
        return;
    }
    // Keep what the system asked to send: the next stage reads it even with transmit off.
    setProperty(mif ? "ItlwmAwdlTemplateMif" : "ItlwmAwdlTemplatePsf", const_cast<uint8_t *>(payload), length);
    if (AirportItlwm::awdlVifTxAllowed() && queueLoop && queueLoop->inGate()) {
        const IOReturn result = static_cast<AirportItlwm *>(ownerController)->setAWDLTemplate(mif, payload, length);
        if (result != kIOReturnSuccess)
            setProperty("ItlwmAwdlTemplateBad", ++templateBad, 32);
    }
}

void AirportItlwmAWDLInterface::remember(unsigned slot, const void *data, size_t length)
{
    if (slot >= kReadSlots || !data || length > sizeof(readBack[0].bytes))
        return;
    memcpy(readBack[slot].bytes, data, length);
    readBack[slot].length = static_cast<uint16_t>(length);
}

// The manager reprograms anything it reads back differently from what it set.
IOReturn AirportItlwmAWDLInterface::recall(unsigned slot, void *data, size_t length, unsigned id)
{
    if (slot >= kReadSlots || !readBack[slot].length || readBack[slot].length != length)
        return unsupported(id);
    if (!data)
        return kIOReturnBadArgument;
    recordRequest(id);
    memcpy(data, readBack[slot].bytes, length);
    return kIOReturnSuccess;
}

void AirportItlwmAWDLInterface::linkTimerFired(OSObject *owner, IOTimerEventSource *)
{
    auto *self = OSDynamicCast(AirportItlwmAWDLInterface, owner);
    if (!self || !self->started || !self->registered || self->linkActive)
        return;
    self->linkActive = true;
    // The family cached capabilities at boot, before arming, and configure reads that copy.
    static_cast<AirportItlwm *>(self->ownerController)->reloadAWDLCapabilities();
    vifStep(self->ownerController, "link-up");
    // Native concrete does this from setInterfaceEnable. The base brings the link up and that
    // starts the family's AWDL manager. The native reportLinkStatus is left out: no IFF_RUNNING.
    const SInt32 result = self->IO80211VirtualInterface::setInterfaceEnable(true);
    self->setProperty("ItlwmAwdlLinkResult", static_cast<uint32_t>(result), 32);
    self->setProperty("ItlwmAwdlLinkState", static_cast<uint32_t>(self->IO80211VirtualInterface::linkState()), 32);
    vifStep(self->ownerController, "link-done");
    if (AirportItlwm::awdlVifRadioAllowed() && result == kIOReturnSuccess) {
        auto controller = static_cast<AirportItlwm *>(self->ownerController);
        const IOReturn queued = controller->requestAWDLMonitor(self->address);
        self->setProperty("ItlwmAwdlNativeMonitorQueueResult", static_cast<uint32_t>(queued), 32);
        if (queued == kIOReturnSuccess && AirportItlwm::awdlVifTxAllowed())
            self->setProperty("ItlwmAwdlNativeTxResult", static_cast<uint32_t>(controller->enableAWDLTransmit()), 32);
        if (queued == kIOReturnSuccess && AirportItlwm::awdlVifDataAllowed())
            self->enableData();
    }
    if (self->awTimer && AirportItlwm::awdlVifAwAllowed())
        self->awTimer->setTimeoutUS(kAwSlotUs);
}

void AirportItlwmAWDLInterface::awTimerFired(OSObject *owner, IOTimerEventSource *)
{
    auto *self = OSDynamicCast(AirportItlwmAWDLInterface, owner);
    if (!self || !self->started || !self->registered || !self->linkActive)
        return;
    // Room can return without a completion on this queue: a full ring elsewhere clears on its own.
    self->txRoom();
    auto *awdlController = static_cast<AirportItlwm *>(self->ownerController);
    awdlController->setAWDLOwnQueue(AirportItlwm::awdlOwnQueueWanted(), AirportItlwm::awdlTxAggWanted(), AirportItlwm::awdlOwnFixWanted());
    // Layout read from monitorTimeline and logAWStart on 24G824; the channel's flags and any
    // other fields the firmware fills are unverified.
    uint8_t event[0x28] = {};
    // Firmware would count AWs from the master it follows. Take the number and phase from the cluster
    // heard: free running, the manager logged a constant offset and rising sync errors against the phone.
    uint16_t heardSeq = 0;
    uint32_t heardWait = 0;
    uint32_t timeout = kAwSlotUs;
    if (static_cast<AirportItlwm *>(self->ownerController)->awdlSyncNext(&heardSeq, &heardWait)) {
        // heardSeq starts the next window, so the one running now is a step earlier.
        const uint32_t current = uint16_t(heardSeq - self->awSteps);
        self->awNumber = current - current % self->awSteps;
        timeout = heardWait < kAwMinSlotUs ? heardWait + kAwSlotUs : heardWait;
        if (timeout > kAwMaxSlotUs)
            timeout = kAwMaxSlotUs;
        if (!(++self->awAligned & 255))
            self->setProperty("ItlwmAwdlAwAligned", self->awAligned, 32);
    }
    const uint32_t number = self->awNumber;
    self->awNumber += self->awSteps;
    const uint32_t slot = (number / self->awSteps) % 16;
    {
        // This Mac's own sequence, as the family set it: the slot starting now, the run of that channel's slots that
        // starts here (0 inside a run), and the 5 GHz channel the sequence uses. On a hotspot on 149 it was
        // 149 in slots 0, 2 and 10, 6 in slot 8, the rest 0.
        const uint32_t chan = self->awChannels[slot] <= 255 ? self->awChannels[slot] : 0;
        uint32_t run = 0;
        if (chan && self->awChannels[(slot + 15) % 16] != chan)
            while (run < 16 && self->awChannels[(slot + run) % 16] == chan)
                ++run;
        else if (chan) {
            // One channel in every slot has no run start: a slot in four, as the AP keeps three quarters.
            bool same = true;
            for (unsigned i = 0; i < 16; ++i)
                same &= self->awChannels[i] == chan;
            run = same && !(slot % 4) ? 1 : 0;
        }
        // The first two different 5 GHz channels, low byte first: the HAL takes the one the AP is not on.
        uint32_t seq5 = 0;
        for (unsigned i = 0; i < 16; ++i) {
            const uint32_t c5 = self->awChannels[i];
            if (c5 < 36 || c5 > 177 || c5 == (seq5 & 0xff))
                continue;
            if (!seq5) {
                seq5 = c5;
            } else {
                seq5 |= c5 << 8;
                break;
            }
        }
        // Mode 4 looks ahead: the 5 GHz channel of the next slot that has one, from this slot on.
        uint32_t next5 = 0;
        for (unsigned k = 0; k < 16 && !next5; ++k) {
            const uint32_t c5 = self->awChannels[(slot + k) % 16];
            if (c5 >= 36 && c5 <= 177)
                next5 = c5;
        }
        awdlController->setAWDLSlot(chan, run | (next5 << 8), seq5);
        bool holdTest = false, amsduTest = false;
        uint32_t phy2Test = 0, teTest = 0;
        AirportItlwm::awdlRadioTest(&holdTest, &phy2Test, &teTest, &amsduTest);
        awdlController->setAWDLRadioTest(holdTest, phy2Test, teTest, amsduTest);
    }
    uint64_t now;
    clock_get_uptime(&now);
    absolutetime_to_nanoseconds(now, &now);
    const uint32_t startUs = static_cast<uint32_t>(now / 1000);
    const uint32_t version = 1;
    memcpy(event, &number, sizeof(number));
    memcpy(event + 0x0e, &self->address, sizeof(self->address));
    memcpy(event + 0x14, &startUs, sizeof(startUs));
    memcpy(event + 0x18, &version, sizeof(version));
    memcpy(event + 0x1c, &self->awChannels[slot], sizeof(uint32_t));
    memcpy(event + 0x20, &self->awFlags[slot], sizeof(uint32_t));
    self->postMessage(kAwStartMessage, event, sizeof(event), false);
    if ((slot == 0) && !(number % (self->awSteps * 16 * 16)))
        self->setProperty("ItlwmAwdlAwStarts", number / self->awSteps + 1, 32);
    self->awTimer->setTimeoutUS(timeout);
}

IOReturn AirportItlwmAWDLInterface::enable(UInt) { return unsupported(1000); }
SInt32 AirportItlwmAWDLInterface::setInterfaceEnable(bool value) { return value ? unsupported(1001) : kIOReturnSuccess; }
SInt32 AirportItlwmAWDLInterface::setRunningState(bool value)
{
    if (!value)
        return IO80211VirtualInterface::setRunningState(false);
    if (dataActive)
        return IO80211VirtualInterface::setRunningState(true);
    // Called from the BSD client's ioctl handler, which sets IFF_RUNNING when this returns success.
    if (linkTimer && !linkRequested && AirportItlwm::awdlVifLinkAllowed()) {
        linkRequested = true;
        linkTimer->setTimeoutMS(1);
    }
    return unsupported(1002);
}
IO80211LinkState AirportItlwmAWDLInterface::linkState() { return linkActive ? IO80211VirtualInterface::linkState() : kIO80211NetworkLinkDown; }
bool AirportItlwmAWDLInterface::setLinkState(IO80211LinkState state, unsigned options) {
    recordRequest(state == kIO80211NetworkLinkUp ? 1004 : 1005);
    return (linkActive || state == kIO80211NetworkLinkDown) && IO80211VirtualInterface::setLinkState(state, options);
}
bool AirportItlwmAWDLInterface::setLinkState(IO80211LinkState state, unsigned options, bool wait, unsigned timeout) {
    return (linkActive || state == kIO80211NetworkLinkDown) && IO80211SkywalkInterface::setLinkState(state, options, wait, timeout);
}
IOReturn AirportItlwmAWDLInterface::setMacAddress(ether_addr &) { return unsupported(1003); }
IOReturn AirportItlwmAWDLInterface::getSSID(apple80211_ssid_data *data) { return unsupported(500); }
IOReturn AirportItlwmAWDLInterface::getCHANNEL(apple80211_channel_data *data) { return unsupported(501); }
IOReturn AirportItlwmAWDLInterface::getBSSID(apple80211_bssid_data *data) { return unsupported(502); }
IOReturn AirportItlwmAWDLInterface::getSTATE(apple80211_state_data *data) { return unsupported(503); }
IOReturn AirportItlwmAWDLInterface::getAWDL_SYNC_PARAMS(apple80211_awdl_sync_params *data) { return recall(kReadSyncParams, data, sizeof(*data), 504); }
IOReturn AirportItlwmAWDLInterface::getAWDL_SYNC_ENABLED(apple80211_awdl_sync_enabled *data)
{
    if (!data) return kIOReturnBadArgument;
    if (readBack[kReadSyncEnabled].length == sizeof(*data)) { memcpy(data, readBack[kReadSyncEnabled].bytes, sizeof(*data)); return kIOReturnSuccess; }
    memset(data, 0, sizeof(*data));
    data->version = APPLE80211_VERSION;
    return kIOReturnSuccess;
}
IOReturn AirportItlwmAWDLInterface::getAWDL_EXTENSION_STATE_MACHINE_PARAMETERS(apple80211_awdl_extension_state_machine_parameter *data) { return unsupported(506); }
IOReturn AirportItlwmAWDLInterface::getAWDL_ELECTION_ID(apple80211_awdl_election_id *data) { return unsupported(507); }
IOReturn AirportItlwmAWDLInterface::getAWDL_ELECTION_METRIC(apple80211_awdl_election_metric *data) { return unsupported(508); }
IOReturn AirportItlwmAWDLInterface::getAWDL_SYNCHRONIZATION_CHANNEL_SEQUENCE(apple80211_awdl_sync_channel_sequence *data) { return recall(kReadChannelSequence, data, sizeof(*data), 509); }
IOReturn AirportItlwmAWDLInterface::getPEER_CACHE_MAXIMUM_SIZE(apple80211_peer_cache_maximum_size *data) { return unsupported(510); }
IOReturn AirportItlwmAWDLInterface::getAWDL_MASTER_CHANNEL(apple80211_awdl_master_channel *data) { return recall(kReadMasterChannel, data, sizeof(*data), 511); }
IOReturn AirportItlwmAWDLInterface::getAWDL_SYNC_STATE(apple80211_awdl_sync_state *data)
{
    if (!data) return kIOReturnBadArgument;
    if (readBack[kReadSyncState].length == sizeof(*data)) { memcpy(data, readBack[kReadSyncState].bytes, sizeof(*data)); return kIOReturnSuccess; }
    memset(data, 0, sizeof(*data));
    data->version = APPLE80211_VERSION;
    return kIOReturnSuccess;
}
IOReturn AirportItlwmAWDLInterface::getAWDL_ELECTION_RSSI_THRESHOLDS(apple80211_awdl_election_rssi_thresholds *data) { return unsupported(513); }
IOReturn AirportItlwmAWDLInterface::getAWDL_PRESENCE_MODE(apple80211_awdl_presence_mode *data) { return unsupported(514); }
IOReturn AirportItlwmAWDLInterface::getAWDL_ELECTION_PARAMS(apple80211_awdl_election_params *data) { return unsupported(515); }
IOReturn AirportItlwmAWDLInterface::getAWDL_DEVICE_CAPABILITIES(apple80211_awdl_device_capabilities *data) { return unsupported(516); }
IOReturn AirportItlwmAWDLInterface::getAWDL_SECONDARY_MASTER_CHANNEL(apple80211_awdl_secondary_master_channel *data) { return recall(kReadSecondaryMaster, data, sizeof(*data), 517); }
IOReturn AirportItlwmAWDLInterface::getAWDL_AF_TX_MODE(apple80211_awdl_af_tx_mode *data) { return recall(kReadAfTxMode, data, sizeof(*data), 518); }
IOReturn AirportItlwmAWDLInterface::getAWDL_MIN_RATE(apple80211_awdl_min_rate *data) { return unsupported(519); }
IOReturn AirportItlwmAWDLInterface::getAWDL_ENCRYPTION_TYPE(apple80211_encrypt *data) { return unsupported(520); }
IOReturn AirportItlwmAWDLInterface::getAWDL_TXCAL_PERIOD(apple80211_awdl_txcal_period *data) { return unsupported(521); }
IOReturn AirportItlwmAWDLInterface::getAWDL_DEV_STATS(apple80211_awdl_dev_stats *data) { return unsupported(522); }
IOReturn AirportItlwmAWDLInterface::getAWDL_DFSP_CONFIG(apple80211_awdl_dfsp_config *data) { return unsupported(523); }
IOReturn AirportItlwmAWDLInterface::getAWDL_CCA(apple80211_awdl_cca *data) { return unsupported(524); }
IOReturn AirportItlwmAWDLInterface::getAWDL_AF_SECONDARY_PAYLOAD_CAPABILITIES(apple80211_awdl_cap *data) { return unsupported(525); }
IOReturn AirportItlwmAWDLInterface::getLLW_PARAMS(apple80211_llw_params *data) { return unsupported(526); }
IOReturn AirportItlwmAWDLInterface::setSSID(apple80211_ssid_data *data) { return acceptSet(527); }
IOReturn AirportItlwmAWDLInterface::setCHANNEL(apple80211_channel_data *data) { return acceptSet(528); }
IOReturn AirportItlwmAWDLInterface::setAWDL_SYNC_PARAMS(apple80211_awdl_sync_params *data)
{
    const IOReturn result = acceptSet(529, data, sizeof(*data));
    if (result == kIOReturnSuccess) remember(kReadSyncParams, data, sizeof(*data));
    return result;
}
IOReturn AirportItlwmAWDLInterface::setAWDL_SYNC_ENABLED(apple80211_awdl_sync_enabled *data)
{
    const IOReturn result = acceptSet(530, data, sizeof(*data));
    if (result == kIOReturnSuccess) remember(kReadSyncEnabled, data, sizeof(*data));
    return result;
}
IOReturn AirportItlwmAWDLInterface::setAWDL_EXTENSION_STATE_MACHINE_PARAMETERS(apple80211_awdl_extension_state_machine_parameter *data) { return acceptSet(531); }
IOReturn AirportItlwmAWDLInterface::setAWDL_ELECTION_ID(apple80211_awdl_election_id *data) { return acceptSet(532); }
IOReturn AirportItlwmAWDLInterface::setAWDL_BSSID(apple80211_awdl_bssid *data) { return acceptSet(533, data, sizeof(*data)); }
IOReturn AirportItlwmAWDLInterface::setAWDL_ELECTION_METRIC(apple80211_awdl_election_metric *data) { return acceptSet(534); }
IOReturn AirportItlwmAWDLInterface::setAWDL_SYNCHRONIZATION_CHANNEL_SEQUENCE(apple80211_awdl_sync_channel_sequence *data)
{
    const IOReturn result = acceptSet(535, data, sizeof(*data));
    if (result == kIOReturnSuccess && data) {
        // As seen from the manager: a 12-byte header, then {version, channel, flags} per slot.
        const uint8_t *raw = reinterpret_cast<const uint8_t *>(data);
        for (unsigned i = 0; i < 16; ++i) {
            memcpy(&awChannels[i], raw + 12 + 12 * i + 4, sizeof(uint32_t));
            memcpy(&awFlags[i], raw + 12 + 12 * i + 8, sizeof(uint32_t));
        }
        // Observed 3: each channel lasts four AWs.
        awSteps = raw[7] < 8 ? raw[7] + 1 : 4;
        remember(kReadChannelSequence, data, sizeof(*data));
    }
    return result;
}
IOReturn AirportItlwmAWDLInterface::setAWDL_MASTER_CHANNEL(apple80211_awdl_master_channel *data)
{
    const IOReturn result = acceptSet(536, data, sizeof(*data));
    if (result == kIOReturnSuccess) remember(kReadMasterChannel, data, sizeof(*data));
    return result;
}
IOReturn AirportItlwmAWDLInterface::setAWDL_SYNC_STATE(apple80211_awdl_sync_state *data)
{
    const IOReturn result = acceptSet(537, data, sizeof(*data));
    if (result == kIOReturnSuccess) remember(kReadSyncState, data, sizeof(*data));
    return result;
}
IOReturn AirportItlwmAWDLInterface::setAWDL_ELECTION_RSSI_THRESHOLDS(apple80211_awdl_election_rssi_thresholds *data) { return acceptSet(538); }
IOReturn AirportItlwmAWDLInterface::setAWDL_PRESENCE_MODE(apple80211_awdl_presence_mode *data) { return acceptSet(539); }
// The family waits for event 51 before real-time traffic: handleEnsembleTrafficReg, "Peer cache operation failed".
// Layout from IO80211Peer::fillInCacheParams and handleCacheControlMessages on 24G824: operation at +4, address at +8.
IOReturn AirportItlwmAWDLInterface::setPEER_CACHE_CONTROL(apple80211_peer_cache_control *data)
{
    const IOReturn result = acceptSet(540);
    // Off by default: on 1.1.45 the family cycled add and delete, and this Mac stopped sending AirDrop.
    if (result == kIOReturnSuccess && data && AirportItlwm::awdlCacheOn()) {
        const auto *raw = reinterpret_cast<const uint8_t *>(data);
        uint32_t op = 0;
        memcpy(&op, raw + 4, sizeof(op));
        static_cast<AirportItlwm *>(ownerController)->awdlPeerCache(raw + 8, op);
    }
    return result;
}

void AirportItlwmAWDLInterface::peerCacheDone(const uint8_t *mac, bool added)
{
    if (!started || !registered || !linkActive)
        return;
    uint8_t event[IWX_AWDL_CACHE_EVENT_LEN] = {};
    const uint32_t version = 1, op = added ? IWX_AWDL_CACHE_EVENT_ADDED : IWX_AWDL_CACHE_EVENT_DELETED;
    memcpy(event, &version, sizeof(version));
    memcpy(event + 4, &op, sizeof(op));
    memcpy(event + 8, mac, 6);
    postMessage(IWX_AWDL_CACHE_EVENT, event, sizeof(event), false);
}
IOReturn AirportItlwmAWDLInterface::setAWDL_OOB_REQUEST(apple80211_awdl_oob_request *data)
{
    // Unicast master indication from sendUnicastMI: address at +4, length at +0x28, pointer at +0x30.
    // The family then waits for the ACK result, event 69, and fails the session without it.
    const IOReturn result = acceptSet(541);
    if (result != kIOReturnSuccess || !data || !AirportItlwm::awdlUmiOn() || !queueLoop || !queueLoop->inGate())
        return result;
    const uint8_t *raw = reinterpret_cast<const uint8_t *>(data);
    uint16_t length = 0;
    const uint8_t *payload = nullptr;
    memcpy(&length, raw + 0x28, sizeof(length));
    memcpy(&payload, raw + 0x30, sizeof(payload));
    static_cast<AirportItlwm *>(ownerController)->sendAWDLUmi(raw + 4, payload, length);
    return result;
}

void AirportItlwmAWDLInterface::umiDone(const uint8_t *mac, bool acked)
{
    if (!started || !registered || !mac)
        return;
    uint8_t event[IWX_AWDL_UMI_EVENT_LEN] = {};
    memcpy(event, mac, 6);
    event[6] = acked ? 0 : 1;
    postMessage(IWX_AWDL_UMI_EVENT, event, sizeof(event), false);
}
IOReturn AirportItlwmAWDLInterface::setAWDL_SYNC_FRAME_TEMPLATE(apple80211_awdl_sync_frame_template *data)
{
    // {version, length, pointer}. On 24G824 the pointer is the caller's buffer right after it.
    const IOReturn result = acceptSet(542);
    if (result == kIOReturnSuccess && data)
        takeTemplate(false, reinterpret_cast<const uint8_t *>(data), 4, 8);
    return result;
}
IOReturn AirportItlwmAWDLInterface::setAWDL_ELECTION_PARAMS(apple80211_awdl_election_params *data) { return acceptSet(543); }
IOReturn AirportItlwmAWDLInterface::setAWDL_PEER_TRAFFIC_REGISTRATION(apple80211_awdl_peer_traffic_registration *data)
{
    // The service name says who needs AWDL; offsets as read by the native handler. The peer address stays out.
    if (data) {
        uint32_t length = 0;
        char name[64] = {};
        memcpy(&length, reinterpret_cast<const uint8_t *>(data) + 0x0c, sizeof(length));
        if (length && length < sizeof(name)) {
            memcpy(name, reinterpret_cast<const uint8_t *>(data) + 0x10, length);
            setProperty("ItlwmAwdlTrafficRegistrationName", name);
        }
    }
    return acceptSet(544);
}
IOReturn AirportItlwmAWDLInterface::setAWDL_SECONDARY_MASTER_CHANNEL(apple80211_awdl_secondary_master_channel *data)
{
    const IOReturn result = acceptSet(545, data, sizeof(*data));
    if (result == kIOReturnSuccess) remember(kReadSecondaryMaster, data, sizeof(*data));
    return result;
}
IOReturn AirportItlwmAWDLInterface::setAWDL_AF_TX_MODE(apple80211_awdl_af_tx_mode *data)
{
    const IOReturn result = acceptSet(546, data, sizeof(*data));
    if (result == kIOReturnSuccess) remember(kReadAfTxMode, data, sizeof(*data));
    return result;
}
IOReturn AirportItlwmAWDLInterface::setAWDL_MIN_RATE(apple80211_awdl_min_rate *data) { return acceptSet(547); }
IOReturn AirportItlwmAWDLInterface::setAWDL_ENCRYPTION_KEYS(apple80211_key *data) { return acceptSet(548); }
IOReturn AirportItlwmAWDLInterface::setAWDL_ENCRYPTION_TYPE(apple80211_encrypt *data) { return acceptSet(549); }
IOReturn AirportItlwmAWDLInterface::setAWDL_OOB_AUTO_REQUEST(apple80211_awdl_oob_request *data)
{
    // Native layout: address at +4, length at +0x28, pointer at +0x30 to the manager's own buffer.
    const IOReturn result = acceptSet(550);
    if (result == kIOReturnSuccess && data)
        takeTemplate(true, reinterpret_cast<const uint8_t *>(data), 0x28, 0x30);
    return result;
}
IOReturn AirportItlwmAWDLInterface::setAWDL_TXCAL_PERIOD(apple80211_awdl_txcal_period *data) { return acceptSet(551); }
IOReturn AirportItlwmAWDLInterface::setAWDL_AWDL_ADVERTISERS(awdl_peer_advert_add *data) { return acceptSet(552); }
IOReturn AirportItlwmAWDLInterface::setAWDL_DFSP_CONFIG(apple80211_awdl_dfsp_config *data) { return acceptSet(553); }
IOReturn AirportItlwmAWDLInterface::setAWDL_DFSP_UCSA_CONFIG(apple80211_awdl_dfsp_ucsa_config *data) { return acceptSet(554); }
IOReturn AirportItlwmAWDLInterface::setCOMPANION_SKYWALK_IF_CREATE(apple80211_companion_skywalk_if_create *data)
{
    // Native: operation at +4, 1 creates and 0 deletes; the BSD name goes back at +8, 16 bytes.
    if (!AirportItlwm::awdlLlwOn() || !data)
        return unsupported(555);
    recordRequest(555);
    uint8_t *raw = reinterpret_cast<uint8_t *>(data);
    uint32_t op = 0;
    memcpy(&op, raw + 4, sizeof(op));
    // It stays until the driver stops: its peer manager and work are tied to awdl0's lifetime.
    if (op == 0)
        return kIOReturnSuccess;
    if (op != 1)
        return kIOReturnBadArgument;
    return static_cast<AirportItlwm *>(ownerController)->createLowLatencyInterface(this, address, reinterpret_cast<char *>(raw + 8), 16);
}
IOReturn AirportItlwmAWDLInterface::setAWDL_OOB_SEC_PAYLOAD_REQUEST(apple80211_awdl_af_sec_payload_request *data) { return acceptSet(556); }
IOReturn AirportItlwmAWDLInterface::setLLW_PARAMS(apple80211_llw_params *data) { return acceptSet(557); }
IOReturn AirportItlwmAWDLInterface::setTX_RATE(apple80211_tx_rate *data) { return acceptSet(558); }
IOReturn AirportItlwmAWDLInterface::setP2P_COEX_PROTECTION(apple80211_p2p_coex_protection *data) { return acceptSet(559); }
IOReturn AirportItlwmAWDLInterface::setPSF_DWELL(apple80211_awdl_psf_dwell_params *data) { return acceptSet(560); }
IOReturn AirportItlwmAWDLInterface::setAWDL_CONFIG(apple80211_awdl_config *data) { return acceptSet(561); }
IOReturn AirportItlwmAWDLInterface::setAWDL_RTG_PEER_STATS_CONFIG(apple80211_rtg_peer_stats_cfg *data) { return acceptSet(562); }

#undef super
#define super IO80211VirtualInterface
OSDefineMetaClassAndStructors(AirportItlwmLowLatencyInterface, IO80211VirtualInterface)

bool AirportItlwmLowLatencyInterface::initForParent(AirportItlwm *controller, AirportItlwmAWDLInterface *parent, const ether_addr &mac)
{
    ownerController = controller;
    parentInterface = parent;
    address = mac;
    controller->setProperty("ItlwmAwdlLlwStage", 1, 32);
    // Native: role 2, id 9, and the same address as awdl0.
    if (!IO80211VirtualInterface::init(controller, &address, 2, "llw"))
        return false;
    initialized = true;
    setInterfaceId(9);
    setLowLatencyEnabled(true);
    setParentInterface(parent);
    parent->setCompanionLowLatencySkywalkInterface(this);
    return true;
}

bool AirportItlwmLowLatencyInterface::attach(IOService *provider)
{
    attached = IO80211VirtualInterface::attach(provider);
    return attached;
}

void AirportItlwmLowLatencyInterface::detach(IOService *provider)
{
    attached = false;
    IO80211VirtualInterface::detach(provider);
}

IO80211Controller *AirportItlwmLowLatencyInterface::getController() { return ownerController; }
const char *AirportItlwmLowLatencyInterface::getBSDNamePrefix() { return "llw"; }
IOReturn AirportItlwmLowLatencyInterface::enable(UInt) { return kIOReturnSuccess; }
SInt32 AirportItlwmLowLatencyInterface::setInterfaceEnable(bool) { return kIOReturnSuccess; }
IOReturn AirportItlwmLowLatencyInterface::setMacAddress(ether_addr &) { return kIOReturnUnsupported; }

UInt32 AirportItlwmLowLatencyInterface::getFeatureFlags()
{
    const UInt32 flags = IO80211SkywalkInterface::getFeatureFlags();
    if (ownerController)
        ownerController->setProperty("ItlwmAwdlLlwFeatureFlags", flags, 32);
    return flags;
}

// AppleBCMWLANLowLatencyInterface on 24G824: the base fills the parameters, then uniqueid (+0x10) points at
// 8 bytes holding the object pointer and uniqueid_len (+0x18) is 8. The Ethernet base uses the MAC address,
// which awdl0 already holds, and the BSD client then retried a busy nexus allocation for 5 s and gave up.
SInt32 AirportItlwmLowLatencyInterface::initBSDInterfaceParameters(ifnet_init_eparams *params, sockaddr_dl **ll)
{
    const SInt32 result = IO80211SkywalkInterface::initBSDInterfaceParameters(params, ll);
    if (result == 0 && params) {
        uniqueId = this;
        uint8_t *raw = reinterpret_cast<uint8_t *>(params);
        const void *id = &uniqueId;
        const uint32_t length = sizeof(uniqueId);
        memcpy(raw + 0x10, &id, sizeof(id));
        memcpy(raw + 0x18, &length, sizeof(length));
        if (ownerController)
            ownerController->setProperty("ItlwmAwdlLlwUniqueId", true);
    }
    return result;
}

SInt32 AirportItlwmLowLatencyInterface::setRunningState(bool value)
{
    if (value && !dataActive)
        return kIOReturnNotReady;
    return IO80211VirtualInterface::setRunningState(value);
}

bool AirportItlwmLowLatencyInterface::start(IOService *provider)
{
    if (started || registered)
        return false;
    IOSkywalkEthernetInterface::RegistrationInfo info = {};
    if (!initRegistrationInfo(&info, 1, sizeof(info)))
        return false;
    // Same fields as awdl0, which native createSkywalkInterface also fills for role 2.
    uint8_t *raw = info.bytes;
    const uint32_t kind = 3, version = 2, capture = 0x80, unit = 0, options = 4, mtu = 1428;
    const uint16_t hwtype = 0x40;
    const char *prefix = "llw";
    memcpy(raw + 0x0c, &kind, 4); memcpy(raw + 0x14, &version, 4);
    memcpy(raw + 0x24, &capture, 4); memcpy(raw + 0x28, &capture, 4);
    memcpy(raw + 0x30, &prefix, sizeof(prefix)); memcpy(raw + 0x38, &unit, 4);
    memcpy(raw + 0x3c, &hwtype, 2); memcpy(raw + 0x40, &options, 4);
    memcpy(raw + 0x48, &mtu, 4); memcpy(raw + 0x4c, &mtu, 4);
    memcpy(raw + 0x108, &address, sizeof(address));
    if (!IO80211VirtualInterface::start(provider))
        return false;
    started = true;
    IOSkywalkPacketBufferPool::PoolOptions po = {};
    po.packetCount = 64; po.bufferCount = 64; po.bufferSize = 2048;
    po.maxBuffersPerPacket = 1;
    po.poolFlags = AirportItlwm::awdlVifPoolFlags();
    pool = IOSkywalkPacketBufferPool::withName("BE201LLW", this, 1, &po);
    if (!pool) return false;
    queues[0] = reinterpret_cast<IOSkywalkPacketQueue *>(IOSkywalkTxSubmissionQueue::withPool(pool,64,0,this,txSubmitAction,nullptr,0));
    queues[1] = reinterpret_cast<IOSkywalkPacketQueue *>(IOSkywalkTxCompletionQueue::withPool(pool,64,0,this,txComplete,nullptr,0));
    queues[2] = reinterpret_cast<IOSkywalkPacketQueue *>(IOSkywalkRxSubmissionQueue::withPool(pool,64,1,0,this,rxSubmit,nullptr,0));
    queues[3] = reinterpret_cast<IOSkywalkPacketQueue *>(IOSkywalkRxCompletionQueue::withPool(pool,64,0,this,rxComplete,nullptr,0));
    for (auto q : queues) if (!q) return false;
    queueLoop = ownerController->getWorkLoop();
    if (!queueLoop) return false;
    queueLoop->retain();
    for (auto q : queues) {
        if (queueLoop->addEventSource(reinterpret_cast<IOEventSource *>(q)) != kIOReturnSuccess)
            return false;
        ++queuesOnLoop;
    }
    linkTimer = IOTimerEventSource::timerEventSource(this, linkTimerFired);
    if (!linkTimer)
        return false;
    if (queueLoop->addEventSource(linkTimer) != kIOReturnSuccess) {
        OSSafeReleaseNULL(linkTimer);
        return false;
    }
    const IOReturn result = registerEthernetInterface(&info, queues, 4, pool, pool, 0);
    ownerController->setProperty("ItlwmAwdlLlwRegistrationError", static_cast<uint32_t>(result), 32);
    if (result != kIOReturnSuccess) return false;
    registered = true;
    ownerController->setProperty("ItlwmAwdlLlwStage", 4, 32);
    registerService();
    return true;
}

void AirportItlwmLowLatencyInterface::bringUp()
{
    if (linkTimer && !dataActive)
        linkTimer->setTimeoutMS(1);
}

// Waits for the BSD interface, then joins awdl0 and brings data up. Never on the requester's thread:
// the attach comes from the matching thread, and the running state reaches the family.
void AirportItlwmLowLatencyInterface::linkTimerFired(OSObject *owner, IOTimerEventSource *)
{
    auto *self = OSDynamicCast(AirportItlwmLowLatencyInterface, owner);
    if (!self || !self->started || !self->registered || self->dataActive || !self->queues[0] || !self->queues[1] || !self->queues[3])
        return;
    auto *controller = self->ownerController;
    if (!self->getBSDInterface()) {
        controller->setProperty("ItlwmAwdlLlwPolls", ++self->attachPolls, 32);
        // 60 s in all, then the stage stays at 4 for the test to read.
        if (self->attachPolls < 600)
            self->linkTimer->setTimeoutMS(100);
        return;
    }
    const char *name = self->getBSDName();
    controller->setProperty("ItlwmAwdlLlwName", name ? name : "");
    controller->setProperty("ItlwmAwdlLlwStage", 5, 32);
    auto *parent = static_cast<AirportItlwm *>(controller)->awdlInterface;
    if (!parent || parent != self->parentInterface)
        return;
    self->setCompanionInterfaceId(parent->getInterfaceId());
    parent->setCompanion(self);
    self->setProperty("ItlwmAwdlOffloadResult", static_cast<unsigned long long>(
        ifnet_set_offload(reinterpret_cast<ifnet_t>(self->getBSDInterface()), static_cast<ifnet_offload_t>(0))), 32);
    be201TxCompEnable(self->queues[1]);
    be201RxCompEnable(self->queues[3]);
    be201TxSubEnable(self->queues[0]);
    self->dataActive = true;
    be201TxSubRequestDequeue(self->queues[0], nullptr, 0);
    self->reportLinkStatus(3, 0x80);
    ifnet_set_flags(reinterpret_cast<ifnet_t>(self->getBSDInterface()), IFF_RUNNING, IFF_RUNNING);
    self->IO80211VirtualInterface::setRunningState(true);
    self->setProperty("ItlwmAwdlDataReady", true);
    controller->setProperty("ItlwmAwdlLlwStage", 6, 32);
}

UInt32 AirportItlwmLowLatencyInterface::txSubmitAction(OSObject *owner, IOSkywalkTxSubmissionQueue *, IOSkywalkPacket *const *packets, UInt32 count, void *)
{
    auto *self = OSDynamicCast(AirportItlwmLowLatencyInterface, owner);
    return self ? self->transmit(packets, count) : 0;
}

UInt32 AirportItlwmLowLatencyInterface::transmit(IOSkywalkPacket *const *packets, UInt32 count)
{
    if (!dataActive || !started || !registered || !packets || !count)
        return 0;
    auto *controller = static_cast<AirportItlwm *>(ownerController);
    UInt32 taken = 0;
    for (; taken < count; ++taken) {
        const size_t length = be201PacketLength(packets[taken]);
        const uint8_t *eth = be201PacketBase(packets[taken]) + be201PacketOffset(packets[taken]);
        if (length > 1514 || !iwx_awdl_llw_output_allowed(eth, length)) {
            ++dataTxDropped;
            continue;
        }
        iwx_awdl_llw_learn(&ports, eth, length);
        const IOReturn sent = controller->sendAWDLData(eth, length);
        if (sent == kIOReturnBusy) {
            txWaiting = true;
            break;
        }
        if (sent == kIOReturnSuccess)
            ++dataTx;
        else
            ++dataTxDropped;
    }
    if (taken)
        be201TxCompEnqueue(queues[1], packets, taken, 0);
    if (!(++txCalls & 15)) {
        setProperty("ItlwmAwdlDataTx", dataTx, 32);
        setProperty("ItlwmAwdlDataTxDropped", dataTxDropped, 32);
    }
    return taken;
}

void AirportItlwmLowLatencyInterface::txRoom()
{
    if (!dataActive || !started || !registered || !txWaiting)
        return;
    txWaiting = false;
    be201TxSubRequestDequeue(queues[0], nullptr, 1);
}

void AirportItlwmLowLatencyInterface::inputEthernet(const uint8_t *eth, size_t n)
{
    if (!dataActive || !started || !registered || !pool)
        return;
    IOSkywalkPacket *packet = nullptr;
    if (be201PoolAllocate(pool, &packet, 1) != kIOReturnSuccess || !packet) {
        ++dataRxDropped;
        return;
    }
    if (be201PacketPrepare(packet, nullptr, 2, 0) != kIOReturnSuccess) {
        be201PoolDeallocate(pool, packet);
        ++dataRxDropped;
        return;
    }
    memcpy(be201PacketBase(packet) + be201PacketOffset(packet), eth, n);
    if (be201PacketSetLength(packet, static_cast<UInt32>(n)) != kIOReturnSuccess ||
        be201RxCompEnqueue(queues[3], &packet, 1, 0) != kIOReturnSuccess) {
        be201PoolDeallocate(pool, packet);
        ++dataRxDropped;
        return;
    }
    if (++dataRx <= 16 || !(dataRx & 63))
        setProperty("ItlwmAwdlDataRx", dataRx, 32);
}

void AirportItlwmLowLatencyInterface::removeQueuesFromWorkLoop()
{
    if (linkTimer) {
        linkTimer->cancelTimeout();
        queueLoop->removeEventSource(linkTimer);
        OSSafeReleaseNULL(linkTimer);
    }
    while (queuesOnLoop) {
        --queuesOnLoop;
        queueLoop->removeEventSource(reinterpret_cast<IOEventSource *>(queues[queuesOnLoop]));
    }
    OSSafeReleaseNULL(queueLoop);
}

void AirportItlwmLowLatencyInterface::releaseQueueResources()
{
    for (int i = 3; i >= 0; --i) OSSafeReleaseNULL(queues[i]);
    OSSafeReleaseNULL(pool);
}

void AirportItlwmLowLatencyInterface::stop(IOService *provider)
{
    dataActive = false;
    if (linkTimer)
        linkTimer->cancelTimeout();
    if (started) {
        started = false;
        IO80211VirtualInterface::stop(provider);
    }
    registered = false;
    removeQueuesFromWorkLoop();
    releaseQueueResources();
}

void AirportItlwmLowLatencyInterface::free()
{
    removeQueuesFromWorkLoop();
    releaseQueueResources();
    IO80211VirtualInterface::free();
}
