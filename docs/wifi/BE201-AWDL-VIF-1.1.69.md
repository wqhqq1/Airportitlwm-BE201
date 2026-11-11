# AirportItlwm 1.1.69: speed fixes resent per context; real-time group cache answers; llw0 on again

## 1.1.68 result, boot 06:40, 2026-11-09 (Mac on the iPhone hotspot, channel 149, 80 MHz)

- **Universal Control:** works (llw0 off).
- **AirDrop, Mac to iPhone, slow:** two uploads, 06:44:28 to 06:45:22 and 06:45:28 to 06:46:02. awdl0 sent 228 MB in all, about 2.6 MB/s. That is below the 4.6 MB/s of the path without aggregation. Before this, 33 MB/s was measured on the same hotspot (1.1.53, 1.1.56).
- **Counters:**
  - Own queue: OwnSent 155081 of DataTx 159344, OwnAggOk 109872, OwnAggFail 5029, OwnRecovers 8, OwnRetargets 20, OwnFixDone 3.
  - UMI: UmiSent 0.
  - Solo: SoloAdds 1, SoloRemoves 1. OwnSentPhy2 3 and OwnDonePhy2 3 show that the own queue was first built on the solo context.

## Cause

`own_fix_done` records that MAC 1 got its power table (no power save) and link 1 got QOS_PARAMS and BEACON_TIMING. These are the 1.1.53 fixes that took Mac to phone from 4.6 to 33 MB/s. The flag was set once per boot and never cleared. Both settings belong to the MAC and the link, and `iwx_awdl_ctx_remove` removes those. So every later context went without the fixes:
- **Since 1.1.66, every boot:** solo AWDL runs before the join, the own queue is built there and the fixes go to the solo MAC and link. After the join, the context is rebuilt on the AP's PHY without them.
- **Before 1.1.66:** any network change, rejoin or firmware restart.

UMI did not take part: the driver sent none. The idle and Low Power schedule states also appeared in the fast 1.1.56 run.

## Change

- `iwx_awdl_ctx_remove` clears `own_fix_done` and `own_fix_err`.
- The firmware restart path clears `own_fix_done`.
- The next own-queue build sends both fixes to the new MAC and link.
- test-awdl-ba checks that the clears happen and that the build sends what is not done.

## llw0 and RTG, read from IO80211Family (24G824)

`IO80211AWDLPeerManager::handleEnsembleTrafficReg` serialises registrations:
- While one registration is running (ivars +0x422a), the next one waits 5 s for peer-manager event 10, then fails with "ERROR: registration ENABLE" and 0xE00002CA. That is the General I/O error UC hit with llw0 present, and Sidecar's "failed to add SideCar to RTG" on 1.1.46.
- A running registration waits on two events:
  - "Waiting for caching of HP-RTG Peer": `addPeerToFWCache`, then event 8 for 3 s. That is the peer cache answer (event 51), which this driver leaves off by default since 1.1.45.
  - The UMI status: event 9 for 3 s, signalled from `processUnicastAfStatus`. That is UMI event 69, which works.

So every ensemble start spends about 3 s waiting for a peer cache answer that never comes, and a second registration in that window fails.

## Change 2 (on by default): peer cache answers for real-time group peers, llw0 on again

- **Opening the window:** setAWDL_PEER_TRAFFIC_REGISTRATION already read the service name. For "ensemble" (Universal Control, Continuity Camera) and "sidecar", it now reads the peer address at +4 and `active` at +0xa8.
  - An enable opens a 10 s window for that peer.
  - A disable closes the window.
  - The table holds four peers.
- **Answering (setPEER_CACHE_CONTROL):**
  - An add for a peer inside its window gets the existing answer path: a peer station, then event 51.
  - A delete gets an answer only when the add was answered.
  - Every other peer, AirDrop included, still gets no answer. The all-peers answers that broke AirDrop on 1.1.45 stay a test switch (`debug.be201_awdl_cache_on`).
- **Switch:** RAM `debug.be201_awdl_cache_rtg`, set to 1 by automatic start.
- **Properties:** ItlwmAwdlRtgRegistrations, ItlwmAwdlRtgCacheAnswers and ItlwmAwdlRtgCacheLate on awdl0, and ItlwmAwdlRtgCacheDefault on the controller.
- **llw0:** `debug.be201_awdl_llw` is on again with automatic start (ItlwmAwdlLowLatencyDefault). If Universal Control still fails, `sudo sysctl -w debug.be201_awdl_llw=0` brings it back at once, as the user found on 1.1.67.
- **Not addressed:** Continuity Camera's `assigned returned false` for llw0 flows. Whether the faster RTG setup changes it is unknown.
- **Tests:**
  - test-awdl-ba checks the window, the delete rule, that AirDrop is excluded, and the defaults.
  - test-awdl-vif covers the new switch: 20 registered.
