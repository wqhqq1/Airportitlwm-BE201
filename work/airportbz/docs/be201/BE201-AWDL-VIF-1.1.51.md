# AirportItlwm 1.1.51: llw0 feature flags as native

## 1.1.50 results, 2026-11-06

Camera (22:41, hotspot 149): llw0 CREATED: stage 6, UP RUNNING, fe80 address, ifnet_attach in the kernel log. The unique id fix worked. "without local llw0" and "No network route" disappeared. Still no picture: Rapport starts UDPNWPath sessions with Flags LowLatency, listeners and RTP connections bind to llw0 with a satisfied path, then nw_path_flow_get_nexus_instance for llw0 "assigned returned false" and the channel flow attach fails; Sidecar still 32002. The kernel does not attach a flowswitch to llw0 ("not attaching flowswitch to llw0"): _ifnet_attach_flowswitch_nexus skips interfaces with xflags 0x404 (low latency or NX_NOAUTO), native too. Low latency flows are meant to get the netif nexus through the netif agent (nx_netif_agent_init, nx_netif_netagent_flow_add). Why that assignment fails is not established.

Feature flags: IO80211SkywalkInterface::getFeatureFlags gives 0x10000 for role 2 (low latency, ends up at registration +0x1a, read by IOSkywalkNetworkBSDClient::isLowLatencyWiFiInterface). IO80211VirtualInterface::getFeatureFlags adds 0x10000000, which the Skywalk code logs as kFeatureOnDemandInterfaceEnable. Native AppleBCMWLANLowLatencyInterface uses the Skywalk one, without that bit.

Second channel (22:59, router 36): teardown clean again. AirDrop photo stayed "waiting" with the second channel on; OwnSent 0, so nothing went through the own queue: traffic to the phone still used the AP queue on 36. The own queue follows the peer that set up block ack, which need not be the AirDrop destination.

User saw "to optimize performance Wi-Fi will be disconnected temporarily" (macOS prompt); at 23:05 en1 and awdl0 were fine. Not traced.

## Change

AirportItlwmLowLatencyInterface::getFeatureFlags returns IO80211SkywalkInterface::getFeatureFlags (property ItlwmAwdlLlwFeatureFlags). Camera tool records ifconfig -v llw0. Whether this changes the nexus assignment is a guess.
