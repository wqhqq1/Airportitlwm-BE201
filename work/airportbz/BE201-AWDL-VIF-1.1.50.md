# AirportItlwm 1.1.50: llw0 gets its own interface unique id; gentler windows

## 1.1.49 results, 2026-11-06

Second channel (22:16, router 36, target 149): the teardown fix works, no firmware error, AP fine afterwards. RxPhy2 182 in 30 s alone (about 6 a second, up from 1 on 1.1.47), 355 in 30 s with schedule windows, but gateway RTT 139 ms with windows every other slot (19 ms without). No awdl0 neighbor again, so own queue TX is still untested.

Camera (22:23, hotspot 149): UMI fine. llw0 again missing. Controller: LlwStage 4 (registered), LlwPolls 600, create result 0. The llw0 object has "BSD Name" llw0 and IOInterfaceName llw0 but no IOSkywalkNetworkBSDClient child, no ifnet_attach in the kernel log, and was busy 5024 ms. IOSkywalkNetworkBSDClient::start names the interface, then loops on kern_nexus_controller_alloc_net_provider_instance while it returns EBUSY (IOSleep), then gives up. Native AppleBCMWLANLowLatencyInterface::initBSDInterfaceParameters calls the base, then sets uniqueid (+0x10) to 8 bytes holding the object pointer, uniqueid_len (+0x18) 8. The Ethernet base sets a unique id from the MAC address, which awdl0 already holds; xnu answers EBUSY for an in-use unique id. That matches, not proven.

## Change

- AirportItlwmLowLatencyInterface overrides initBSDInterfaceParameters like native. Property ItlwmAwdlLlwUniqueId on the controller when it ran.
- Schedule windows (debug.be201_awdl_phy2_te 2) at most every 250 ms instead of 120 ms.
- 开始信道实验.command asks for a real AirDrop photo send during the own queue phase, since no neighbor appears without traffic.
