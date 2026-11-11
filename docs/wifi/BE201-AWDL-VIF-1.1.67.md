# AirportItlwm 1.1.67: UMI and llw0 on by default (Continuity Camera, Sidecar)

## Where llw0 stood

- **1.1.47:** UMI works. iPhone and iPad ack the Mac's unicast master indication and the RTG goes Active. No llw0 yet.
- **1.1.50:** llw0 is created and running (unique id fix). Rapport's low latency sessions bind to llw0, but the flow never gets the netif nexus ("assigned returned false"), so there is still no picture.
- **1.1.51:** llw0's feature flags became native (no on-demand bit, 0x10000000). This was built but never run on hardware: the UMI and llw0 switches stayed RAM test switches, off by default, and the camera work was paused.

## Kernel side, read from xnu (bsd/skywalk/nexus/netif)

- `nx_netif_flags_init` marks a native netif low latency when the interface name starts with `llw`. That sets `IFXF_LOW_LATENCY`.
- `nx_netif_flow_init` then enables flows (the interface family must be Ethernet).
- `nx_netif_agent_init` registers and adds the NetIf netagent, with NEXUS_PROVIDER for low latency.
- Rapport's flows are IPv6 ULA flows (per-session `fd..` addresses). `nx_netif_netagent_handle_ipv6_ula_flow_add` binds a netif port keyed on local and remote ULA.

Nothing on this path depends on the driver beyond the name, a native netif and the Ethernet family, and 1.1.50 meets all three. So why the assignment failed is not established. The unified log keeps only default-level lines from the 1.1.50 test, and the skywalk and libnetwork detail was at debug level.

## Which sessions use low latency

In three days of logs, Rapport started low latency sessions (`Flags 0x6 < LowLatency Handoff >`) only from ContinuityCaptureAgent (49) and SidecarRelay (6). AirDrop and Universal Control never did. wifip2pd asks for llw0 once per boot, and today each request ends with "unsupported function".

## Change (on by default)

- **Automatic start:** `startAWDLAuto` also turns on UMI (`debug.be201_awdl_umi`) and llw0 (`debug.be201_awdl_llw`). Property: ItlwmAwdlLowLatencyDefault.
- **When it does not apply:** not after a panic, the same as the other defaults.
- **Effect:** llw0 is created on wifip2pd's request at boot. Camera and Sidecar run the whole path in normal use, including the 1.1.51 feature flags, with no test tool.
- **Turning it off:** each switch still works, for this boot only, with `sudo sysctl -w debug.be201_awdl_llw=0` (or `debug.be201_awdl_umi=0`).

## What to read after a camera or Sidecar attempt

- `ifconfig -v llw0`: low latency flag, agents (Skywalk NetIf), netif nexus.
- llw0's ItlwmAwdlDataTx, DataRx and DataTxDropped.
- The controller's ItlwmAwdlLlwStage (6 means data up) and ItlwmAwdlLlwFeatureFlags.
- Rapport, avconferenced and ContinuityCaptureAgent lines around the attempt. A live `log stream --level debug` for com.apple.network gives the assignment detail.

## Tests

test-awdl-ba checks that both switches are off without automatic start, on with it, set after the panic check, and published.
