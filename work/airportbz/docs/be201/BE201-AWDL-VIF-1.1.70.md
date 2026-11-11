# AirportItlwm 1.1.70: llw0 goes up through IOSkywalk, so low latency channels can open

## 1.1.69 result, boot 07:08, 2026-11-09

- Universal Control works with llw0 on: the RTG peer cache answers fixed the registration overlap.
- Continuity Camera and Sidecar connect, then drop with no picture.

## Capture at 07:41:48 (outputs/BE201llw0采集)

The capture recorded `skywalkctl channel`, `skywalkctl tree` and `skywalkctl flow-owner` every second for 40 s, plus the network debug log.

- The camera connections C7, C8 and C9 get their nexus (`flow:receive_nexus`). Then `os_channel_create` fails with 16 (Resource busy) on key `6CA91B9B-…-2`, which is llw0's netif nexus, port 2.
- At no second was any channel on llw0's nexus. So neither a duplicate port nor a held device port is the cause.

## Cause, read from xnu and IOSkywalkFamily (24G824)

1. The first virtual port of a low latency netif opens a kernel channel on the device port (`netif_vp_na_activate_on` → `netif_hwna_setup` → `ch_open_special`). `ch_connect` then calls the provider's pre-connect, `IOSkywalkNetworkBSDClient::preConnect`.
2. `preConnectAction`:
   - It returns success when the interface is marked enabled (+0x141).
   - Otherwise it sends itself SIOCSIFFLAGS and, if the mark is still clear, returns kIOReturnNotReady.
   - `IOService::errnoFromReturn(kIOReturnNotReady)` is EBUSY, which matches what the flow saw.
3. The mark is set only in `ioctlHandler`'s SIOCSIFFLAGS path, and only when IFF_UP is set and IFF_RUNNING is not. That path calls the interface's `setRunningState(true)` (vtable 0x930) and, on success, sets IFF_RUNNING and the mark.
4. Through 1.1.69, llw0's link timer set IFF_RUNNING directly with `ifnet_set_flags`. An earlier SIOCSIFFLAGS from configd had come while `setRunningState` still refused (data not active). So every later SIOCSIFFLAGS was skipped as already running, the mark never came, and every first low latency channel got EBUSY.

## Change

- **Bringing llw0 up:** after the data path is active, llw0 sets IFF_UP and sends itself SIOCSIFFLAGS through `ifnet_ioctl`. IOSkywalk then calls `setRunningState(true)`, which succeeds now, and sets IFF_RUNNING and the enabled mark itself.
- **Properties:** ItlwmAwdlLlwUpResult (the ioctl result) and ItlwmAwdlLlwUpRunning.
- **Fallback:** if RUNNING still did not come, the old direct path runs, and ItlwmAwdlLlwUpFallback is set.
- **New import:** `_ifnet_ioctl` (kernel KPI).
- **Tests:**
  - test-awdl-vif: the mock interface flags and SIOCSIFFLAGS stub expect the ioctl path and no fallback.
  - test-awdl-ba: checks the order.

## Not changed

AirDrop registrations still wait 3 s for a peer cache answer before each send ("Waiting for caching of AirDrop Peer"). Answering every AirDrop peer is what broke sending on 1.1.45, so it stays off.
