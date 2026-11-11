//
//  IntelBTPatcher.cpp
//  IntelBTPatcher
//
//  Created by zxystd <zxystd@foxmail.com> on 2021/2/8.
//
#define __ACIDANTHERA_MAC_SDK 2600
#include <Headers/kern_api.hpp>
#include <Headers/kern_util.hpp>
#include "BE201Defaults.hpp"
#include <Headers/plugin_start.hpp>

#include "IntelBTPatcher.hpp"
#include "ProbeReporter.hpp"
#include "NativeAddressGuard.hpp"
static bool be201NativeAddressEnabled = false;
static bool be201LEBaselineEnabled = false;
static be201address::Guard be201AddressGuard = {};
#include "AddressCompletion.hpp"
static uintptr_t be201EventPipe = 0;
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
            // Only inspect explicit non-secret capability/reset responses. No
            // extra HCI requests and no broad reads of arbitrary command data.
            const size_t capabilitySize=be201privacycap::required(prefix,count,bytes);
            if(capabilitySize && capabilitySize<=70 && capabilitySize<=bytes) {
                uint8_t capability[70]={};
                const size_t got=buffer->readBytes(0,capability,capabilitySize);
                if(got==capabilitySize)be201privacycap::event(be201PrivacyCapabilities,capability,got,bytes);
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
static void nativeAddressUSBCompleted(uint64_t ticket, IOReturn status, uint32_t bytes, bool fromCallback) {
    if (be201ProbeEnabled) {
        if (fromCallback) be201probe::increment(be201ProbeStats.nativeRPAAsyncCompletions);
        be201probe::put(be201ProbeStats.nativeRPAAsyncStatus, uint32_t(status));
        be201probe::put(be201ProbeStats.nativeRPAAsyncBytes, bytes);
        be201probe::increment(be201ProbeStats.sequence);
    }
    if (status != kIOReturnSuccess || bytes != 9) {
        be201AddressGuard.rejected(ticket); return;
    }
    if (be201AddressGuard.accepted(ticket, true, true, bytes) && be201ProbeEnabled) {
        be201probe::increment(be201ProbeStats.nativeRPAUSBAccepted);
        be201probe::increment(be201ProbeStats.sequence);
    }
}

static CIntelBTPatcher ibtPatcher;
static CIntelBTPatcher *callbackIBTPatcher = nullptr;

static const char *bootargOff[] {
    "-ibtcompatoff"
};

static const char *bootargDebug[] {
    "-ibtcompatdbg"
};

static const char *bootargBeta[] {
    "-ibtcompatbeta"
};

PluginConfiguration ADDPR(config) {
    xStringify(PRODUCT_NAME),
    parseModuleVersion(xStringify(MODULE_VERSION)),
    LiluAPI::AllowNormal | LiluAPI::AllowInstallerRecovery | LiluAPI::AllowSafeMode,
    bootargOff,
    arrsize(bootargOff),
    bootargDebug,
    arrsize(bootargDebug),
    bootargBeta,
    arrsize(bootargBeta),
    KernelVersion::MountainLion,
    KernelVersion::Tahoe,
    []() {
        ibtPatcher.init();
    }
};

static const char *IntelBTPatcher_IOBluetoothFamily[] { "/System/Library/Extensions/IOBluetoothFamily.kext/Contents/MacOS/IOBluetoothFamily" };

static KernelPatcher::KextInfo IntelBTPatcher_IOBluetoothInfo {
    "com.apple.iokit.IOBluetoothFamily",
    IntelBTPatcher_IOBluetoothFamily,
    1,
    {true, true},
    {},
    KernelPatcher::KextInfo::Unloaded
};

static const char *IntelBTPatcher_IOUSBHostFamily[] {
    "/System/Library/Extensions/IOUSBHostFamily.kext/Contents/MacOS/IOUSBHostFamily" };

static KernelPatcher::KextInfo IntelBTPatcher_IOUsbHostInfo {
    "com.apple.iokit.IOUSBHostFamily",
    IntelBTPatcher_IOUSBHostFamily,
    1,
    {true, true},
    {},
    KernelPatcher::KextInfo::Unloaded
};

void *CIntelBTPatcher::_hookPipeInstance = nullptr;
bool CIntelBTPatcher::_randomAddressInit = false;

bool CIntelBTPatcher::init()
{
    DBGLOG(DRV_NAME, "%s", __PRETTY_FUNCTION__);
    be201ProbeEnabled = getKernelVersion() == KernelVersion::Sequoia && be201Switch("-be201btprobe");
    be201NativeAddressEnabled = getKernelVersion() == KernelVersion::Sequoia && be201Switch("-be201nativeaddr");
    be201LEBaselineEnabled = getKernelVersion() == KernelVersion::Sequoia && be201Switch("-be201lebaseline");
    callbackIBTPatcher = this;
    if (getKernelVersion() < KernelVersion::Monterey) {
        lilu.onKextLoadForce(&IntelBTPatcher_IOBluetoothInfo, 1,
        [](void *user, KernelPatcher &patcher, size_t index, mach_vm_address_t address, size_t size) {
            callbackIBTPatcher->processKext(patcher, index, address, size);
        }, this);
    } else {
        lilu.onKextLoadForce(&IntelBTPatcher_IOUsbHostInfo, 1,
        [](void *user, KernelPatcher &patcher, size_t index, mach_vm_address_t address, size_t size) {
            callbackIBTPatcher->processKext(patcher, index, address, size);
        }, this);
    }
    return true;
}

void CIntelBTPatcher::free()
{
    DBGLOG(DRV_NAME, "%s", __PRETTY_FUNCTION__);
}

void CIntelBTPatcher::processKext(KernelPatcher &patcher, size_t index, mach_vm_address_t address, size_t size)
{
    DBGLOG(DRV_NAME, "%s", __PRETTY_FUNCTION__);
    if (getKernelVersion() < KernelVersion::Monterey) {
        if (IntelBTPatcher_IOBluetoothInfo.loadIndex == index) {
            DBGLOG(DRV_NAME, "%s", IntelBTPatcher_IOBluetoothInfo.id);
            
            KernelPatcher::RouteRequest findQueueRequestRequest {
                "__ZN25IOBluetoothHostController17FindQueuedRequestEtP22BluetoothDeviceAddresstbPP21IOBluetoothHCIRequest",
                newFindQueueRequest,
                oldFindQueueRequest
            };
            patcher.routeMultiple(index, &findQueueRequestRequest, 1, address, size);
            if (patcher.getError() == KernelPatcher::Error::NoError) {
                DBGLOG(DRV_NAME, "routed %s", findQueueRequestRequest.symbol);
            } else {
                SYSLOG(DRV_NAME, "failed to resolve %s, error = %d", findQueueRequestRequest.symbol, patcher.getError());
                patcher.clearError();
            }
            
        }
    } else {
        if (IntelBTPatcher_IOUsbHostInfo.loadIndex == index) {
            SYSLOG(DRV_NAME, "%s", IntelBTPatcher_IOUsbHostInfo.id);
            
            KernelPatcher::RouteRequest hostDeviceRequest {
            "__ZN15IOUSBHostDevice13deviceRequestEP9IOServiceRN11StandardUSB13DeviceRequestEPvP18IOMemoryDescriptorRjP19IOUSBHostCompletionj",
                newHostDeviceRequest,
                oldHostDeviceRequest
            };
            patcher.routeMultiple(index, &hostDeviceRequest, 1, address, size);
            if (patcher.getError() == KernelPatcher::Error::NoError) {
                SYSLOG(DRV_NAME, "routed %s", hostDeviceRequest.symbol);
            } else {
                SYSLOG(DRV_NAME, "failed to resolve %s, error = %d", hostDeviceRequest.symbol, patcher.getError());
                patcher.clearError();
            }

            KernelPatcher::RouteRequest asyncIORequest {
            "__ZN13IOUSBHostPipe2ioEP18IOMemoryDescriptorjP19IOUSBHostCompletionj",
                newAsyncIO,
                oldAsyncIO
            };
            patcher.routeMultiple(index, &asyncIORequest, 1, address, size);
            if (patcher.getError() == KernelPatcher::Error::NoError) {
                SYSLOG(DRV_NAME, "routed %s", asyncIORequest.symbol);
            } else {
                SYSLOG(DRV_NAME, "failed to resolve %s, error = %d", asyncIORequest.symbol, patcher.getError());
                patcher.clearError();
            }

            // macOS 26.5+: third parameter became ConfigurationDescriptor (was SuperSpeedEndpointCompanionDescriptor)
            KernelPatcher::RouteRequest initPipeConfigRequest {
            "__ZN13IOUSBHostPipe28initWithDescriptorsAndOwnersEPKN11StandardUSB18EndpointDescriptorEPKNS0_23ConfigurationDescriptorEP22AppleUSBHostControllerP15IOUSBHostDeviceP18IOUSBHostInterfaceht",
                newInitPipeConfig,
                oldInitPipeConfig
            };
            patcher.routeMultiple(index, &initPipeConfigRequest, 1, address, size);
            if (patcher.getError() == KernelPatcher::Error::NoError) {
                SYSLOG(DRV_NAME, "routed %s", initPipeConfigRequest.symbol);
            } else {
                SYSLOG(DRV_NAME, "failed to resolve %s, error = %d", initPipeConfigRequest.symbol, patcher.getError());
                patcher.clearError();
            }

            KernelPatcher::RouteRequest initPipeRequest {
            "__ZN13IOUSBHostPipe28initWithDescriptorsAndOwnersEPKN11StandardUSB18EndpointDescriptorEPKNS0_37SuperSpeedEndpointCompanionDescriptorEP22AppleUSBHostControllerP15IOUSBHostDeviceP18IOUSBHostInterfaceht",
                newInitPipe,
                oldInitPipe
            };
            patcher.routeMultiple(index, &initPipeRequest, 1, address, size);
            if (patcher.getError() == KernelPatcher::Error::NoError) {
                SYSLOG(DRV_NAME, "routed %s", initPipeRequest.symbol);
            } else {
                SYSLOG(DRV_NAME, "failed to resolve %s, error = %d", initPipeRequest.symbol, patcher.getError());
                patcher.clearError();
            }
        }
    }
}

#pragma mark - For Bigsur-, patch unhandled 0x2019 opcode

#define HCI_OP_LE_START_ENCRYPTION 0x2019

IOReturn CIntelBTPatcher::newFindQueueRequest(void *that, unsigned short arg1, void *addr, unsigned short arg2, bool arg3, void **hciRequestPtr)
{
    IOReturn ret = FunctionCast(newFindQueueRequest, callbackIBTPatcher->oldFindQueueRequest)(that, arg1, addr, arg2, arg3, hciRequestPtr);
    if (ret != 0 && arg1 == HCI_OP_LE_START_ENCRYPTION) {
        ret = FunctionCast(newFindQueueRequest, callbackIBTPatcher->oldFindQueueRequest)(that, arg1, addr, 0xffff, arg3, hciRequestPtr);
        DBGLOG(DRV_NAME, "%s ret: %d arg1: 0x%04x arg2: 0x%04x arg3: %d ptr: %p", __FUNCTION__, ret, arg1, arg2, arg3, *hciRequestPtr);
    }
    return ret;
}

#pragma mark - For Monterey+ patch for intercept HCI REQ and RESP

StandardUSB::DeviceRequest randomAddressRequest;
// Hardcoded Random Address HCI Command
const uint8_t randomAddressHci[9] = {0x05, 0x20, 0x06, 0x94, 0x50, 0x64, 0xD0, 0x78, 0x6B}; 
IOBufferMemoryDescriptor *writeHCIDescriptor = nullptr;

#define MAX_HCI_BUF_LEN                 255
#define HCI_OP_RESET                    0x0c03
#define HCI_OP_LE_SET_SCAN_PARAM        0x200B
#define HCI_OP_LE_SET_SCAN_ENABLE       0x200C
#define HCI_OP_LE_READ_REMOTE_FEATURES  0x2016

int remoteReadSCount = 0;
IOReturn CIntelBTPatcher::newHostDeviceRequest(void *that, IOService *provider, StandardUSB::DeviceRequest &request, void *data, IOMemoryDescriptor *descriptor, unsigned int &length, IOUSBHostCompletion *completion, unsigned int timeout)
{
    bool targetBE201 = false;
    if ((be201ProbeEnabled || be201NativeAddressEnabled || be201LEBaselineEnabled) && (request.bmRequestType & 0xe0) == 0x20 &&
        (request.bRequest == 0 || request.bRequest == 0xe0)) {
        auto *device = static_cast<IOUSBHostDevice *>(that);
        const auto *description = device->getDeviceDescriptor();
        targetBE201 = description && description->idVendor == 0x8087 && description->idProduct == 0x0037;
    }
    const bool observeBE201 = targetBE201 && be201ProbeEnabled;
    const bool guardBE201 = targetBE201 && be201NativeAddressEnabled && be201AddressGuard.bind(reinterpret_cast<uintptr_t>(that));
    uint64_t nativeAddressTicket = 0;
    HciCommandHdr *hdr = nullptr;
    uint32_t hdrLen = 0;
    char hciBuf[MAX_HCI_BUF_LEN] = {0};
    
    if (data == nullptr) {
        if (descriptor != nullptr &&
            (getKernelVersion() < KernelVersion::Sequoia || !descriptor->prepare(kIODirectionOut))) {
            if (descriptor->getLength() > 0) {
                descriptor->readBytes(0, hciBuf, min(descriptor->getLength(), MAX_HCI_BUF_LEN));
                hdrLen = (uint32_t)min(descriptor->getLength(), MAX_HCI_BUF_LEN);
            }
            if (getKernelVersion() >= KernelVersion::Sequoia)
                descriptor->complete(kIODirectionOut);
        }
        hdr = (HciCommandHdr *)hciBuf;
        if (hdr->opcode == HCI_OP_LE_SET_SCAN_PARAM && hdr->data[5] == 0x1) {
            const bool preserveNative = guardBE201 && hdrLen >= 10 && hdr->len == 7 &&
                be201AddressGuard.preserve(reinterpret_cast<uintptr_t>(that));
            if (!_randomAddressInit && preserveNative) {
                // Do not replace the system RPA with the historical fixed value.
                // Leave _randomAddressInit untouched: reset/rejected address can
                // still take the original fallback on the next scan request.
                if (observeBE201) {
                    be201probe::increment(be201ProbeStats.placeholderSkipped);
                    be201probe::increment(be201ProbeStats.sequence);
                }
            } else if (!_randomAddressInit) {
                randomAddressRequest.bmRequestType = makeDeviceRequestbmRequestType(kRequestDirectionOut, kRequestTypeClass, kRequestRecipientInterface);
                randomAddressRequest.bRequest = 0xE0;
                randomAddressRequest.wIndex = 0;
                randomAddressRequest.wValue = 0;
                randomAddressRequest.wLength = 9;
                length = 9;
                if (writeHCIDescriptor == nullptr)
                    writeHCIDescriptor = IOBufferMemoryDescriptor::withBytes(randomAddressHci, 9, kIODirectionInOut);
                writeHCIDescriptor->prepare(kIODirectionInOut);
                if (observeBE201) be201probe::injectedRandomAddress(be201ProbeStats);
                IOReturn ret = FunctionCast(newHostDeviceRequest, callbackIBTPatcher->oldHostDeviceRequest)(that, provider, randomAddressRequest, nullptr, writeHCIDescriptor, length, nullptr, timeout);
                writeHCIDescriptor->complete(kIODirectionInOut);
                const char *randAddressDump = _hexDumpHCIData((uint8_t *)randomAddressHci, 9);
                if (randAddressDump) {
                    SYSLOG(DRV_NAME, "[PATCH] Sending Random Address HCI %d %s", ret, randAddressDump);
                    IOFree((void *)randAddressDump, 9 * 3 + 1);
                }
                _randomAddressInit = true;
                SYSLOG(DRV_NAME, "[PATCH] Resend LE SCAN PARAM HCI %d", ret);
            }
        } else if (hdr->opcode == HCI_OP_LE_READ_REMOTE_FEATURES &&
                   !(targetBE201 && be201LEBaselineEnabled)) {
            // #514: send TWO extra reads -> two duplicate 0x04 events to rewrite
            // (1st dup -> fake PHY Update Complete, 2nd dup -> fake LE Data Length Change).
            remoteReadSCount += 2;
            FunctionCast(newHostDeviceRequest, callbackIBTPatcher->oldHostDeviceRequest)(that, provider, request, nullptr, descriptor, length, nullptr, timeout);
            FunctionCast(newHostDeviceRequest, callbackIBTPatcher->oldHostDeviceRequest)(that, provider, request, nullptr, descriptor, length, nullptr, timeout);
        }
    } else {
        hdr = (HciCommandHdr *)data;
        hdrLen = request.wLength - 3;
    }
    if (hdr) {
        // HCI reset, we need to send Random address again
        if (hdr->opcode == HCI_OP_RESET)
            _randomAddressInit = false;
#if DEBUG
        DBGLOG(DRV_NAME, "[%s] bRequest: 0x%x direction: %s type: %s recipient: %s wValue: 0x%02x wIndex: 0x%02x opcode: 0x%04x len: %d length: %d async: %d", provider->getName(), request.bRequest, requestDirectionNames[(request.bmRequestType & kDeviceRequestDirectionMask) >> kDeviceRequestDirectionPhase], requestRecipientNames[(request.bmRequestType & kDeviceRequestRecipientMask) >> kDeviceRequestRecipientPhase], requestTypeNames[(request.bmRequestType & kDeviceRequestTypeMask) >> kDeviceRequestTypePhase], request.wValue, request.wIndex, hdr->opcode, hdr->len, request.wLength, completion != nullptr);
        if (hdrLen) {
            const char *dump = _hexDumpHCIData((uint8_t *)hdr, hdrLen);
            if (dump) {
                DBGLOG(DRV_NAME, "[Request]: %s", dump);
                IOFree((void *)dump, hdrLen * 3 + 1);
            }
        }
#endif
    }
    const size_t available = data ? request.wLength : hdrLen;
    const auto *commandBytes = reinterpret_cast<const uint8_t *>(hdr);
    if (guardBE201 && commandBytes && available >= 3) {
        if (be201address::header(commandBytes, available, HCI_OP_RESET, 0)) {
            be201AddressGuard.invalidate();
        } else if (commandBytes[0] == 0x05 && commandBytes[1] == 0x20) {
            const uint64_t ticket = be201AddressGuard.invalidate();
            if (be201address::validRPACommand(commandBytes, available)) {
                nativeAddressTicket = ticket;
                if (observeBE201) {
                    be201probe::increment(be201ProbeStats.nativeRPAValidCommands);
                    if (completion) be201probe::increment(be201ProbeStats.nativeRPAAsyncSubmissions);
                }
            }
        }
    }
    if (observeBE201) {
        be201probe::submitted(be201ProbeStats, reinterpret_cast<const uint8_t *>(hdr), available);
        be201PeerObserver.command(be201PeerStats,reinterpret_cast<const uint8_t *>(hdr),available);
        be201privacycap::submitted(be201PrivacyCapabilities,reinterpret_cast<const uint8_t *>(hdr),available);
    }
    BE201AddressCompletion *addressCompletion = nullptr;
    IOUSBHostCompletion wrappedCompletion = {};
    if (nativeAddressTicket && completion && completion->action) {
        addressCompletion = new BE201AddressCompletion;
        if (addressCompletion) {
            addressCompletion->original = *completion;
            addressCompletion->ticket = nativeAddressTicket;
            addressCompletion->finished = nativeAddressUSBCompleted;
            wrappedCompletion = addressCompletion->wrapped();
        } else if (observeBE201) {
            be201probe::increment(be201ProbeStats.nativeRPAObserverAllocationFailures);
        }
    }
    const IOReturn transportResult = FunctionCast(newHostDeviceRequest, callbackIBTPatcher->oldHostDeviceRequest)(that, provider, request, data, descriptor, length, addressCompletion ? &wrappedCompletion : completion, timeout);
    if (addressCompletion) addressCompletion->submitted(transportResult);
    if (observeBE201 && nativeAddressTicket && !completion) {
        be201probe::put(be201ProbeStats.nativeRPASyncBytes, length);
    }
    if (nativeAddressTicket && be201AddressGuard.accepted(nativeAddressTicket,
            completion == nullptr, transportResult == kIOReturnSuccess, length) && observeBE201) {
        be201probe::increment(be201ProbeStats.nativeRPAUSBAccepted);
        be201probe::increment(be201ProbeStats.sequence);
    }
    if (observeBE201 && transportResult != kIOReturnSuccess) {
        be201probe::increment(be201ProbeStats.submitErrors);
        be201probe::increment(be201ProbeStats.sequence);
    }
    return transportResult;
}

#define HCI_EVT_LE_META                               0x3E
#define HCI_EVT_LE_META_READ_REMOTE_FEATURES_COMPLETE 0x04

uint8_t fakePhyUpdateCompleteEvent[8] = {0x3E, 0x06, 0x0C, 0x00, 0x00, 0x00, 0x02, 0x02};
// #514: LE Data Length Change (LE Meta subevent 0x07, no status byte -> handle at [3][4]).
// bluetoothd stalls at LE_READY_WAIT_FOR_LENGTH after PHY until it sees this. 27 octets / 328us tx+rx.
// Made by Claude.
uint8_t fakeDataLengthChangeEvent[13] = {0x3E, 0x0B, 0x07, 0x00, 0x00, 0x1B, 0x00, 0x48, 0x01, 0x1B, 0x00, 0x48, 0x01};
//uint8_t remoteFeaturesStatus[6] = {0x0F, 0x04, 0x00, 0x01, 0x16, 0x20};

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

#define VENDOR_USB_INTEL 0x8087

void CIntelBTPatcher::captureIntelInterruptPipe(void *that, StandardUSB::EndpointDescriptor const *descriptor, IOUSBHostDevice *device)
{
    if (!device)
        return;
    const StandardUSB::DeviceDescriptor *deviceDescriptor = device->getDeviceDescriptor();
    if (deviceDescriptor && deviceDescriptor->idVendor == VENDOR_USB_INTEL) {
        uint8_t epType = StandardUSB::getEndpointType(descriptor);
        if (epType == kIOUSBEndpointTypeInterrupt) {
            CIntelBTPatcher::_hookPipeInstance = that;
            if (deviceDescriptor->idProduct == 0x0037 && (descriptor->bEndpointAddress & 0x80)) {
                __atomic_store_n(&be201EventPipe, reinterpret_cast<uintptr_t>(that), __ATOMIC_RELAXED);
                if (be201ProbeEnabled) {
                    be201probe::increment(be201ProbeStats.eventPipeCaptures);
                    be201probe::increment(be201ProbeStats.sequence);
                }
            }
        }
    }
}

int CIntelBTPatcher::
newInitPipe(void *that, StandardUSB::EndpointDescriptor const *descriptor, StandardUSB::SuperSpeedEndpointCompanionDescriptor const *superDescriptor, AppleUSBHostController *controller, IOUSBHostDevice *device, IOUSBHostInterface *interface, unsigned char a7, unsigned short a8)
{
    int ret = FunctionCast(newInitPipe, callbackIBTPatcher->oldInitPipe)(that, descriptor, superDescriptor, controller, device, interface, a7, a8);
    captureIntelInterruptPipe(that, descriptor, device);
    return ret;
}

int CIntelBTPatcher::
newInitPipeConfig(void *that, StandardUSB::EndpointDescriptor const *descriptor, StandardUSB::ConfigurationDescriptor const *configDescriptor, AppleUSBHostController *controller, IOUSBHostDevice *device, IOUSBHostInterface *interface, unsigned char a7, unsigned short a8)
{
    int ret = FunctionCast(newInitPipeConfig, callbackIBTPatcher->oldInitPipeConfig)(that, descriptor, configDescriptor, controller, device, interface, a7, a8);
    captureIntelInterruptPipe(that, descriptor, device);
    return ret;
}
