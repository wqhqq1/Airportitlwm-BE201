# AirportItlwm 1.1.73: AWDL survives a Wi-Fi loss

## 1.1.72 results

Two boots: 2026-11-09 08:35 and 2026-11-10 09:31.

- **Camera real-time group starts.** On the 2026-11-10 09:43:57 session, the family cached the phone and sent the ensemble start UMI. The phone acked it ("Peer acked Ensemble start UMI request", "Done with traffic registration") and the schedule went to RealTimeGroup on 149. This is the first time on this machine.
- **Then Wi-Fi drops.** The Mac's infrastructure network is the same iPhone's Personal Hotspot (172.20.10.x, 5 GHz channel 149):
  - 09:44:05.5: link down (IEEE reason 1, involuntary). The 149 BSS stopped appearing in scans.
  - 09:44:23: the hotspot reappeared with a new BSSID on 2.4 GHz channel 6, and the Mac rejoined it at 09:44:54.
  - So the phone restarted its hotspot on 2.4 GHz once the camera group was up. The 2026-11-09 08:53:34 drop shows the same pattern (BSSID changed, link down).
  - The camera registration was cleared at 09:44:13.
- **AWDL then stayed off for the boot.** AirDrop failed afterwards ("Ask failed", peers:0), as on 2026-11-09 09:01.

## Cause of AWDL staying off

Properties after the drop: ItlwmFwErrors 1, error 0x20101E08, data1 3, last command 0x680308 (MAC_CONFIG). AWDL properties: TxTripped 1, SoloFailed 1, SoloErr 5 at stage 4, NativeMonitorReady No.

The frozen LINK trace (ItlwmTlcFirstFaultTrace), in order:

| Ordinal | State | Command |
|---|---|---|
| 55 | RUN | LINK REMOVE link 1 (AWDL removed before the AP) |
| 56, 57 | RUN | AP link 0 deactivated, then removed |
| 58 to 60 | INIT | solo context: LINK ADD link 1, then PHY 1, then active |
| 0x63 to 0x65 | | STA_CONFIG, SCD_QUEUE_CONFIG, STA_REMOVE |
| 61, 62 | | link 1 deactivated, then removed |
| 0x68 | | MAC_CONFIG REMOVE for MAC 1: assert |

After 5 s idle, the solo context started.

1. **The queue was refused.** The firmware handed the AWDL station a queue number. Under VT-d, `iwx_tvqm_enable_txq` refused any number whose host ring still counted frames. That number belonged to the AP data queue, whose host ring still counted frames from before the link loss. The refusal returned EIO without removing the queue in the firmware.
2. **The solo failure removed the context.** The queue was still attached to the AWDL station, so removing the MAC asserted the firmware.
3. **`iwx_nic_error` tripped AWDL for the boot.** Nothing re-armed it after the firmware restart, so every later association skipped `iwx_awdl_ctx_add`.

1.1.56 hit a similar class (0x20101F49 leaving a hotspot), with the same latch.

## Change

- **`iwx_tvqm_enable_txq`** (VT-d path):
  - The queue the firmware just allocated is free in the firmware. Host frames still counted on it are stale, and the existing reset/free below handles them, unless a live owner holds that number. The new `iwx_txq_owned` checks for that owner: the management queue, any AP TID, or the AWDL qid, own_qid or phy2_qid.
  - Every refusal after the firmware allocated the queue now sends `SCD_QUEUE_CONFIG` REMOVE for that station and TID (MLD firmware), so nothing is left on the station.
- **Fault re-arm:**
  - `iwx_nic_error` marks a fault trip as re-armable while `fault_rearms < IWX_AWDL_FAULT_REARM_MAX` (2).
  - `iwx_stop` clears the trip and `solo_failed` after it clears the context state, which is the firmware restart.
  - The third fault in a boot latches as before.
  - Properties: ItlwmAwdlFirmwareFaults, ItlwmAwdlFaultRearms.
- **OpenCore:** TakeoffDelay 10000 → 100000 µs.
  - Holding Option did not open the picker with ShowPicker false. This machine's keyboard is PS/2. The OpenCore docs give Escape and 0 as picker keys for firmware that does not report a held Option key, which some PS/2 keyboards do not.
  - The longer delay gives the keyboard driver more time before the single hotkey read.
  - Nothing else in the config changes.

## Not changed

The phone moving its hotspot when the camera group starts is the phone's behavior. With the Mac on that phone's hotspot, the infrastructure link will still drop. AWDL should now continue (solo while disconnected, then on the new network) instead of staying off.

## Tests

test-awdl-ba checks:
- the refused queue is released;
- stale frames alone do not refuse a queue;
- the owner list;
- the bounded re-arm;
- the re-arm order in `iwx_stop`.

All 24 suites pass.
