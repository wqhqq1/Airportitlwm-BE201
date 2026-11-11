# AirportItlwm 1.1.72: peer cache answers for every peer, with a UMI safety

## 1.1.71 result, boot 08:14, 2026-11-09

The camera still drops. llw0 received nothing (Ipkts 0). The VCMediaStream RTCP timeout came 12 s after the 08:16:18 session.

## Ensemble start on the Mac side (Continuity Camera, Mac as initiator)

At 08:16:18.637 `handleEnsembleTrafficReg` received a sidecar registration for the iPhone (its AWDL address, left out here). Then:

1. `sendIoctlToCachePeer`, then it waits 3 s for PeerCacheOperationCompleted, which times out: "Peer cache operation failed".
2. `sendRealTimeUMI`: "Not safe to send UMI". `handleUmiTimer` logs "Not sending UMI because peer … is not cached". UmiSent stayed 0.
3. It waits 3 s for EnsembleUMIStatusDone, which times out: "Ensemble start Failure, waiting for UMIStatus umi: b000000". The peer is uncached "due to inactivity".

With no RTG, the phone never streams. 1.1.69's window could not help:
- The family asks for the cache before it hands the traffic registration to the driver.
- RtgRegistrations stayed 0 even after the driver saw "sidecar". The +4 field may be a pointer (apple80211_ioctl.h declares `void *addr`), not the MAC.

The cache request itself carries no service type: +0x44 is a bandwidth class, 1 to 4.

## Change

- **Automatic start:** `startAWDLAuto` turns on `debug.be201_awdl_cache_on`, which answers peer cache requests for every peer through the existing path (a peer station, then event 51). Property: ItlwmAwdlCacheDefault.
- **Expected effect:**
  - UMI can be sent and acked, so the ensemble can start.
  - AirDrop's 3 s "Waiting for caching of AirDrop Peer" goes away.
- **Safety:** on 1.1.45 these answers broke AirDrop sending while UMI was not implemented, so a UMI failure was the visible symptom. `awdlUmiDone` counts consecutive UMI failures. At 4, it turns the answers off for the boot, if automatic start turned them on. Properties: ItlwmAwdlCacheAutoOff and ItlwmAwdlUmiFailStreak.
- **Unchanged:** the RTG window from 1.1.69 stays as it was.
- **Tests:** test-awdl-ba checks the default and the safety.

## Recovery

`sudo sysctl -w debug.be201_awdl_cache_on=0` stops the answers for the running boot.
