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
        PROP(resolutionEnableCount); PROP(resolutionEnabled); PROP(controllerResetCount);
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
        setProperty("BE201BLEProbeSemantics", "USB command submissions; not HCI completion or radio success");
        if (be201ProbeEnabled) {
            probeLoop = IOWorkLoop::workLoop();
            if (probeLoop) probeTimer = IOTimerEventSource::timerEventSource(this, tick);
            if (!probeTimer || probeLoop->addEventSource(probeTimer) != kIOReturnSuccess) {
                releaseProbe(); setProperty("BE201BLEProbeStatus", "reporter unavailable");
            } else {
                timerAttached = true; publishProbe(); probeTimer->setTimeoutMS(1000);
                setProperty("BE201BLEProbeStatus", "metadata only; transport unchanged");
            }
        }
        registerService(); return true;
    }
    void stop(IOService *provider) override { releaseProbe(); IOService::stop(provider); }
    void free() override { releaseProbe(); be201NativeServiceFree(this); }
};
OSDefineMetaClassAndStructors(IntelBTPatcher, IOService)
