// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <Headers/kern_version.hpp>
#include <IOKit/IOService.h>
#include <IOKit/IOWorkLoop.h>
#include <IOKit/IOTimerEventSource.h>
#include "LECommandProbe.hpp"

extern "C" void be201NativeServiceFree(IOService *) __asm__("__ZN9IOService4freeEv");

static bool be201ProbeEnabled = false;
static be201probe::Statistics be201ProbeStats = {};

class EXPORT IntelBTPatcher : public IOService {
    OSDeclareDefaultStructors(IntelBTPatcher)
    IOWorkLoop *probeLoop = nullptr;
    IOTimerEventSource *probeTimer = nullptr;
    uint64_t lastSequence = UINT64_MAX;
    bool timerAttached = false;
    void releaseProbe() {
        if (probeTimer) {
            probeTimer->cancelTimeout();
            probeTimer->disable();
            if (probeLoop && timerAttached) probeLoop->removeEventSource(probeTimer);
            probeTimer->cancelTimeout(); timerAttached = false;
            probeTimer->release(); probeTimer = nullptr;
        }
        if (probeLoop) { probeLoop->release(); probeLoop = nullptr; }
    }
    void publishProbe() {
        const uint64_t seq = be201probe::load(be201ProbeStats.sequence);
        if (seq == lastSequence) return;
        lastSequence = seq;
#define PROP(field) setProperty("BE201BLE_" #field, be201probe::load(be201ProbeStats.field), 64)
        PROP(sequence); PROP(commandCount); PROP(malformedCount); PROP(submitErrors);
        PROP(nativeRandomCount); PROP(nativeRandomSequence); PROP(nativeRandomKind);
        PROP(nativeRandomSinceReset); PROP(placeholderCount); PROP(placeholderSequence);
        PROP(nativeBeforePlaceholder); PROP(scanCount); PROP(scanOwnAddressType);
        PROP(connectCount); PROP(connectSequence); PROP(connectOpcode);
        PROP(connectOwnAddressType); PROP(connectPeerAddressType);
        PROP(connectFilterPolicy); PROP(connectPHYMask); PROP(nativeBeforeConnect);
        PROP(resolvingListAdds); PROP(resolvingListClears);
        PROP(acceptListAdds); PROP(acceptListClears); PROP(acceptListLastAddressType);
        PROP(eventCount); PROP(eventMalformed); PROP(lastCommandOpcode); PROP(lastCommandStatus);
        PROP(randomAddressHCICompletions); PROP(randomAddressHCIErrors);
        PROP(connectCommandStatuses); PROP(connectCommandLastStatus);
        PROP(connectionCompleteCount); PROP(connectionCompleteLastStatus);
        PROP(connectionCompleteSuccesses); PROP(connectionCompleteFailures);
        PROP(eventObserverAllocationFailures); PROP(eventUSBErrors);
        PROP(eventPipeCaptures); PROP(eventReadCallbacks); PROP(eventReadFailures);
        PROP(nativeRPAValidCommands); PROP(nativeRPAAsyncSubmissions); PROP(nativeRPAAsyncCompletions);
        PROP(nativeRPAAsyncStatus); PROP(nativeRPAAsyncBytes); PROP(nativeRPASyncBytes);
        PROP(nativeRPAObserverAllocationFailures); PROP(nativeRPAUSBAccepted); PROP(placeholderSkipped);
        PROP(resolutionEnableCount); PROP(resolutionEnabled); PROP(controllerResetCount);
        PROP(advertisingParameters); PROP(advertisingType); PROP(advertisingOwnAddressType);
        PROP(advertisingEnableCommands); PROP(advertisingEnabled);
        PROP(advertisingDataCommands); PROP(advertisingDataLength); PROP(advertisingDataTypeMask);
        PROP(scanResponseCommands); PROP(scanResponseLength); PROP(scanResponseTypeMask);
        PROP(advertisingMalformedAD); PROP(handoffDataCommands); PROP(handoffResponseCommands);
        PROP(advertisingParameterCompletions); PROP(advertisingParameterErrors);
        PROP(advertisingDataCompletions); PROP(advertisingDataErrors);
        PROP(scanResponseCompletions); PROP(scanResponseErrors);
        PROP(advertisingEnableCompletions); PROP(advertisingEnableErrors);
        PROP(centralConnectionSuccesses); PROP(peripheralConnectionSuccesses);
        PROP(connectionRoleUnknown); PROP(lastSuccessfulRole); PROP(lastSuccessfulPeerAddressType);
#undef PROP
    }
    static void tick(OSObject *owner, IOTimerEventSource *timer) {
        auto *self = OSDynamicCast(IntelBTPatcher, owner);
        if (self) { self->publishProbe(); timer->setTimeoutMS(1000); }
    }
public:
    IOService *probe(IOService *provider, SInt32 *score) override {
        return ADDPR(startSuccess) ? IOService::probe(provider, score) : nullptr;
    }
    bool start(IOService *provider) override {
        if (!IOService::start(provider)) return false;
        setProperty("VersionInfo", kextVersion);
        setProperty("BE201BLEProbeEnabled", be201ProbeEnabled);
        setProperty("BE201LEBaselineEnabled", getKernelVersion()==KernelVersion::Sequoia && checkKernelArgument("-be201lebaseline"));
        setProperty("BE201BLEProbeSemantics", "USB submissions/completions and observed HCI event status prefixes; no addresses or keys");
        if (be201ProbeEnabled) {
            probeLoop = IOWorkLoop::workLoop();
            if (probeLoop) probeTimer = IOTimerEventSource::timerEventSource(this, tick);
            if (!probeTimer || probeLoop->addEventSource(probeTimer) != kIOReturnSuccess) {
                releaseProbe(); setProperty("BE201BLEProbeStatus", "reporter unavailable");
            } else {
                timerAttached = true; publishProbe(); probeTimer->setTimeoutMS(1000);
                setProperty("BE201BLEProbeStatus", "RPA preservation experiment; USB acceptance is not HCI completion");
            }
        }
        registerService(); return true;
    }
    void stop(IOService *provider) override { releaseProbe(); IOService::stop(provider); }
    void free() override { releaseProbe(); be201NativeServiceFree(this); }
};
OSDefineMetaClassAndStructors(IntelBTPatcher, IOService)
