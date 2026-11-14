//
//  AirportItlwmV2.cpp
//  AirportItlwm-Sonoma
//
//  Created by qcwap on 2023/6/27.
//  Copyright © 2023 Zhong Xianyao. All rights reserved.
//

#include "AirportItlwmV2.hpp"
#include <IOKit/IODeviceTreeSupport.h>
#include <sys/_netstat.h>
#include <crypto/sha1.h>
#include <net80211/ieee80211_priv.h>
#include <net80211/ieee80211_var.h>

#include "AirportItlwmSkywalkInterface.hpp"
#ifdef AIRPORT_WCL
#include "AirportItlwmAWDLInterface.hpp"
#ifdef AIRPORT_WCL
#include <sys/sysctl.h>
#endif
#endif
#include "IOPCIEDeviceWrapper.hpp"
#include "ItlStartupDiagnostics.hpp"

#define super IO80211Controller
OSDefineMetaClassAndStructors(AirportItlwm, IO80211Controller);
OSDefineMetaClassAndStructors(CTimeout, OSObject)

IO80211WorkQueue *_fWorkloop;
IOCommandGate *_fCommandGate;

void AirportItlwm::releaseAll()
{
#ifdef AIRPORT_WCL
    stopAWDLInterface();
    if (fNetIf)
        static_cast<AirportItlwmSkywalkInterface *>(fNetIf)->stopWCL();
    OSSafeReleaseNULL(driverFaultReporter);
    OSSafeReleaseNULL(driverCoreFaultReporter);
    OSSafeReleaseNULL(driverFaultStream);
    OSSafeReleaseNULL(driverLogger);
    // Stop only successfully started pipes, while their owner workloop exists.
    if (driverSnapshotsPipeStarted) {
        driverSnapshotsPipe->CCPipe::stopPipe();
        driverSnapshotsPipeStarted = false;
    }
    if (driverDataPathPipeStarted) {
        driverDataPathPipe->CCPipe::stopPipe();
        driverDataPathPipeStarted = false;
    }
    if (driverLogPipeStarted) {
        driverLogPipe->CCPipe::stopPipe();
        driverLogPipeStarted = false;
    }
#endif
    OSSafeReleaseNULL(driverLogPipe);
    OSSafeReleaseNULL(driverDataPathPipe);
    OSSafeReleaseNULL(driverSnapshotsPipe);
#ifndef AIRPORT_WCL
    OSSafeReleaseNULL(driverFaultReporter);
#endif
    if (fHalService) {
        fHalService->release();
        fHalService = NULL;
    }
    if (_fWorkloop) {
        if (_fCommandGate) {
//            _fCommandGate->disable();
            _fWorkloop->removeEventSource(_fCommandGate);
            _fCommandGate->release();
            _fCommandGate = NULL;
        }
        if (scanSource) {
            scanSource->cancelTimeout();
            scanSource->disable();
            _fWorkloop->removeEventSource(scanSource);
            scanSource->release();
            scanSource = NULL;
        }
        if (fWatchdogWorkLoop) {
            if (watchdogTimer) {
                watchdogTimer->cancelTimeout();
                fWatchdogWorkLoop->removeEventSource(watchdogTimer);
                watchdogTimer->release();
                watchdogTimer = NULL;
            }
            fWatchdogWorkLoop->release();
            fWatchdogWorkLoop = NULL;
        }
        _fWorkloop->release();
        _fWorkloop = NULL;
    }
    unregistPM();
}

void AirportItlwm::
eventHandler(struct ieee80211com *ic, int msgCode, void *data)
{
    AirportItlwm *that = OSDynamicCast(AirportItlwm, ic->ic_ac.ac_if.controller);
#ifdef AIRPORT_WCL
    if (!that)
        return;
#endif
    IO80211SkywalkInterface *interface = that->fNetIf;
    if (!interface)
        return;
#ifdef AIRPORT_WCL
    static_cast<AirportItlwmSkywalkInterface *>(interface)->handleWCLEvent(msgCode, data);
#else
    switch (msgCode) {
        case IEEE80211_EVT_COUNTRY_CODE_UPDATE:
            interface->postMessage(APPLE80211_M_COUNTRY_CODE_CHANGED, NULL, 0, 0);
            break;
        case IEEE80211_EVT_STA_ASSOC_DONE:
            interface->postMessage(APPLE80211_M_ASSOC_DONE, NULL, 0, 0);
            break;
        case IEEE80211_EVT_STA_DEAUTH:
            interface->postMessage(APPLE80211_M_DEAUTH_RECEIVED, NULL, 0, 0);
            break;
        default:
            break;
    }
#endif
}

void AirportItlwm::watchdogAction(IOTimerEventSource *timer)
{
    struct _ifnet *ifp = &fHalService->get80211Controller()->ic_ac.ac_if;
    (*ifp->if_watchdog)(ifp);

    watchdogTimer->setTimeoutMS(kWatchDogTimerPeriod);
}

void AirportItlwm::fakeScanDone(OSObject *owner, IOTimerEventSource *sender)
{
#ifndef AIRPORT_WCL
    UInt32 msg = 0;
#endif
    AirportItlwm *that = (AirportItlwm *)owner;
#ifdef AIRPORT_WCL
    if (that->fNetIf)
        static_cast<AirportItlwmSkywalkInterface *>(that->fNetIf)->completeWCLScan();
#else
    that->fNetIf->postMessage(APPLE80211_M_SCAN_DONE, &msg, 4, 0);
#endif
}

bool AirportItlwm::init(OSDictionary *properties)
{
    XYLog("%s\n", __PRETTY_FUNCTION__);
    bool ret = super::init(properties);
    awdlSyncEnable = false;
    power_state = 0;
    memset(geo_location_cc, 0, sizeof(geo_location_cc));
    return ret;
}

IOService* AirportItlwm::probe(IOService *provider, SInt32 *score)
{
    XYLog("%s\n", __PRETTY_FUNCTION__);
    IOPCIEDeviceWrapper *wrapper = OSDynamicCast(IOPCIEDeviceWrapper, provider);
    if (!wrapper) {
        XYLog("%s Not a IOPCIEDeviceWrapper instance\n", __FUNCTION__);
        return NULL;
    }
    pciNub = wrapper->pciNub;
    fHalService = wrapper->fHalService;
    if (!pciNub || !fHalService) {
        XYLog("%s Not a valid IOPCIEDeviceWrapper instance\n", __FUNCTION__);
        return NULL;
    }
    return super::probe(provider, score);
}

#define LOWER32(x)  ((uint64_t)(x) & 0xffffffff)
#define HIGHER32(x) ((uint64_t)(x) >> 32)

bool AirportItlwm::
initCCLogs()
{
    ItlStartupStage(pciNub, "corecapture-log-pipe");
    CCPipeOptions driverLogOptions = { 0 };
    driverLogOptions.pipe_type = 0;
    driverLogOptions.log_data_type = 1;
    driverLogOptions.pipe_size = 0x200000;
    driverLogOptions.min_log_size_notify = 0xccccc;
    driverLogOptions.notify_threshold = 1000;
    strlcpy(driverLogOptions.file_name, "Itlwm_Logs", sizeof(driverLogOptions.file_name));
    snprintf(driverLogOptions.name, sizeof(driverLogOptions.name), "wlan%d", 0);
    strlcpy(driverLogOptions.directory_name, "WiFi", sizeof(driverLogOptions.directory_name));
    driverLogOptions.pad9 = 0x1000000;
    driverLogOptions.pad10 = 2;
    driverLogOptions.file_options = 0;
    driverLogOptions.log_policy = 0;
    driverLogPipe = CCPipe::withOwnerNameCapacity(this, "com.zxystd.AirportItlwm", "DriverLogs", &driverLogOptions);
    XYLog("%s driverLogPipeRet %d\n", __FUNCTION__, driverLogPipe != NULL);
#ifdef AIRPORT_WCL
    if (!driverLogPipe || !getWorkLoop()) {
        ItlStartupFailure(pciNub, "corecapture-log-pipe", kIOReturnNoResources);
        return false;
    }
    // The factory only initializes the pipe. startPipe creates its event sources.
    // Qualify the native method: do not dispatch through the legacy CCPipe header.
    driverLogPipeStarted = driverLogPipe->CCPipe::startPipe();
    if (!driverLogPipeStarted) {
        ItlStartupFailure(pciNub, "corecapture-log-pipe-start", kIOReturnError);
        return false;
    }
    CCStreamOptions loggerOptions = {};
    CCStream *logger = CCStream::withPipeAndName(driverLogPipe, "AirportItlwm", &loggerOptions);
    driverLogger = OSDynamicCast(CCLogStream, logger);
    if (!driverLogger) {
        ItlStartupFailure(pciNub, "corecapture-log-stream", kIOReturnNoResources);
        OSSafeReleaseNULL(logger);
        return false;
    }
#endif

    ItlStartupStage(pciNub, "corecapture-datapath-pipe");
    memset(&driverLogOptions, 0, sizeof(driverLogOptions));
    driverLogOptions.pipe_type = 0;
    driverLogOptions.log_data_type = 0;
    driverLogOptions.pipe_size = 0x200000;
    driverLogOptions.min_log_size_notify = 0xccccc;
    driverLogOptions.notify_threshold = 1000;
    strlcpy(driverLogOptions.file_name, "AppleBCMWLAN_Datapath", sizeof(driverLogOptions.file_name));
    strlcpy(driverLogOptions.directory_name, "WiFi", sizeof(driverLogOptions.directory_name));
    driverLogOptions.pad9 = HIGHER32(0x202800000);
    driverLogOptions.pad10 = LOWER32(0x202800000);
    driverLogOptions.file_options = 0;
    driverLogOptions.log_policy = 0;
    driverDataPathPipe = CCPipe::withOwnerNameCapacity(this, "com.zxystd.AirportItlwm", "DatapathEvents", &driverLogOptions);
    XYLog("%s driverDataPathPipeRet %d\n", __FUNCTION__, driverDataPathPipe != NULL);
#ifdef AIRPORT_WCL
    if (!driverDataPathPipe) {
        ItlStartupFailure(pciNub, "corecapture-datapath-pipe", kIOReturnNoResources);
        return false;
    }
    driverDataPathPipeStarted = driverDataPathPipe->CCPipe::startPipe();
    if (!driverDataPathPipeStarted) {
        ItlStartupFailure(pciNub, "corecapture-datapath-pipe-start", kIOReturnError);
        return false;
    }
#endif

    ItlStartupStage(pciNub, "corecapture-snapshots-pipe");
    memset(&driverLogOptions, 0, sizeof(driverLogOptions));
    driverLogOptions.pipe_type = 0x200000001;
    driverLogOptions.log_data_type = 2;
    strlcpy(driverLogOptions.file_name, "StateSnapshots", sizeof(driverLogOptions.file_name));
    strlcpy(driverLogOptions.name, "0", sizeof(driverLogOptions.name));
    strlcpy(driverLogOptions.directory_name, "WiFi", sizeof(driverLogOptions.directory_name));
    driverLogOptions.pipe_size = 128;
    driverSnapshotsPipe = CCPipe::withOwnerNameCapacity(this, "com.zxystd.AirportItlwm", "StateSnapshots", &driverLogOptions);
    XYLog("%s driverSnapshotsPipeRet %d\n", __FUNCTION__, driverSnapshotsPipe != NULL);
#ifdef AIRPORT_WCL
    if (!driverSnapshotsPipe) {
        ItlStartupFailure(pciNub, "corecapture-snapshots-pipe", kIOReturnNoResources);
        return false;
    }
    driverSnapshotsPipeStarted = driverSnapshotsPipe->CCPipe::startPipe();
    if (!driverSnapshotsPipeStarted) {
        ItlStartupFailure(pciNub, "corecapture-snapshots-pipe-start", kIOReturnError);
        return false;
    }
#endif

    ItlStartupStage(pciNub, "corecapture-fault-reporter");
    CCStreamOptions faultReportOptions = { 0 };
    faultReportOptions.stream_type = 1;
    faultReportOptions.console_level = 0xFFFFFFFFFFFFFFFF;
#ifdef AIRPORT_WCL
    driverFaultStream = CCStream::withPipeAndName(driverSnapshotsPipe, "FaultReporter", &faultReportOptions);
    CCDataStream *dataStream = OSDynamicCast(CCDataStream, driverFaultStream);
    if (!dataStream || !_fWorkloop) {
        ItlStartupFailure(pciNub, "corecapture-fault-stream", kIOReturnNoResources);
        return false;
    }
    driverCoreFaultReporter = CCFaultReporter::withStreamWorkloop(dataStream, _fWorkloop);
    if (!driverCoreFaultReporter) {
        ItlStartupFailure(pciNub, "corecapture-core-fault-reporter", kIOReturnNoResources);
        return false;
    }
    driverFaultReporter = IO80211FaultReporter::allocWithParams(driverCoreFaultReporter);
    if (!OSDynamicCast(CommonFaultReporter, driverFaultReporter)) {
        ItlStartupFailure(pciNub, "corecapture-wifi-fault-reporter", kIOReturnNoResources);
        return false;
    }
#else
    driverFaultReporter = CCStream::withPipeAndName(driverSnapshotsPipe, "FaultReporter", &faultReportOptions);
#endif
    XYLog("%s driverFaultReporterRet %d\n", __FUNCTION__, driverFaultReporter != NULL);
    return driverLogPipe && driverDataPathPipe && driverSnapshotsPipe && driverFaultReporter;
}

bool AirportItlwm::start(IOService *provider)
{
    ItlStartupResult(pciNub, "starting");
    pciNub->setProperty("ItlwmStartupRevision", "be201-local-ac-1.0.1");
    pciNub->setProperty("BE201ProtocolLimit", "a/b/g/n/ac; HE/EHT disabled");
    pciNub->setProperty("BE201AWDLStatus", "not implemented; disabled");
    pciNub->setProperty("BE201RangingStatus", "not implemented; disabled");
    ItlStartupStage(pciNub, "controller-start");
#if __IO80211_TARGET == __MAC_15_2
    if (version_major != 24 || version_minor < 2) {
        ItlStartupFailure(pciNub, "darwin-version", kIOReturnUnsupported);
        return false;
    }
#endif
    // 1.1.88: AWDL is on by default only on the kernel its private layouts were read from (24G824).
    pciNub->setProperty("ItlwmAwdlLayoutVerified", ItlAwdlLayoutVerified());
    XYLog("%s\n", __PRETTY_FUNCTION__);
    struct IOSkywalkEthernetInterface::RegistrationInfo registInfo;
    int boot_value = 0;

    UInt8 builtIn = 0;
    setProperty("built-in", OSData::withBytes(&builtIn, sizeof(builtIn)));
    setProperty("DriverKitDriver", kOSBooleanFalse);
#ifdef AIRPORT_WCL
    ItlStartupStage(pciNub, "corecapture-init");
    if (!initCCLogs()) {
        ItlStartupFailure(pciNub, "corecapture-init", kIOReturnError);
        releaseAll();
        return false;
    }
    ItlStartupStage(pciNub, "corecapture-ready");
#endif
    ItlStartupStage(pciNub, "super-start");
    if (!super::start(provider)) {
        ItlStartupFailure(pciNub, "super-start", kIOReturnError);
#ifdef AIRPORT_WCL
        releaseAll();
#endif
        return false;
    }
    ItlStartupStage(pciNub, "super-start-ready");
    pciNub->setBusMasterEnable(true);
    pciNub->setIOEnable(true);
    pciNub->setMemoryEnable(true);
    pciNub->configWrite8(0x41, 0);
    ItlStartupStage(pciNub, "power-domain-request");
    const IOReturn powerRequestResult = pciNub->requestPowerDomainState(kIOPMPowerOn,
                                        (IOPowerConnection *) getParentEntry(gIOPowerPlane), IOPMLowestState);
    pciNub->setProperty("ItlwmStartupPowerResult", static_cast<UInt32>(powerRequestResult), 32);
    if (powerRequestResult != IOPMNoErr) {
        ItlStartupFailure(pciNub, "power-domain-request", powerRequestResult);
        super::stop(provider);
        return false;
    }
    ItlStartupStage(pciNub, "pci-power-init");
    if (initPCIPowerManagment(pciNub) == false) {
        ItlStartupFailure(pciNub, "pci-power-init", kIOReturnError);
        super::stop(pciNub);
        return false;
    }
    ItlStartupStage(pciNub, "workloop-check");
    if (_fWorkloop == NULL) {
        ItlStartupFailure(pciNub, "workloop-check", kIOReturnNoResources);
        XYLog("No _fWorkloop!!\n");
        super::stop(pciNub);
        releaseAll();
        return false;
    }
    ItlStartupStage(pciNub, "command-gate-create");
    _fCommandGate = IOCommandGate::commandGate(this, (IOCommandGate::Action)AirportItlwm::tsleepHandler);
    if (_fCommandGate == 0) {
        ItlStartupFailure(pciNub, "command-gate-create", kIOReturnNoResources);
        XYLog("No command gate!!\n");
        super::stop(pciNub);
        releaseAll();
        return false;
    }
    ItlStartupStage(pciNub, "command-gate-add");
    const IOReturn gateAddResult = _fWorkloop->addEventSource(_fCommandGate);
    pciNub->setProperty("ItlwmStartupGateAddResult", static_cast<UInt32>(gateAddResult), 32);
    if (gateAddResult != kIOReturnSuccess) {
        ItlStartupFailure(pciNub, "command-gate-add", gateAddResult);
        super::stop(provider);
        releaseAll();
        return false;
    }
    ItlStartupStage(pciNub, "medium-setup");
    const IONetworkMedium *primaryMedium;
    if (!createMediumTables(&primaryMedium) ||
        !setCurrentMedium(primaryMedium) || !setSelectedMedium(primaryMedium)) {
        ItlStartupFailure(pciNub, "medium-setup", kIOReturnError);
        XYLog("setup medium fail\n");
        releaseAll();
        return false;
    }
    ItlStartupStage(pciNub, "hal-controller-init");
    const bool halInitResult = fHalService->initWithController(this, _fWorkloop, _fCommandGate);
    pciNub->setProperty("ItlwmStartupHalInitResult", static_cast<UInt32>(halInitResult), 32);
    if (!halInitResult) {
        ItlStartupFailure(pciNub, "hal-controller-init", kIOReturnError);
        super::stop(provider);
        releaseAll();
        return false;
    }
    fHalService->get80211Controller()->ic_event_handler = eventHandler;

    if (PE_parse_boot_argn("-novht", &boot_value, sizeof(boot_value)))
        fHalService->get80211Controller()->ic_userflags |= IEEE80211_F_NOVHT;
    if (PE_parse_boot_argn("-noht40", &boot_value, sizeof(boot_value)))
        fHalService->get80211Controller()->ic_userflags |= IEEE80211_F_NOHT40;

#ifdef AIRPORT_WCL
    // HE is opt-in per bundle; a boot override can force the ac recovery path.
    // Do not reuse itlwm_he: old installs may retain that unrelated argument.
    bool requestHE = getProperty("BE201EnableHE") == kOSBooleanTrue;
    int heOverride = 0;
    if (PE_parse_boot_argn("be201_he", &heOverride, sizeof(heOverride)))
        requestHE = heOverride == 1;
    fHalService->get80211Controller()->ic_userflags &= ~IEEE80211_F_HEON;
    if (requestHE)
        fHalService->get80211Controller()->ic_userflags |= IEEE80211_F_HEON;
    pciNub->setProperty("BE201HERequested", requestHE);
    pciNub->setProperty("BE201ProtocolLimit", requestHE ?
        "a/b/g/n/ac; HE <=80MHz requested; EHT/6GHz/MLO disabled" :
        "a/b/g/n/ac; HE/EHT disabled");
#endif

    ItlStartupStage(pciNub, "hal-attach");
    if (!fHalService->attach(pciNub)) {
        ItlStartupFailure(pciNub, "hal-attach", kIOReturnError);
        XYLog("attach fail\n");
        super::stop(pciNub);
        releaseAll();
        return false;
    }
    ItlStartupStage(pciNub, "hal-attach-ready");
    ItlStartupStage(pciNub, "watchdog-workloop-create");
    fWatchdogWorkLoop = IOWorkLoop::workLoop();
    if (fWatchdogWorkLoop == NULL) {
        ItlStartupFailure(pciNub, "watchdog-workloop-create", kIOReturnNoResources);
        XYLog("init watchdog workloop fail\n");
        fHalService->detach(pciNub);
        super::stop(pciNub);
        releaseAll();
        return false;
    }
    ItlStartupStage(pciNub, "watchdog-timer-create");
    watchdogTimer = IOTimerEventSource::timerEventSource(this, OSMemberFunctionCast(IOTimerEventSource::Action, this, &AirportItlwm::watchdogAction));
    if (!watchdogTimer) {
        ItlStartupFailure(pciNub, "watchdog-timer-create", kIOReturnNoResources);
        XYLog("init watchdog fail\n");
        fHalService->detach(pciNub);
        super::stop(pciNub);
        releaseAll();
        return false;
    }
    const IOReturn watchdogAddResult = fWatchdogWorkLoop->addEventSource(watchdogTimer);
    pciNub->setProperty("ItlwmStartupWatchdogAddResult", static_cast<UInt32>(watchdogAddResult), 32);
    if (watchdogAddResult != kIOReturnSuccess) {
        ItlStartupFailure(pciNub, "watchdog-timer-add", watchdogAddResult);
        fHalService->detach(pciNub);
        super::stop(provider);
        releaseAll();
        return false;
    }
    ItlStartupStage(pciNub, "scan-timer-create");
    scanSource = IOTimerEventSource::timerEventSource(this, &fakeScanDone);
#ifdef AIRPORT_WCL
    const IOReturn scanAddResult = scanSource ? _fWorkloop->addEventSource(scanSource) : kIOReturnNoResources;
    pciNub->setProperty("ItlwmStartupScanAddResult", static_cast<UInt32>(scanAddResult), 32);
    if (!scanSource || scanAddResult != kIOReturnSuccess) {
        ItlStartupFailure(pciNub, "scan-timer-create", scanAddResult);
        super::stop(provider);
        releaseAll();
        return false;
    }
#else
    _fWorkloop->addEventSource(scanSource);
#endif
    scanSource->enable();

    ItlStartupStage(pciNub, "skywalk-init");
    fNetIf = new AirportItlwmSkywalkInterface;
#ifdef AIRPORT_WCL
    if (!fNetIf || !static_cast<AirportItlwmSkywalkInterface *>(fNetIf)->init(this)) {
#else
    if (!fNetIf->init(this)) {
#endif
        ItlStartupFailure(pciNub, "skywalk-init", kIOReturnError);
        XYLog("Skywalk interface init fail\n");
        super::stop(provider);
        releaseAll();
        return false;
    }
    fNetIf->setInterfaceRole(1);
    fNetIf->setInterfaceId(1);

#ifndef AIRPORT_WCL
    ItlStartupStage(pciNub, "corecapture-init");
    if (!initCCLogs()) {
        ItlStartupFailure(pciNub, "corecapture-init", kIOReturnError);
        XYLog("CCLog init fail\n");
        super::stop(provider);
        releaseAll();
        return false;
    }
#endif
    ItlStartupStage(pciNub, "skywalk-service-attach");
    if (!fNetIf->attach(this)) {
        ItlStartupFailure(pciNub, "skywalk-service-attach", kIOReturnError);
        XYLog("attach to service fail\n");
        super::stop(provider);
        releaseAll();
        return false;
    }
    ItlStartupStage(pciNub, "skywalk-controller-attach");
    if (!attachInterface(fNetIf, this)) {
        ItlStartupFailure(pciNub, "skywalk-controller-attach", kIOReturnError);
        XYLog("attach to interface fail\n");
        super::stop(provider);
        releaseAll();
        return false;
    }
    ItlStartupStage(pciNub, "bsd-interface-attach");
    if (!IONetworkController::attachInterface((IONetworkInterface **)&bsdInterface,
#ifdef AIRPORT_WCL
                                             false
#else
                                             true
#endif
                                             )) {
        ItlStartupFailure(pciNub, "bsd-interface-attach", kIOReturnError);
        XYLog("attach to IONetworkController interface fail\n");
        super::stop(provider);
        releaseAll();
        return false;
    }
    ItlStartupStage(pciNub, "skywalk-registration-init");
    memset(&registInfo, 0, sizeof(registInfo));
    if (!fNetIf->initRegistrationInfo(&registInfo, 1, sizeof(registInfo))) {
        ItlStartupFailure(pciNub, "skywalk-registration-init", kIOReturnError);
        XYLog("initRegistrationInfo fail\n");
        super::stop(provider);
        releaseAll();
        return false;
    }
#ifdef AIRPORT_WCL
    ItlStartupStage(pciNub, "skywalk-registration-allocate");
    fNetIf->mExpansionData->fRegistrationInfo = (struct IOSkywalkNetworkInterface::RegistrationInfo *)IOMalloc(sizeof(struct IOSkywalkNetworkInterface::RegistrationInfo));
    fNetIf->mExpansionData2->fRegistrationInfo = (struct IOSkywalkEthernetInterface::RegistrationInfo *)IOMalloc(sizeof(struct IOSkywalkEthernetInterface::RegistrationInfo));
    if (!fNetIf->mExpansionData->fRegistrationInfo || !fNetIf->mExpansionData2->fRegistrationInfo) {
        ItlStartupFailure(pciNub, "skywalk-registration-allocate", kIOReturnNoMemory);
        super::stop(provider);
        releaseAll();
        return false;
    }
    memcpy(fNetIf->mExpansionData->fRegistrationInfo, &registInfo, sizeof(registInfo));
    memcpy(fNetIf->mExpansionData2->fRegistrationInfo, &registInfo, sizeof(registInfo));
    if (fNetIf->getInterfaceRole() == 1)
        fNetIf->deferBSDAttach(true);
    ItlStartupStage(pciNub, "skywalk-start");
    if (!fNetIf->start(this)) {
        ItlStartupFailure(pciNub, "skywalk-start", kIOReturnError);
        super::stop(provider);
        releaseAll();
        return false;
    }

#else
    ItlStartupStage(pciNub, "skywalk-registration-init-second");
    if (!fNetIf->initRegistrationInfo(&registInfo, 1, sizeof(registInfo))) {
        ItlStartupFailure(pciNub, "skywalk-registration-init-second", kIOReturnError);
        XYLog("initRegistrationInfo fail\n");
        super::stop(provider);
        releaseAll();
        return false;
    }
    fNetIf->mExpansionData->fRegistrationInfo = (struct IOSkywalkNetworkInterface::RegistrationInfo *)IOMalloc(sizeof(struct IOSkywalkNetworkInterface::RegistrationInfo));
    fNetIf->mExpansionData2->fRegistrationInfo = (struct IOSkywalkEthernetInterface::RegistrationInfo *)IOMalloc(sizeof(struct IOSkywalkEthernetInterface::RegistrationInfo));
    memcpy(fNetIf->mExpansionData->fRegistrationInfo, &registInfo, sizeof(registInfo));
    memcpy(fNetIf->mExpansionData2->fRegistrationInfo, &registInfo, sizeof(registInfo));
    if (fNetIf->getInterfaceRole() == 1)
        fNetIf->deferBSDAttach(true);
    fNetIf->start(this);

#endif
    ItlStartupStage(pciNub, "network-publish");
    setLinkStatus(kIONetworkLinkValid);
    if (TAILQ_EMPTY(&fHalService->get80211Controller()->ic_ess))
        fHalService->get80211Controller()->ic_flags |= IEEE80211_F_AUTO_JOIN;
#ifdef AIRPORT_WCL
    bsdInterface->registerService();
    registerAWDLArmControl();
    startAWDLAuto();
#endif
    registerService();
    ItlStartupStage(pciNub, "ready");
    ItlStartupResult(pciNub, "ready");
    return true;
}

void AirportItlwm::stop(IOService *provider)
{
#ifdef AIRPORT_WCL
    stopAWDLInterface();
#endif
    XYLog("%s\n", __PRETTY_FUNCTION__);XYLog("%s\n", __PRETTY_FUNCTION__);
    struct _ifnet *ifp = &fHalService->get80211Controller()->ic_ac.ac_if;
#ifdef AIRPORT_WCL
    if (fNetIf)
        static_cast<AirportItlwmSkywalkInterface *>(fNetIf)->stopWCL();
#endif
    super::stop(provider);
    disableAdapter(bsdInterface);
    setLinkStatus(kIONetworkLinkValid);
    fHalService->detach(pciNub);
    ether_ifdetach(ifp);
    detachInterface(fNetIf, true);
    OSSafeReleaseNULL(fNetIf);
    releaseAll();
}

void AirportItlwm::free()
{
    XYLog("%s\n", __PRETTY_FUNCTION__);
    if (fHalService != NULL) {
        fHalService->release();
        fHalService = NULL;
    }
    if (syncFrameTemplate != NULL && syncFrameTemplateLength > 0) {
        IOFree(syncFrameTemplate, syncFrameTemplateLength);
        syncFrameTemplateLength = 0;
        syncFrameTemplate = NULL;
    }
    if (roamProfile != NULL) {
        IOFree(roamProfile, sizeof(struct apple80211_roam_profile_band_data));
        roamProfile = NULL;
    }
    if (btcProfile != NULL) {
        IOFree(btcProfile, sizeof(struct apple80211_btc_profiles_data));
        btcProfile = NULL;
    }
    super::free();
}

bool AirportItlwm::createWorkQueue()
{
    XYLog("%s %d\n", __FUNCTION__, _fWorkloop != 0);
    return _fWorkloop != 0;
}

#ifdef AIRPORT_WCL
IOWorkLoop *AirportItlwm::getWorkLoop() const
{
    return _fWorkloop;
}
#endif

IO80211WorkQueue *AirportItlwm::getWorkQueue()
#ifdef AIRPORT_WCL
const
#endif
{
    return _fWorkloop;
}

#ifdef AIRPORT_WCL
CommonFaultReporter *AirportItlwm::getFaultReporterFromDriver()
#else
void *AirportItlwm::getFaultReporterFromDriver()
#endif
{
    return driverFaultReporter;
}

IOReturn AirportItlwm::enable(IO80211SkywalkInterface *netif)
{
    XYLog("%s\n", __PRETTY_FUNCTION__);
    super::enable(netif);
    _fCommandGate->enable();
    if (power_state)
        enableAdapter(bsdInterface);
    return kIOReturnSuccess;
}

IOReturn AirportItlwm::disable(IO80211SkywalkInterface *netif)
{
    XYLog("%s\n", __PRETTY_FUNCTION__);
    super::disable(netif);
    setLinkStatus(kIONetworkLinkValid);
    return kIOReturnSuccess;
}

bool AirportItlwm::configureInterface(IONetworkInterface *netif)
{
    IONetworkData *nd;
    struct _ifnet *ifp = &fHalService->get80211Controller()->ic_ac.ac_if;

    if (super::configureInterface(netif) == false) {
        XYLog("super failed\n");
        return false;
    }

    nd = netif->getParameter(kIONetworkStatsKey);
    if (!nd || !(fpNetStats = (IONetworkStats *)nd->getBuffer())) {
        XYLog("network statistics buffer unavailable?\n");
        return false;
    }
    ifp->netStat = fpNetStats;
    ether_ifattach(ifp, OSDynamicCast(IOEthernetInterface, netif));
    fpNetStats->collisions = 0;
#ifdef __PRIVATE_SPI__
#ifdef AIRPORT_WCL
    if (netif->configureOutputPullModel(fHalService->getDriverInfo()->getTxQueueSize(),
        kIONetworkWorkLoopSynchronous, 0,
        IOEthernetInterface::kOutputPacketSchedulingModelNormal, 0) != kIOReturnSuccess)
        return false;
#else
    netif->configureOutputPullModel(fHalService->getDriverInfo()->getTxQueueSize(), 0, 0, IOEthernetInterface::kOutputPacketSchedulingModelNormal, 0);
#endif
#endif

    return true;
}

IONetworkInterface *AirportItlwm::createInterface()
{
    AirportItlwmEthernetInterface *netif = new AirportItlwmEthernetInterface;
    if (!netif)
        return NULL;
    if (!netif->initWithSkywalkInterfaceAndProvider(this, fNetIf)) {
        netif->release();
        return NULL;
    }
    return netif;
}

bool AirportItlwm::createMediumTables(const IONetworkMedium **primary)
{
    IONetworkMedium    *medium;

    OSDictionary *mediumDict = OSDictionary::withCapacity(2);
    if (mediumDict == NULL) {
        XYLog("Cannot allocate OSDictionary\n");
        return false;
    }

    medium = IONetworkMedium::medium(kIOMediumIEEE80211, 54000000);
    IONetworkMedium::addMedium(mediumDict, medium);
    medium->release();
    if (primary) {
        *primary = medium;
    }
    medium = IONetworkMedium::medium(kIOMediumIEEE80211None, 0);
    IONetworkMedium::addMedium(mediumDict, medium);
    medium->release();

    bool result = publishMediumDictionary(mediumDict);
    if (!result) {
        XYLog("Cannot publish medium dictionary!\n");
    }

    mediumDict->release();
    return result;
}

IOReturn AirportItlwm::selectMedium(const IONetworkMedium *medium) {
    setSelectedMedium(medium);
    return kIOReturnSuccess;
}

bool AirportItlwm::
setLinkStatus(UInt32 status, const IONetworkMedium * activeMedium, UInt64 speed, OSData * data)
{
    struct _ifnet *ifq = &fHalService->get80211Controller()->ic_ac.ac_if;
    if (status == currentStatus) {
        return true;
    }
    bool ret = super::setLinkStatus(status, activeMedium, speed, data);
    currentStatus = status;
    if (fNetIf) {
        if (status & kIONetworkLinkActive) {
#ifdef __PRIVATE_SPI__
            bsdInterface->startOutputThread();
#endif
            getCommandGate()->runAction(setLinkStateGated, (void *)kIO80211NetworkLinkUp, (void *)0);
//            fNetIf->setLinkQualityMetric(100);
        } else if (!(status & kIONetworkLinkNoNetworkChange)) {
#ifdef __PRIVATE_SPI__
            bsdInterface->stopOutputThread();
            bsdInterface->flushOutputQueue();
#endif
            ifq_flush(&ifq->if_snd);
            mq_purge(&fHalService->get80211Controller()->ic_mgtq);
            getCommandGate()->runAction(setLinkStateGated, (void *)kIO80211NetworkLinkDown, (void *)fHalService->get80211Controller()->ic_deauth_reason);
        }
    }
    return ret;
}

IOReturn AirportItlwm::
setLinkStateGated(OSObject *target, void *arg0, void *arg1, void *arg2, void *arg3)
{
    AirportItlwm *that = OSDynamicCast(AirportItlwm, target);
#ifdef AIRPORT_WCL
    that->bsdInterface->setLinkState((IO80211LinkState)(uint64_t)arg0);
    static_cast<AirportItlwmSkywalkInterface *>(that->fNetIf)->handleWCLLink(
        (IO80211LinkState)(uint64_t)arg0 == kIO80211NetworkLinkUp);
    return kIOReturnSuccess;
#else
    IOReturn ret = that->fNetIf->setLinkState((IO80211LinkState)(uint64_t)arg0, (unsigned int)(uint64_t)arg1);
    that->fNetIf->setRunningState((IO80211LinkState)(uint64_t)arg0 == kIO80211NetworkLinkUp);
    that->fNetIf->postMessage(APPLE80211_M_LINK_CHANGED, NULL, 0, false);
    that->fNetIf->postMessage(APPLE80211_M_BSSID_CHANGED, NULL, 0, false);
    that->fNetIf->postMessage(APPLE80211_M_SSID_CHANGED, NULL, 0, false);
    if ((IO80211LinkState)(uint64_t)arg0 == kIO80211NetworkLinkUp) {
        that->fNetIf->reportLinkStatus(3, 0x80);
    } else {
        that->fNetIf->reportLinkStatus(1, 0);
    }
    that->bsdInterface->setLinkState((IO80211LinkState)(uint64_t)arg0);
    return ret;
#endif
}

#ifdef __PRIVATE_SPI__
IOReturn AirportItlwm::outputStart(IONetworkInterface *interface, IOOptionBits options)
{
    struct _ifnet *ifp = &fHalService->get80211Controller()->ic_ac.ac_if;
    mbuf_t m = NULL;
#ifdef AIRPORT_WCL
    if (!ifp->if_snd.queue)
        return kIOReturnNoResources;
    if (!ifq_empty(&ifp->if_snd))
        (*ifp->if_start)(ifp);
    const uint32_t capacity = ifp->if_snd.queue->getCapacity();
    const uint32_t queued = ifq_len(&ifp->if_snd);
    if (ifq_is_oactive(&ifp->if_snd) || queued >= capacity)
        return kIOReturnNoResources;
    const uint32_t count = MIN(32U, capacity - queued);
    if (interface->dequeueOutputPackets(count, &m) != kIOReturnSuccess || !m)
        return kIOReturnSuccess;
    while (m) {
        mbuf_t next = mbuf_nextpkt(m);
        mbuf_setnextpkt(m, NULL);
        enqueuePacket(m);
        m = next;
    }
    (*ifp->if_start)(ifp);
    if (ifq_is_oactive(&ifp->if_snd))
        return kIOReturnNoResources;
    return kIOReturnSuccess;
#else
    if (ifq_is_oactive(&ifp->if_snd))
        return kIOReturnNoResources;
    while (kIOReturnSuccess == interface->dequeueOutputPackets(1, &m)) {
        if (outputPacket(m, NULL)!= kIOReturnOutputSuccess ||
            ifq_is_oactive(&ifp->if_snd))
            return kIOReturnNoResources;
    }
    return kIOReturnSuccess;
#endif
}

IOReturn AirportItlwm::networkInterfaceNotification(
                    IONetworkInterface * interface,
                    uint32_t              type,
                    void *                  argument )
{
    XYLog("%s\n", __FUNCTION__);
    return kIOReturnSuccess;
}
#endif

extern const char* hexdump(uint8_t *buf, size_t len);

#ifdef AIRPORT_WCL
UInt32 AirportItlwm::outputPacket(mbuf_t m, void *param)
{
    IOReturn status = _fCommandGate ? _fCommandGate->runAction(outputPacketGated, m) : kIOReturnNotReady;
    if (status != kIOReturnOutputSuccess && status != kIOReturnOutputDropped) {
        if (m && mbuf_type(m) != MBUF_TYPE_FREE)
            freePacket(m);
        return kIOReturnOutputDropped;
    }
    return status;
}

IOReturn AirportItlwm::outputPacketGated(OSObject *owner, void *arg0, void *, void *, void *)
{
    auto self = static_cast<AirportItlwm *>(owner);
    UInt32 status = self->enqueuePacket(static_cast<mbuf_t>(arg0));
    auto ifp = &self->fHalService->get80211Controller()->ic_ac.ac_if;
    if (ifp->if_snd.queue)
        (*ifp->if_start)(ifp);
    return status;
}

UInt32 AirportItlwm::enqueuePacket(mbuf_t m)
{
    auto ic = fHalService->get80211Controller();
    auto ifp = &ic->ic_ac.ac_if;
    if (ic->ic_state == IEEE80211_S_RUN && ifp->if_snd.queue &&
        m && mbuf_type(m) != MBUF_TYPE_FREE && (mbuf_flags(m) & MBUF_PKTHDR) &&
        ifp->if_snd.queue->lockEnqueue(m))
        return kIOReturnOutputSuccess;
    if (ifp->netStat)
        ++ifp->netStat->outputErrors;
    if (m && mbuf_type(m) != MBUF_TYPE_FREE)
        freePacket(m);
    return kIOReturnOutputDropped;
}
#else
UInt32 AirportItlwm::outputPacket(mbuf_t m, void *param)
{
//    XYLog("%s\n", __FUNCTION__);
    IOReturn ret = kIOReturnOutputSuccess;
    struct _ifnet *ifp = &fHalService->get80211Controller()->ic_ac.ac_if;
    
    if (fHalService->get80211Controller()->ic_state != IEEE80211_S_RUN || ifp->if_snd.queue == NULL) {
        if (m && mbuf_type(m) != MBUF_TYPE_FREE)
            freePacket(m);
        return kIOReturnOutputDropped;
    }
    if (m == NULL) {
        XYLog("%s m==NULL!!\n", __FUNCTION__);
        ifp->netStat->outputErrors++;
        ret = kIOReturnOutputDropped;
    }
    if (!(mbuf_flags(m) & MBUF_PKTHDR) ){
        XYLog("%s pkthdr is NULL!!\n", __FUNCTION__);
        ifp->netStat->outputErrors++;
        freePacket(m);
        ret = kIOReturnOutputDropped;
    }
    if (mbuf_type(m) == MBUF_TYPE_FREE) {
        XYLog("%s mbuf is FREE!!\n", __FUNCTION__);
        ifp->netStat->outputErrors++;
        ret = kIOReturnOutputDropped;
    }
    size_t len = mbuf_len(m);
    ether_header_t *eh = (ether_header_t *)mbuf_data(m);
    if (len >= sizeof(ether_header_t) && eh->ether_type == htons(ETHERTYPE_PAE)) { // EAPOL packet
        const char* dump = hexdump((uint8_t*)mbuf_data(m), len);
        XYLog("output EAPOL packet, len: %zu, data: %s\n", len, dump ? dump : "Failed to allocate memory");
        if (dump)
            IOFree((void*)dump, 3 * len + 1);
    }
    if (!ifp->if_snd.queue->lockEnqueue(m)) {
        freePacket(m);
        ret = kIOReturnOutputDropped;
    }
    (*ifp->if_start)(ifp);
    return ret;
}
#endif

const OSString * AirportItlwm::newVendorString() const
{
    return OSString::withCString("Apple");
}

const OSString * AirportItlwm::newModelString() const
{
    return OSString::withCString(fHalService->getDriverInfo()->getFirmwareName());
}

IOReturn AirportItlwm::getHardwareAddress(IOEthernetAddress *addrP)
{
    if (IEEE80211_ADDR_EQ(etheranyaddr, fHalService->get80211Controller()->ic_myaddr))
        return kIOReturnError;
    else {
        IEEE80211_ADDR_COPY(addrP, fHalService->get80211Controller()->ic_myaddr);
        return kIOReturnSuccess;
    }
}

IOReturn AirportItlwm::setHardwareAddress(const void *addrP, UInt32 addrBytes)
{
    if (!fNetIf || !addrP)
        return kIOReturnError;
#ifdef AIRPORT_WCL
    const UInt8 *address = static_cast<const UInt8 *>(addrP);
    auto ic = fHalService->get80211Controller();
    bool initializing = (ic->ic_if.if_flags & IFF_UP) && !(ic->ic_if.if_flags & IFF_RUNNING);
    auto update = AirportWCL::planMacUpdate(ic->ic_myaddr, address, addrBytes, initializing);
    if (update == AirportWCL::MacUpdate::Invalid)
        return kIOReturnBadArgument;
    if (update == AirportWCL::MacUpdate::Busy) {
        return kIOReturnBusy;
    }
    if (!bsdInterface || !bsdInterface->getIfnet())
        return kIOReturnNotReady;
    // WCL calls this directly, bypassing IOEthernetInterface's normal MAC ioctl.
    // Update the BSD address used by DHCP/ARP as well as the firmware address.
    errno_t error = ifnet_set_lladdr(bsdInterface->getIfnet(), address, addrBytes);
    if (error)
        return kIOReturnError;
    bsdInterface->setProperty(kIOMACAddress, const_cast<UInt8 *>(address), addrBytes);
    // WCL replays the current address after every driver-available notification.
    // Keep BSD synchronized, but do not restart firmware for a replay.
    if (update == AirportWCL::MacUpdate::Unchanged) {
        return kIOReturnSuccess;
    }
    /*
     * Keep the authoritative 802.11 address in sync. The HAL uses ic_myaddr
     * for probe requests, scan configuration and the station/MAC context, and
     * a stale value makes every WCL replay look like a fresh change, which
     * restarts the firmware over and over and aborts joins with STOPPED.
     */
    IEEE80211_ADDR_COPY(ic->ic_myaddr, address);
#endif
    if_setlladdr(&fHalService->get80211Controller()->ic_ac.ac_if, (const UInt8 *)addrP);
#ifdef AIRPORT_WCL
    /*
     * MLD firmware takes our address from MAC_CONFIG/LINK_CONFIG at the next
     * authentication and from each probe request, so no firmware restart is
     * needed (Linux only re-adds the interface context). The restart made
     * IO80211 reject the association that follows a private-MAC change.
     */
    if ((ic->ic_if.if_flags & IFF_RUNNING) && !fHalService->macChangeNeedsRestart()) {
        ++macChangesWithoutRestart;
        if (pciNub)
            pciNub->setProperty("ItlwmMacChangeNoRestart", macChangesWithoutRestart, 32);
        return kIOReturnSuccess;
    }
    if (ic->ic_if.if_flags & IFF_RUNNING) {
        ic->ic_wcl_mac_reconfig = true;
        if (pciNub)
            pciNub->setProperty("ItlwmMacReconfigSet", static_cast<UInt32>(1), 32);
#else
    if (fHalService->get80211Controller()->ic_state > IEEE80211_S_INIT) {
#endif
        fHalService->disable(bsdInterface);
        fHalService->enable(bsdInterface);
    }
    return kIOReturnSuccess;
}

UInt32 AirportItlwm::getFeatures() const
{
    return fHalService->getDriverInfo()->supportedFeatures();
}

IOReturn AirportItlwm::setPromiscuousMode(IOEnetPromiscuousMode mode)
{
    return kIOReturnSuccess;
}

IOReturn AirportItlwm::setMulticastMode(IOEnetMulticastMode mode)
{
    return kIOReturnSuccess;
}

IOReturn AirportItlwm::setMulticastList(IOEthernetAddress* addr, UInt32 len)
{
    return fHalService->getDriverController()->setMulticastList(addr, len);
}

IOReturn AirportItlwm::getPacketFilters(const OSSymbol *group, UInt32 *filters) const
{
    IOReturn    rtn = kIOReturnSuccess;
    if (group == gIOEthernetWakeOnLANFilterGroup && magicPacketSupported)
        *filters = kIOEthernetWakeOnMagicPacket;
    else if (group == gIONetworkFilterGroup)
        *filters = kIOPacketFilterMulticast | kIOPacketFilterPromiscuous;
    else
        rtn = IOEthernetController::getPacketFilters(group, filters);
    return rtn;
}

SInt32 AirportItlwm::
enableFeature(IO80211FeatureCode code, void *data)
{
    if (code == kIO80211Feature80211n) {
        return 0;
    }
    return 102;
}

bool AirportItlwm::getLogPipes(CCPipe**logPipe, CCPipe**eventPipe, CCPipe**snapshotsPipe)
{
    bool ret = false;
    if (logPipe) {
        *logPipe = driverLogPipe;
        ret = true;
    }
    if (eventPipe) {
        *eventPipe = driverDataPathPipe;
        ret = true;
    }
    if (snapshotsPipe) {
        *snapshotsPipe = driverSnapshotsPipe;
        ret = true;
    }
    return ret;
}

#define APPLE80211_CAPA_AWDL_FEATURE_AUTO_UNLOCK    0x00000004
#define APPLE80211_CAPA_AWDL_FEATURE_WOW            0x00000080

IOReturn AirportItlwm::
getCARD_CAPABILITIES(OSObject *object,
                                     struct apple80211_capability_data *cd)
{
    uint32_t caps = fHalService->get80211Controller()->ic_caps;
    memset(cd, 0, sizeof(struct apple80211_capability_data));

    if (caps & IEEE80211_C_WEP)
        cd->capabilities[0] |= 1 << APPLE80211_CAP_WEP;
    if (caps & IEEE80211_C_RSN)
        cd->capabilities[0] |= 1 << APPLE80211_CAP_TKIP | 1 << APPLE80211_CAP_AES_CCM;
    // Disable not implemented capabilities
    // if (caps & IEEE80211_C_PMGT)
    //     cd->capabilities[0] |= 1 << APPLE80211_CAP_PMGT;
    // if (caps & IEEE80211_C_IBSS)
    //     cd->capabilities[0] |= 1 << APPLE80211_CAP_IBSS;
    // if (caps & IEEE80211_C_HOSTAP)
    //     cd->capabilities[0] |= 1 << APPLE80211_CAP_HOSTAP;
    // AES not enabled, like on Apple cards

    if (caps & IEEE80211_C_SHSLOT)
        cd->capabilities[1] |= 1 << (APPLE80211_CAP_SHSLOT - 8);
    if (caps & IEEE80211_C_SHPREAMBLE)
        cd->capabilities[1] |= 1 << (APPLE80211_CAP_SHPREAMBLE - 8);
    if (caps & IEEE80211_C_RSN)
        cd->capabilities[1] |= 1 << (APPLE80211_CAP_WPA1 - 8) | 1 << (APPLE80211_CAP_WPA2 - 8) | 1 << (APPLE80211_CAP_TKIPMIC - 8);
    // Disable not implemented capabilities
    // if (caps & IEEE80211_C_TXPMGT)
    //     cd->capabilities[1] |= 1 << (APPLE80211_CAP_TXPMGT - 8);
    // if (caps & IEEE80211_C_MONITOR)
    //     cd->capabilities[1] |= 1 << (APPLE80211_CAP_MONITOR - 8);
    // WPA not enabled, like on Apple cards

    cd->version = APPLE80211_VERSION;
#ifdef AIRPORT_WCL
    // WPA2 can use TKIP for group traffic even when unicast uses CCMP.
    // net80211 handles TKIP/MIC in software; hiding it makes Apple80211
    // reject these networks before it submits an association request.
    cd->capabilities[0] = (caps & IEEE80211_C_RSN) ?
        (1 << APPLE80211_CAP_AES_CCM) | (1 << APPLE80211_CAP_TKIP) : 0;
    cd->capabilities[1] &= ~(1 << (APPLE80211_CAP_WPA1 - 8));
    cd->capabilities[5] = 0x40; // Scan completion events.
    cd->capabilities[2] = (1 << (APPLE80211_CAP_WME - 16)) |
        (1 << (APPLE80211_CAP_SHORT_GI_40MHZ - 16)) |
        (1 << (APPLE80211_CAP_SHORT_GI_20MHZ - 16));
    // Tahoe WCLDeviceConfiguration::isHeSupported reads byte 17, bit 7.
    // WCL uses this capability together with the BSS HE IE for PHY reporting.
    if (caps & IEEE80211_C_HE)
        cd->capabilities[17] |= 0x80;
    // Capability bit 32 is what wifip2pd checks before VIRTUAL_IF_CREATE with role 6.
    // be201_awdl_vif alone stays silent until armed, so a normal boot behaves as if it were off.
    if (ItlDiagnosticFlag("be201_awdl_if") || (ItlAwdlFlag("be201_awdl_vif") && awdlVifCapabilityArmed()))
        cd->capabilities[4] |= 0x01;
    // The AWDL manager tests these through its cached copy: capabilities[0] bit 2 in configure,
    // and capabilities[3] bit 5 as dual band; without that AWDL stays on 2.4 GHz.
    if (ItlAwdlFlag("be201_awdl_vif") && awdlVifCapabilityArmed()) {
        cd->capabilities[0] |= 0x04;
        cd->capabilities[3] |= 0x20;
    }
#else
    cd->capabilities[2] = 0xFF; // BURST, WME, SHORT_GI_40MHZ, SHORT_GI_20MHZ, WOW, TSN, ?, ?
    cd->capabilities[3] = 0x2B;
    cd->capabilities[5] = 0x40;
    cd->capabilities[6] = (
//                           1 |    //MFP capable
                           0x8 |
                           0x4 |
                           0x80
                           );
    *(uint16_t *)&cd->capabilities[8] = 0x201;
//
//    cd->capabilities[2] |= 0x10;
//    cd->capabilities[5] |= 0x1;
//
//    cd->capabilities[2] |= 0x2;
//
//    cd->capabilities[3] |= 0x20;
//
//    cd->capabilities[0] |= 0x80;
//
//    cd->capabilities[3] |= 0x80;
//    cd->capabilities[4] |= 0x4;
//
//    cd->capabilities[4] |= 0x1;
//    cd->capabilities[3] |= 0x1;
//    cd->capabilities[6] |= 0x8;
//
//    cd->capabilities[3] |= 3;
//    cd->capabilities[4] |= 2;
//    cd->capabilities[6] |= 0x10;
//    cd->capabilities[5] |= 0x20;
//    cd->capabilities[5] |= 0x80;
//
//    if (cd->capabilities[6] & 0x20) {
//        cd->capabilities[2] |= 8;
//    }
//    cd->capabilities[5] |= 8;
//    cd->capabilities[8] |= 2;
//
//    cd->capabilities[11] |= (2 | 4 | 8 | 0x10 | 0x20 | 0x40 | 0x80);

#endif
    return kIOReturnSuccess;
}

IOReturn AirportItlwm::
getDRIVER_VERSION(OSObject *object,
                                  struct apple80211_version_data *hv)
{
    if (!hv)
        return kIOReturnError;
    hv->version = APPLE80211_VERSION;
    snprintf(hv->string, sizeof(hv->string), "itlwm: %s%s fw: %s", ITLWM_VERSION, GIT_COMMIT, fHalService->getDriverInfo()->getFirmwareVersion());
    hv->string_len = strlen(hv->string);
    return kIOReturnSuccess;
}

IOReturn AirportItlwm::
getHARDWARE_VERSION(OSObject *object,
                                    struct apple80211_version_data *hv)
{
    if (!hv)
        return kIOReturnError;
    hv->version = APPLE80211_VERSION;
    strncpy(hv->string, fHalService->getDriverInfo()->getFirmwareVersion(), sizeof(hv->string));
    hv->string_len = strlen(fHalService->getDriverInfo()->getFirmwareVersion());
    return kIOReturnSuccess;
}

IOReturn AirportItlwm::
getCOUNTRY_CODE(OSObject *object,
                                struct apple80211_country_code_data *cd)
{
    char user_override_cc[3];
    const char *cc_fw = fHalService->getDriverInfo()->getFirmwareCountryCode();

    if (!cd)
        return kIOReturnError;
    cd->version = APPLE80211_VERSION;
    memset(user_override_cc, 0, sizeof(user_override_cc));
    PE_parse_boot_argn("itlwm_cc", user_override_cc, 3);
    /* user_override_cc > firmware_cc > geo_location_cc */
    strncpy((char*)cd->cc, user_override_cc[0] ? user_override_cc : ((cc_fw[0] == 'Z' && cc_fw[1] == 'Z' && geo_location_cc[0]) ? geo_location_cc : cc_fw), sizeof(cd->cc));
    return kIOReturnSuccess;
}

IOReturn AirportItlwm::
setCOUNTRY_CODE(OSObject *object, struct apple80211_country_code_data *data)
{
#ifdef AIRPORT_WCL
    if (!data)
        return kIOReturnBadArgument;
    if (data->cc[0] != 'x' && data->cc[0] != 'X' &&
        memcmp(geo_location_cc, data->cc, sizeof(geo_location_cc)) != 0) {
        memcpy(geo_location_cc, data->cc, sizeof(geo_location_cc));
        if (fNetIf)
            static_cast<AirportItlwmSkywalkInterface *>(fNetIf)->handleWCLEvent(
                IEEE80211_EVT_COUNTRY_CODE_UPDATE, nullptr);
    }
#else
    XYLog("%s cc=%s\n", __FUNCTION__, data->cc);
    if (data && data->cc[0] != 120 && data->cc[0] != 88) {
        memcpy(geo_location_cc, data->cc, sizeof(geo_location_cc));
        fNetIf->postMessage(APPLE80211_M_COUNTRY_CODE_CHANGED, NULL, 0, 0);
    }
#endif
    return kIOReturnSuccess;
}

IOReturn AirportItlwm::
getPOWER(OSObject *object,
                         struct apple80211_power_data *pd)
{
    if (!pd)
        return kIOReturnError;
    pd->version = APPLE80211_VERSION;
    pd->num_radios = 4;
    pd->power_state[0] = power_state;
    pd->power_state[1] = power_state;
    pd->power_state[2] = power_state;
    pd->power_state[3] = power_state;
    return kIOReturnSuccess;
}

IOReturn AirportItlwm::
setPOWER(OSObject *object,
                         struct apple80211_power_data *pd)
{
#ifdef AIRPORT_WCL
    if (!pd)
        return kIOReturnError;
    IOLog("itlwm: setPOWER: num_radios[%d]  power_state(0:%u  1:%u  2:%u  3:%u)\n", pd->num_radios, pd->power_state[0], pd->power_state[1], pd->power_state[2], pd->power_state[3]);
    if (pd->num_radios > 0) {
        bool isRunning = (fHalService->get80211Controller()->ic_ac.ac_if.if_flags & IFF_RUNNING) != 0;
        if (pd->power_state[0] == 0) {
            fHalService->get80211Controller()->ic_wcl_mac_reconfig = false;
            changePowerStateToPriv(kPowerStateOff);
            if (fHalService->get80211Controller()->ic_ac.ac_if.if_flags & (IFF_UP | IFF_RUNNING)) {
                net80211_ifstats(fHalService->get80211Controller());
                disableAdapter(bsdInterface);
            }
        } else {
            changePowerStateToPriv(kPowerStateOn);
            if (!isRunning)
                enableAdapter(bsdInterface);
        }
        power_state = (pd->power_state[0]);
    }

    return kIOReturnSuccess;
#else
    if (!pd)
        return kIOReturnError;
    IOLog("itlwm: setPOWER: num_radios[%d]  power_state(0:%u  1:%u  2:%u  3:%u)\n", pd->num_radios, pd->power_state[0], pd->power_state[1], pd->power_state[2], pd->power_state[3]);
    if (pd->num_radios > 0) {
        bool isRunning = (fHalService->get80211Controller()->ic_ac.ac_if.if_flags & (IFF_UP | IFF_RUNNING)) != 0;
        if (pd->power_state[0] == 0) {
            changePowerStateToPriv(1);
            if (isRunning) {
                net80211_ifstats(fHalService->get80211Controller());
                disableAdapter(bsdInterface);
            }
        } else {
            changePowerStateToPriv(2);
            if (!isRunning)
                enableAdapter(bsdInterface);
        }
        power_state = (pd->power_state[0]);
    }

    return kIOReturnSuccess;
#endif
}

SInt32 AirportItlwm::apple80211_ioctl(IO80211SkywalkInterface *interface,unsigned long cmd,void *data, bool b1, bool b2)
{
    if (!ml_at_interrupt_context())
        XYLog("%s cmd: %s b1: %d b2: %d\n", __FUNCTION__, convertApple80211IOCTLToString((unsigned int)cmd), b1, b2);
#ifdef AIRPORT_WCL
    if (cmd == APPLE80211_IOC_WCL_EXTENDED_BSS_INFO && interface == fNetIf && interface)
        return static_cast<AirportItlwmSkywalkInterface *>(interface)->getWCL_EXTENDED_BSS_INFO((apple80211_extended_bss_info *)data);
    return kIOReturnUnsupported;
#else
    return super::apple80211_ioctl(interface, cmd, data, b1, b2);
#endif
}

SInt32 AirportItlwm::apple80211SkywalkRequest(UInt request,int cmd,IO80211SkywalkInterface *interface,void *data)
{
    if (!ml_at_interrupt_context())
        XYLog("%s 1 cmd: %s request: %d\n", __FUNCTION__, convertApple80211IOCTLToString(cmd), request);
    if (cmd == APPLE80211_IOC_WCL_EXTENDED_BSS_INFO && interface == fNetIf && interface)
        return static_cast<AirportItlwmSkywalkInterface *>(interface)->getWCL_EXTENDED_BSS_INFO((apple80211_extended_bss_info *)data);
    return kIOReturnUnsupported;
}

SInt32 AirportItlwm::apple80211SkywalkRequest(UInt request,int cmd,IO80211SkywalkInterface *interface,void *data,void *)
{
    if (!ml_at_interrupt_context())
        XYLog("%s 2 cmd: %s request: %d\n", __FUNCTION__, convertApple80211IOCTLToString(cmd), request);
    if (cmd == APPLE80211_IOC_WCL_EXTENDED_BSS_INFO && interface == fNetIf && interface)
        return static_cast<AirportItlwmSkywalkInterface *>(interface)->getWCL_EXTENDED_BSS_INFO((apple80211_extended_bss_info *)data);
    return kIOReturnUnsupported;
}

IOReturn AirportItlwm::enableAdapter(IONetworkInterface *netif)
{
#ifdef AIRPORT_WCL
    IOReturn status = fHalService->enable(netif);
    if (status != kIOReturnSuccess)
        return status;
#else
    fHalService->enable(netif);
#endif
    watchdogTimer->setTimeoutMS(kWatchDogTimerPeriod);
    watchdogTimer->enable();
    return kIOReturnSuccess;
}

void AirportItlwm::disableAdapter(IONetworkInterface *netif)
{
    watchdogTimer->cancelTimeout();
    watchdogTimer->disable();
    fHalService->disable(netif);
}

IOReturn AirportItlwm::
tsleepHandler(OSObject* owner, void* arg0, void* arg1, void* arg2, void* arg3)
{
    AirportItlwm* dev = OSDynamicCast(AirportItlwm, owner);
    if (dev == 0)
        return kIOReturnError;

    if (arg1 == 0) {
        if (_fCommandGate->commandSleep(arg0, THREAD_INTERRUPTIBLE) == THREAD_AWAKENED)
            return kIOReturnSuccess;
        else
            return kIOReturnTimeout;
    } else {
        AbsoluteTime deadline;
        clock_interval_to_deadline((*(int*)arg1), kNanosecondScale, reinterpret_cast<uint64_t*> (&deadline));
        if (_fCommandGate->commandSleep(arg0, deadline, THREAD_INTERRUPTIBLE) == THREAD_AWAKENED)
            return kIOReturnSuccess;
        else
            return kIOReturnTimeout;
    }
}

bool AirportItlwm::initPCIPowerManagment(IOPCIDevice *provider)
{
    UInt16 reg16;

    reg16 = provider->configRead16(kIOPCIConfigCommand);

    reg16 |= ( kIOPCICommandBusMaster       |
               kIOPCICommandMemorySpace     |
               kIOPCICommandMemWrInvalidate );

    reg16 &= ~kIOPCICommandIOSpace;  // disable I/O space

    provider->configWrite16( kIOPCIConfigCommand, reg16 );
    provider->findPCICapability(kIOPCIPowerManagementCapability,
                                &pmPCICapPtr);
    if (pmPCICapPtr) {
        UInt16 pciPMCReg = provider->configRead32( pmPCICapPtr ) >> 16;
        if (pciPMCReg & kPCIPMCPMESupportFromD3Cold)
            magicPacketSupported = true;
        provider->configWrite16((pmPCICapPtr + 4), 0x8000 );
        IOSleep(10);
    }
    return true;
}

static IOPMPowerState powerStateArray[kPowerStateCount] =
{
    {1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {1, kIOPMDeviceUsable, kIOPMPowerOn, kIOPMPowerOn, 0, 0, 0, 0, 0, 0, 0, 0}
};

void AirportItlwm::unregistPM()
{
    if (powerOffThreadCall) {
        thread_call_free(powerOffThreadCall);
        powerOffThreadCall = NULL;
    }
    if (powerOnThreadCall) {
        thread_call_free(powerOnThreadCall);
        powerOnThreadCall = NULL;
    }
}

IOReturn AirportItlwm::setPowerState(unsigned long powerStateOrdinal, IOService *policyMaker)
{
    IOReturn result = IOPMAckImplied;

    if (pmPowerState == powerStateOrdinal)
        return result;
    switch (powerStateOrdinal) {
        case kPowerStateOff:
            if (powerOffThreadCall) {
                retain();
                if (thread_call_enter(powerOffThreadCall))
                    release();
                result = 5000000;
            }
            break;
        case kPowerStateOn:
            if (powerOnThreadCall) {
                retain();
                if (thread_call_enter(powerOnThreadCall))
                    release();
                result = 5000000;
            }
            break;

        default:
            break;
    }
    return result;
}

IOReturn AirportItlwm::setWakeOnMagicPacket(bool active)
{
    magicPacketEnabled = active;
    return kIOReturnSuccess;
}

static void handleSetPowerStateOff(thread_call_param_t param0,
                             thread_call_param_t param1)
{
    AirportItlwm *self = (AirportItlwm *)param0;

    if (param1 == 0)
    {
        self->getCommandGate()->runAction((IOCommandGate::Action)
                                           handleSetPowerStateOff,
                                           (void *) 1);
    }
    else
    {
        self->setPowerStateOff();
        self->release();
    }
}

static void handleSetPowerStateOn(thread_call_param_t param0,
                            thread_call_param_t param1)
{
    AirportItlwm *self = (AirportItlwm *) param0;

    if (param1 == 0)
    {
        self->getCommandGate()->runAction((IOCommandGate::Action)
                                           handleSetPowerStateOn,
                                           (void *) 1);
    }
    else
    {
        self->setPowerStateOn();
        self->release();
    }
}

IOReturn AirportItlwm::registerWithPolicyMaker(IOService *policyMaker)
{
    IOReturn ret;

    pmPowerState = kPowerStateOn;
    pmPolicyMaker = policyMaker;

    powerOffThreadCall = thread_call_allocate(
                                            (thread_call_func_t)handleSetPowerStateOff,
                                            (thread_call_param_t)this);
    powerOnThreadCall  = thread_call_allocate(
                                            (thread_call_func_t)handleSetPowerStateOn,
                                              (thread_call_param_t)this);
    ret = pmPolicyMaker->registerPowerDriver(this,
                                             powerStateArray,
                                             kPowerStateCount);
    return ret;
}

void AirportItlwm::setPowerStateOff()
{
    XYLog("%s\n", __FUNCTION__);
    pmPowerState = kPowerStateOff;
    disableAdapter(bsdInterface);
    pmPolicyMaker->acknowledgeSetPowerState();
}

void AirportItlwm::setPowerStateOn()
{
    XYLog("%s\n", __FUNCTION__);
    pmPowerState = kPowerStateOn;
    pmPolicyMaker->acknowledgeSetPowerState();
}

#ifdef AIRPORT_WCL
/*
 * wifip2pd asks for awdl0 by itself during every boot, so creation must not depend on the
 * boot argument alone: a fault there would leave the Mac unable to start. Root arms one
 * attempt from a running session with sysctl. Kept in RAM, so every boot starts unarmed.
 */
static int be201AwdlVifArm;
static bool be201AwdlVifAttempted;
SYSCTL_DECL(_debug);
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_vif_arm, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlVifArm, 0, "");
static int be201AwdlVifPoolFlagsValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_vif_poolflags, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlVifPoolFlagsValue, 0, "");

static int be201AwdlVifAcceptSetsValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_vif_accept, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlVifAcceptSetsValue, 0, "");

static int be201AwdlVifLinkValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_vif_link, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlVifLinkValue, 0, "");

static int be201AwdlVifAwValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_vif_aw, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlVifAwValue, 0, "");

static int be201AwdlVifRadioValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_vif_radio, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlVifRadioValue, 0, "");
static int be201AwdlVifDataValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_vif_data, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlVifDataValue, 0, "");

bool AirportItlwm::awdlVifDataAllowed()
{
    return __atomic_load_n(&be201AwdlVifDataValue, __ATOMIC_ACQUIRE) == 1;
}

IOReturn AirportItlwm::sendAWDLData(const uint8_t *eth, size_t length)
{
    return fHalService ? fHalService->sendAwdlData(eth, length) : kIOReturnNotReady;
}

static int be201AwdlVifTxValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_vif_tx, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlVifTxValue, 0, "");

bool AirportItlwm::awdlVifTxAllowed()
{
    return __atomic_load_n(&be201AwdlVifTxValue, __ATOMIC_ACQUIRE) == 1;
}

// Data to a peer on that peer's own firmware queue, following where data goes. On with aggregation and both fixes
// from 1.1.54 when AWDL starts automatically (33 MB/s Mac to phone on 2026-11-07); 0 from RAM turns each off.
static int be201AwdlOwnQueueValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_own_queue, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlOwnQueueValue, 0, "");
// Test only: that queue on TID 0 with A-MPDU parameters and firmware rate control, QoS data, for Mac to phone speed.
static int be201AwdlTxAggValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_txagg, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlTxAggValue, 0, "");
// Test only: fixes tried for the held own queue, by bit (1 MAC 1 without power save, 2 link 1 QoS and beacon timing).
static int be201AwdlOwnFixValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_own_fix, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlOwnFixValue, 0, "");

// Test only, from RAM too: wait out the peer's other channels; link 1 on a channel of its own, with windows.
// be201_awdl_phy2: 0 off, 1 automatic (the 5 GHz channel of this Mac's own sequence when the AP is elsewhere), 36+ fixed.
static int be201AwdlTxHoldValue, be201AwdlPhy2Value, be201AwdlPhy2TeValue, be201AwdlAmsduValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_amsdu, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlAmsduValue, 0, "");
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_tx_hold, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlTxHoldValue, 0, "");
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_phy2, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlPhy2Value, 0, "");
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_phy2_te, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlPhy2TeValue, 0, "");

void AirportItlwm::awdlRadioTest(bool *hold, uint32_t *phy2, uint32_t *te, bool *amsdu)
{
    *amsdu = __atomic_load_n(&be201AwdlAmsduValue, __ATOMIC_ACQUIRE) == 1;
    *hold = __atomic_load_n(&be201AwdlTxHoldValue, __ATOMIC_ACQUIRE) == 1;
    const int channel = __atomic_load_n(&be201AwdlPhy2Value, __ATOMIC_ACQUIRE);
    *phy2 = channel > 0 ? static_cast<uint32_t>(channel) : 0;
    // 1: a window once a second, as in 1.1.42. 2: windows in the reference peer's slots on that channel.
    // 3: windows in this Mac's own slots on that channel (1.1.54). Channel 1 means automatic.
    // 4: as 3, and with channel 1 the link itself follows the sequence: the AP's channel for its slots (1.1.60).
    // 5: as 4, the own queue kept (flushed) across the moves instead of released (1.1.61).
    // The value is mode + 16 x kind of session protection (0 ASSOC as before, 1 GO_CLIENT_ASSOC, 2 P2P_DEVICE_DISCOV,
    // 3 P2P_GO_NEGOTIATION), passed above the mode (1.1.62).
    const int windows = __atomic_load_n(&be201AwdlPhy2TeValue, __ATOMIC_ACQUIRE);
    // Kind 1 asserted the firmware at once (0x2000150D, last command SESSION_PROTECTION, 2026-11-08 19:18) and kind 3
    // is the same family: only 0 and 2 are taken (1.1.63).
    const int mode = windows > 0 ? windows % 16 : 0, kind = windows > 0 ? windows / 16 : 0;
    // 6: as 5, and AWDL frames leave on a queue of link 1 while it is on the second channel (1.1.64).
    // 7: as 6 without windows; 8: link 1 stays on the second channel, its queue, no windows (1.1.65).
    *te = mode >= 1 && mode <= 8 && (kind == 0 || kind == 2) ? static_cast<uint32_t>(mode | (kind << 8)) : 0;
}

bool AirportItlwm::awdlOwnQueueWanted()
{
    return __atomic_load_n(&be201AwdlOwnQueueValue, __ATOMIC_ACQUIRE) == 1;
}

bool AirportItlwm::awdlTxAggWanted()
{
    return __atomic_load_n(&be201AwdlTxAggValue, __ATOMIC_ACQUIRE) == 1;
}

uint32_t AirportItlwm::awdlOwnFixWanted()
{
    const int fix = __atomic_load_n(&be201AwdlOwnFixValue, __ATOMIC_ACQUIRE);
    return fix > 0 ? static_cast<uint32_t>(fix) & 3 : 0;
}

// Test only: answer the family's peer cache requests. Off, a request is taken and never answered, as through 1.1.44.
static int be201AwdlCacheOnValue;
// Set by automatic start; awdlUmiDone may then turn the answers off again (1.1.72).
static bool be201CacheOnByDefault;
static uint32_t be201UmiFailStreak;
static constexpr uint32_t kBe201UmiFailsBeforeCacheOff = 4;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_cache_on, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlCacheOnValue, 0, "");
// Peer cache answers only for a peer that just registered real-time group traffic (ensemble, sidecar), 1.1.69.
static int be201AwdlCacheRtgValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_cache_rtg, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlCacheRtgValue, 0, "");

static int be201AwdlUmiValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_umi, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlUmiValue, 0, "");
static int be201AwdlLlwValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_llw, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlLlwValue, 0, "");
/*
 * 1.1.75 test, off by default: remain on channel for the AWDL sequence's other 5 GHz channel. Mode in the low
 * nibble (1 ROC only, 2 also management and multicast frames, 3 also unicast data), ROC activity in the next.
 */
static int be201AwdlRocValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_roc, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlRocValue, 0, "");
/* 1.2.24: pause mode, the whole radio on the AWDL channel while file data flows (be201_awdl_pause=0 turns it off). */
static int be201AwdlPauseValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_pause, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlPauseValue, 0, "");
bool AirportItlwm::awdlPauseWanted()
{
    return __atomic_load_n(&be201AwdlPauseValue, __ATOMIC_ACQUIRE) == 1;
}
uint32_t AirportItlwm::awdlRocWanted()
{
    const int value = __atomic_load_n(&be201AwdlRocValue, __ATOMIC_ACQUIRE);
    /* 1.1.96: mode and activity in the low byte, probe flags 0x100 (80 MHz) and 0x200 (no DTIM clamp) above;
     * 1.1.99: 0x400 asks for the DTIM clamp in mode 4. */
    /* 1.2.1/1.2.2: 0x800 times mode 4 by the phone's own schedule instead of the family's slots. */
    /* 1.2.4: 0x1000 turns the early ROC before a 149 slot off. */
    /* 1.2.6: 0x2000 covers 6 slots of each 149 run. */
    /* 1.2.9: 0x4000 covers the family's 149 slots only, not the phone's too. */
    /* 1.2.11: 0x8000 puts the AUX queue on TID 3 for A-MSDU. 1.2.12: 7 slots by default. 1.2.15: 2 slots to the AP by
     * default, 0x2000 leaves 1; 0x10000 marks the boot default (off while the AP is on 2.4 GHz). 1.2.16: 0x20000 covers
     * every slot of a peer data goes to (test). */
    return value > 0 && value < 0x400000 ? static_cast<uint32_t>(value) : 0;
}

bool AirportItlwm::awdlUmiOn()
{
    return __atomic_load_n(&be201AwdlUmiValue, __ATOMIC_ACQUIRE) == 1;
}

bool AirportItlwm::awdlLlwOn()
{
    return __atomic_load_n(&be201AwdlLlwValue, __ATOMIC_ACQUIRE) == 1;
}

bool AirportItlwm::awdlCacheOn()
{
    return __atomic_load_n(&be201AwdlCacheOnValue, __ATOMIC_ACQUIRE) == 1;
}

bool AirportItlwm::awdlCacheRtgOn()
{
    return __atomic_load_n(&be201AwdlCacheRtgValue, __ATOMIC_ACQUIRE) == 1;
}

static int be201AwdlVifRxValue;
SYSCTL_INT(_debug, OID_AUTO, be201_awdl_vif_rx, CTLFLAG_RW | CTLFLAG_LOCKED, &be201AwdlVifRxValue, 0, "");

bool AirportItlwm::awdlVifRxAllowed()
{
    return __atomic_load_n(&be201AwdlVifRxValue, __ATOMIC_ACQUIRE) == 1;
}

void AirportItlwm::inputAWDLActionFrame(const uint8_t *frame, size_t length,
    uint8_t channel, int rssi, uint32_t device_us)
{
    // HAL RX and interface teardown use this same workloop gate. No cached child pointer in HAL.
    if (!getWorkLoop() || !getWorkLoop()->inGate() || awdlStopping || awdlCreating ||
        !awdlInterface || !awdlVifRxAllowed())
        return;
    awdlInterface->inputActionFrame(frame, length, channel, rssi, device_us);
}

// A completion made room on the radio. Same gate as receive; the wake itself only signals the queue.
void AirportItlwm::awdlTxRoom()
{
    if (!getWorkLoop() || !getWorkLoop()->inGate() || awdlStopping || awdlCreating || !awdlInterface)
        return;
    awdlInterface->txRoom();
    if (llwInterface)
        llwInterface->txRoom();
}

void AirportItlwm::awdlUmiDone(const uint8_t *mac, bool acked)
{
    if (!getWorkLoop() || !getWorkLoop()->inGate() || awdlStopping || awdlCreating || !awdlInterface)
        return;
    /*
     * Safety for the default cache answers: if UMI keeps failing after them, the 1.1.45 failure (cache added, UMI
     * failing, AirDrop not starting) may be back, so stop answering for this boot. A success resets the count.
     */
    if (acked) {
        be201UmiFailStreak = 0;
    } else if (++be201UmiFailStreak >= kBe201UmiFailsBeforeCacheOff && be201CacheOnByDefault &&
               __atomic_load_n(&be201AwdlCacheOnValue, __ATOMIC_ACQUIRE) == 1) {
        __atomic_store_n(&be201AwdlCacheOnValue, 0, __ATOMIC_RELEASE);
        setProperty("ItlwmAwdlCacheAutoOff", true);
    }
    setProperty("ItlwmAwdlUmiFailStreak", be201UmiFailStreak, 32);
    awdlInterface->umiDone(mac, acked);
}

void AirportItlwm::awdlPeerCacheDone(const uint8_t *mac, bool added)
{
    if (!getWorkLoop() || !getWorkLoop()->inGate() || awdlStopping || awdlCreating || !awdlInterface)
        return;
    awdlInterface->peerCacheDone(mac, added);
}

bool AirportItlwm::awdlVifRadioAllowed()
{
    return __atomic_load_n(&be201AwdlVifRadioValue, __ATOMIC_ACQUIRE) == 1;
}

IOReturn AirportItlwm::setAWDLTemplate(bool mif, const uint8_t *data, size_t length)
{
    return fHalService ? fHalService->setAwdlNativeTemplate(mif, data, length) : kIOReturnNotReady;
}

IOReturn AirportItlwm::enableAWDLTransmit()
{
    return fHalService ? fHalService->enableAwdlNativeTx() : kIOReturnNotReady;
}

IOReturn AirportItlwm::requestAWDLMonitor(const ether_addr &address)
{
    return fHalService ? fHalService->requestAwdlMonitor(reinterpret_cast<const uint8_t *>(&address)) : kIOReturnNotReady;
}

bool AirportItlwm::awdlVifAwAllowed()
{
    return __atomic_load_n(&be201AwdlVifAwValue, __ATOMIC_ACQUIRE) != 0;
}

void AirportItlwm::reloadAWDLCapabilities()
{
    if (!fNetIf)
        return;
    loadCardCapabilities(fNetIf);
    if (const uint8_t *cache = nativeCapabilityCache())
        setProperty("ItlwmAwdlCapabilityCache", const_cast<uint8_t *>(cache), 0x18);
}

bool AirportItlwm::awdlVifLinkAllowed()
{
    return __atomic_load_n(&be201AwdlVifLinkValue, __ATOMIC_ACQUIRE) != 0;
}

bool AirportItlwm::awdlVifAcceptSets()
{
    return __atomic_load_n(&be201AwdlVifAcceptSetsValue, __ATOMIC_ACQUIRE) != 0;
}

uint32_t AirportItlwm::awdlVifPoolFlags()
{
    return __atomic_load_n(&be201AwdlVifPoolFlagsValue, __ATOMIC_ACQUIRE) & 1;
}

bool AirportItlwm::awdlVifCapabilityArmed()
{
    return __atomic_load_n(&be201AwdlVifArm, __ATOMIC_ACQUIRE) || be201AwdlVifAttempted;
}

void AirportItlwm::registerAWDLArmControl()
{
    if (awdlArmRegistered || !ItlAwdlFlag("be201_awdl_vif")) return;
    sysctl_register_oid(&sysctl__debug_be201_awdl_vif_arm);
    sysctl_register_oid(&sysctl__debug_be201_awdl_vif_poolflags);
    sysctl_register_oid(&sysctl__debug_be201_awdl_vif_accept);
    sysctl_register_oid(&sysctl__debug_be201_awdl_vif_link);
    sysctl_register_oid(&sysctl__debug_be201_awdl_vif_aw);
    sysctl_register_oid(&sysctl__debug_be201_awdl_vif_tx);
    sysctl_register_oid(&sysctl__debug_be201_awdl_vif_data);
    sysctl_register_oid(&sysctl__debug_be201_awdl_vif_radio);
    sysctl_register_oid(&sysctl__debug_be201_awdl_vif_rx);
    sysctl_register_oid(&sysctl__debug_be201_awdl_own_queue);
    sysctl_register_oid(&sysctl__debug_be201_awdl_txagg);
    sysctl_register_oid(&sysctl__debug_be201_awdl_own_fix);
    sysctl_register_oid(&sysctl__debug_be201_awdl_tx_hold);
    sysctl_register_oid(&sysctl__debug_be201_awdl_phy2);
    sysctl_register_oid(&sysctl__debug_be201_awdl_phy2_te);
    sysctl_register_oid(&sysctl__debug_be201_awdl_amsdu);
    sysctl_register_oid(&sysctl__debug_be201_awdl_cache_on);
    sysctl_register_oid(&sysctl__debug_be201_awdl_cache_rtg);
    sysctl_register_oid(&sysctl__debug_be201_awdl_umi);
    sysctl_register_oid(&sysctl__debug_be201_awdl_llw);
    sysctl_register_oid(&sysctl__debug_be201_awdl_roc);
    sysctl_register_oid(&sysctl__debug_be201_awdl_pause);
    /*
     * 1.2.15: cross-channel AirDrop on at boot, as the tool's --on (be201_awdl_xchan=0 keeps it off): link 1 on the
     * automatic second channel, and mode 4 once it is there (the driver waits for it). The RAM switches still change it.
     */
    if (ItlAwdlFlag("be201_awdl_xchan")) {
        __atomic_store_n(&be201AwdlPhy2Value, 1, __ATOMIC_RELEASE);
        /*
         * IWX_AWDL_ROC_DEFAULT plus 0x380000 (1.2.24): the presence A/B of 2026-11-14 14:59 (presence-*.txt) found
         * fewer peer absences (3.3 against 5.1 a minute) and half the aged-out services with 2 s sequence aging, no
         * receive timestamps and no slot flush, as on 1.2.17, in both pairs of rounds.
         */
        __atomic_store_n(&be201AwdlRocValue, 0x390024, __ATOMIC_RELEASE);
        setProperty("ItlwmAwdlXchanDefault", true);
        /* 1.2.24: ROC finds peers and asks; file data takes the whole radio (be201_awdl_pause=0: ROC only). */
        if (ItlAwdlFlag("be201_awdl_pause")) {
            __atomic_store_n(&be201AwdlPauseValue, 1, __ATOMIC_RELEASE);
            setProperty("ItlwmAwdlPauseDefault", true);
        }
    }
    awdlArmRegistered = true;
}

// What the test tool did by hand, now at load. The same single attempt per boot; the test switches stay off.
// After a panic the record is still in NVRAM at this point, read only here: a panic must not repeat every boot.
void AirportItlwm::startAWDLAuto()
{
    if (!awdlArmRegistered || !ItlAwdlFlag("be201_awdl_auto")) return;
    if (awdlLastBootPanicked()) {
        setProperty("ItlwmAwdlAutoSkippedAfterPanic", true);
        return;
    }
    __atomic_store_n(&be201AwdlVifAcceptSetsValue, 1, __ATOMIC_RELEASE);
    __atomic_store_n(&be201AwdlVifLinkValue, 1, __ATOMIC_RELEASE);
    __atomic_store_n(&be201AwdlVifAwValue, 1, __ATOMIC_RELEASE);
    __atomic_store_n(&be201AwdlVifRadioValue, 1, __ATOMIC_RELEASE);
    __atomic_store_n(&be201AwdlVifRxValue, 1, __ATOMIC_RELEASE);
    __atomic_store_n(&be201AwdlVifTxValue, 1, __ATOMIC_RELEASE);
    __atomic_store_n(&be201AwdlVifDataValue, 1, __ATOMIC_RELEASE);
    __atomic_store_n(&be201AwdlVifArm, 1, __ATOMIC_RELEASE);
    // Mac to phone speed, as tested on 2026-11-07: own queue, aggregation, both fixes. The 4.6 MB/s path stays the fallback.
    __atomic_store_n(&be201AwdlOwnQueueValue, 1, __ATOMIC_RELEASE);
    __atomic_store_n(&be201AwdlTxAggValue, 1, __ATOMIC_RELEASE);
    __atomic_store_n(&be201AwdlOwnFixValue, 3, __ATOMIC_RELEASE);
    // UMI (acked by iPhone and iPad since 1.1.47). Universal Control worked with it on 1.1.67.
    __atomic_store_n(&be201AwdlUmiValue, 1, __ATOMIC_RELEASE);
    /*
     * 1.1.69: real-time group peers get their peer cache answer. handleEnsembleTrafficReg waits 3 s for it
     * ("Waiting for caching of HP-RTG Peer"), and a second registration in that time waits 5 s for the first and
     * fails with 0xE00002CA: Universal Control's General I/O error while llw0 was on (1.1.67), Sidecar's "failed to
     * add SideCar to RTG". AirDrop peers still get no answer (1.1.45). llw0 is on again with it, for Continuity
     * Camera and Sidecar; debug.be201_awdl_llw=0 still brings Universal Control back at once if this is not enough.
     */
    __atomic_store_n(&be201AwdlCacheRtgValue, 1, __ATOMIC_RELEASE);
    /*
     * 1.1.74: llw0 off by default again. The next work (AirDrop on two channels, then ranging and the camera) is
     * measured without it; debug.be201_awdl_llw=1 still creates it for a test.
     */
    __atomic_store_n(&be201AwdlLlwValue, 0, __ATOMIC_RELEASE);
    /*
     * 1.1.72: peer cache answers for every peer. The family asks for the cache before it hands the traffic
     * registration to the driver, so 1.1.69's registration window never opened (RtgCacheAnswers 0), and it sends UMI
     * only to a cached peer ("Not sending UMI because peer ... is not cached"): Continuity Camera's ensemble start
     * failed at "waiting for UMIStatus" and the phone never streamed. On 1.1.45 these answers broke AirDrop while UMI
     * was not implemented; UMI is acked since 1.1.47. awdlUmiDone turns them off for the boot if UMI keeps failing.
     */
    __atomic_store_n(&be201AwdlCacheOnValue, 1, __ATOMIC_RELEASE);
    be201CacheOnByDefault = true;
    setProperty("ItlwmAwdlAuto", true);
    setProperty("ItlwmAwdlSpeedDefault", true);
    setProperty("ItlwmAwdlUmiDefault", true);
    setProperty("ItlwmAwdlRtgCacheDefault", true);
    setProperty("ItlwmAwdlCacheDefault", true);
    setProperty("ItlwmAwdlLowLatencyDefault", false);
}

bool AirportItlwm::awdlLastBootPanicked()
{
    IORegistryEntry *options = IORegistryEntry::fromPath("/options", gIODTPlane);
    if (!options) return false;
    OSObject *record = options->copyProperty("aapl,panic-info");
    const bool panicked = record != nullptr;
    OSSafeReleaseNULL(record);
    options->release();
    return panicked;
}

IOReturn AirportItlwm::createAWDLInterface(apple80211_virt_if_create_data *request)
{
    if (!request || !ItlAwdlFlag("be201_awdl_vif")) return kIOReturnUnsupported;
    if (!_fCommandGate) return kIOReturnNotReady;
    return _fCommandGate->runAction(createAWDLInterfaceGated, request);
}

IOReturn AirportItlwm::createAWDLInterfaceGated(OSObject *owner, void *arg0, void *, void *, void *)
{
    auto controller = OSDynamicCast(AirportItlwm, owner);
    auto request = static_cast<apple80211_virt_if_create_data *>(arg0);
    if (!controller || !request) return kIOReturnBadArgument;
    if (controller->awdlStopping || controller->awdlCreating) return kIOReturnNotReady;
    if (request->role != APPLE80211_VIF_AWDL || (request->version != 0 && request->version != APPLE80211_VERSION))
        return kIOReturnUnsupported;
    uint8_t nonzero = 0;
    for (unsigned i = 0; i < APPLE80211_ADDR_LEN; ++i) nonzero |= request->mac[i];
    if (!nonzero || (request->mac[0] & 1)) return kIOReturnBadArgument;
    if (controller->awdlFailed) {
        // A BSD attach that came after the wait gave up is taken on the next request. On 2026-11-08 at boot awdl0
        // attached 6 s after a 10 s wait had failed; the failure stayed for the boot and AirDrop could not send.
        auto *late = controller->awdlInterface;
        const char *name = late ? late->getBSDName() : nullptr;
        if (controller->awdlStopping || !late || !name || strncmp(name, "awdl", 4) || !late->getBSDInterface())
            return kIOReturnNotReady;
        ether_addr old = late->getSelfMacAddr();
        if (memcmp(&old, request->mac, sizeof(old))) return kIOReturnBusy;
        late->markDown();
        strlcpy(reinterpret_cast<char *>(request->bsd_name), name, sizeof(request->bsd_name));
        late->setProperty("ItlwmAwdlVifStage", 6, 32);
        controller->setProperty("ItlwmAwdlVifStep", "ready-late");
        controller->setProperty("ItlwmAwdlVifLateAdopted", ++controller->awdlLateAdopted, 32);
        controller->awdlFailed = false;
        return kIOReturnSuccess;
    }
    if (controller->awdlInterface) {
        ether_addr old = controller->awdlInterface->getSelfMacAddr();
        if (memcmp(&old, request->mac, sizeof(old))) return kIOReturnBusy;
        const char *name = controller->awdlInterface->getBSDName();
        if (!name || !controller->awdlInterface->getBSDInterface()) return kIOReturnNotReady;
        strlcpy(reinterpret_cast<char *>(request->bsd_name), name, sizeof(request->bsd_name));
        return kIOReturnSuccess;
    }
    // Each arm allows one attempt, so a failure cannot repeat on wifip2pd's next request.
    if (!__atomic_exchange_n(&be201AwdlVifArm, 0, __ATOMIC_ACQ_REL)) {
        controller->setProperty("ItlwmAwdlVifUnarmedRefusals", ++controller->awdlUnarmedRefusals, 32);
        return kIOReturnUnsupported;
    }
    be201AwdlVifAttempted = true;
    controller->setProperty("ItlwmAwdlVifAttempts", ++controller->awdlAttempts, 32);
    IOLog("BE201VIF create attempt=%u\n", controller->awdlAttempts);
    controller->awdlCreating = true;
    auto interface = new AirportItlwmAWDLInterface;
    IOReturn result = kIOReturnNoMemory;
    if (interface) {
        ether_addr mac = {}; memcpy(&mac, request->mac, sizeof(mac));
        result = kIOReturnError;
        if (interface->initForController(controller, mac) && interface->attach(controller) && interface->start(controller)) {
            // The BSD client attaches from the matching thread and may need this gate, so the
            // wait gives it up. Bounded, because a failure here must not hold wifip2pd forever.
            // 30 s: a busy boot took 16 s on 2026-11-08, past the old 10 s.
            result = kIOReturnNotReady;
            for (int i = 0; i < 300 && !controller->awdlStopping && !interface->getBSDInterface(); ++i) {
                AbsoluteTime deadline;
                clock_interval_to_deadline(100, kMillisecondScale, &deadline);
                _fCommandGate->commandSleep(&controller->awdlCreating, deadline, THREAD_UNINT);
            }
            const char *name = interface->getBSDName();
            if (!controller->awdlStopping && name && !strncmp(name, "awdl", 4) && interface->getBSDInterface()) {
                interface->markDown();
                strlcpy(reinterpret_cast<char *>(request->bsd_name), name, sizeof(request->bsd_name));
                interface->setProperty("ItlwmAwdlVifStage", 6, 32);
                controller->setProperty("ItlwmAwdlVifStep", "ready");
                IOLog("BE201VIF step=ready name=%s\n", name);
                result = kIOReturnSuccess;
            }
        }
        if (result != kIOReturnSuccess) {
            auto stage = OSDynamicCast(OSNumber, interface->getProperty("ItlwmAwdlVifStage"));
            controller->setProperty("ItlwmAwdlVifFailedStage", stage ? stage->unsigned32BitValue() : 0, 32);
        }
        if (result == kIOReturnSuccess || interface->holdsNativeState()) {
            // Retain the creation reference for controller lifetime. A failed object stays too:
            // freeing it left the controller's AWDL pointer dangling, which panicked 1.1.21.
            controller->awdlInterface = interface;
            controller->awdlFailed = result != kIOReturnSuccess;
        } else {
            interface->release();
        }
    }
    controller->setProperty("ItlwmAwdlVifCreateResult", static_cast<uint32_t>(result), 32);
    IOLog("BE201VIF create result=0x%x\n", result);
    controller->awdlCreating = false;
    _fCommandGate->commandWakeup(&controller->awdlCreating);
    return result;
}

struct LowLatencyRequest {
    AirportItlwmAWDLInterface *parent;
    const ether_addr *address;
    char *name;
    size_t nameLength;
};

IOReturn AirportItlwm::createLowLatencyInterface(AirportItlwmAWDLInterface *parent, const ether_addr &address, char *name, size_t nameLength)
{
    if (!_fCommandGate) return kIOReturnNotReady;
    LowLatencyRequest request = {parent, &address, name, nameLength};
    return _fCommandGate->runAction(createLowLatencyInterfaceGated, &request);
}

IOReturn AirportItlwm::createLowLatencyInterfaceGated(OSObject *owner, void *arg0, void *, void *, void *)
{
    auto controller = OSDynamicCast(AirportItlwm, owner);
    auto request = static_cast<LowLatencyRequest *>(arg0);
    if (!controller || !request || !request->parent || request->parent != controller->awdlInterface) return kIOReturnBadArgument;
    if (controller->awdlStopping || controller->llwCreating) return kIOReturnNotReady;
    if (controller->llwFailed) return kIOReturnNotReady;
    // 1.1.47 waited here for the BSD interface and never got it: the request comes on awdl0's path, which the
    // attach may need. Native answers at once, and wifip2pd waits for the name to appear, so this answers at once
    // and the interface finishes from its own timer.
    if (controller->llwInterface) {
        const char *existing = controller->llwInterface->getBSDInterface() ? controller->llwInterface->getBSDName() : nullptr;
        strlcpy(request->name, existing && existing[0] ? existing : "llw0", request->nameLength);
        return kIOReturnSuccess;
    }
    controller->setProperty("ItlwmAwdlLlwAttempts", 1, 32);
    controller->llwCreating = true;
    auto interface = new AirportItlwmLowLatencyInterface;
    IOReturn result = kIOReturnNoMemory;
    if (interface) {
        result = kIOReturnError;
        const bool ok = interface->initForParent(controller, request->parent, *request->address) &&
            (controller->setProperty("ItlwmAwdlLlwStage", 2, 32), interface->attach(controller)) &&
            (controller->setProperty("ItlwmAwdlLlwStage", 3, 32), interface->start(controller));
        if (ok) {
            // The name native would give; the interface publishes the real one when it attaches.
            strlcpy(request->name, "llw0", request->nameLength);
            interface->bringUp();
            result = kIOReturnSuccess;
        } else {
            auto stage = OSDynamicCast(OSNumber, controller->getProperty("ItlwmAwdlLlwStage"));
            controller->setProperty("ItlwmAwdlLlwFailedStage", stage ? stage->unsigned32BitValue() : 0, 32);
        }
        // The parent points at it after init, so a failed object stays too, like awdl0's.
        if (result == kIOReturnSuccess || interface->holdsNativeState()) {
            controller->llwInterface = interface;
            controller->llwFailed = result != kIOReturnSuccess;
        } else {
            interface->release();
        }
    }
    controller->setProperty("ItlwmAwdlLlwCreateResult", static_cast<uint32_t>(result), 32);
    controller->llwCreating = false;
    _fCommandGate->commandWakeup(&controller->llwCreating);
    return result;
}

IOReturn AirportItlwm::takeAWDLInterfaceGated(OSObject *owner, void *arg0, void *, void *, void *)
{
    auto controller = static_cast<AirportItlwm *>(owner);
    controller->awdlStopping = true;
    while (controller->awdlCreating || controller->llwCreating)
        _fCommandGate->commandSleep(controller->awdlCreating ? &controller->awdlCreating : &controller->llwCreating, THREAD_UNINT);
    *static_cast<AirportItlwmAWDLInterface **>(arg0) = controller->awdlInterface;
    controller->awdlInterface = nullptr;
    return kIOReturnSuccess;
}

void AirportItlwm::stopAWDLInterface()
{
    if (awdlArmRegistered) {
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_vif_arm);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_vif_poolflags);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_vif_accept);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_vif_link);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_vif_aw);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_vif_tx);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_vif_data);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_vif_radio);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_vif_rx);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_own_queue);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_txagg);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_own_fix);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_tx_hold);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_phy2);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_phy2_te);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_amsdu);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_cache_on);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_cache_rtg);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_umi);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_llw);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_roc);
        sysctl_unregister_oid(&sysctl__debug_be201_awdl_pause);
        awdlArmRegistered = false;
    }
    AirportItlwmAWDLInterface *interface = nullptr;
    if (_fCommandGate) _fCommandGate->runAction(takeAWDLInterfaceGated, &interface);
    else { awdlStopping = true; interface = awdlInterface; awdlInterface = nullptr; }
    if (!interface) return;
    // Before its parent, whose peer manager it borrows.
    if (auto *lowLatency = llwInterface) {
        llwInterface = nullptr;
        interface->setCompanion(nullptr);
        lowLatency->terminate(kIOServiceRequired | kIOServiceSynchronous);
        lowLatency->stop(this);
        lowLatency->release();
    }
    // This is a controller stop/release path, never the create ioctl or RX callback.
    // Required synchronous termination closes clients, invokes child stop and detaches it.
    interface->terminate(kIOServiceRequired | kIOServiceSynchronous);
    interface->stop(this); // Idempotent if IOKit already performed stop during termination.
    interface->release();
}
#endif
