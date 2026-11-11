# AirportItlwm 1.1.81: awdl0 traffic reported before every AW event

## 1.1.80 result, boot 2026-11-10 17:11

- **One AirDrop to the iPhone:**
  - Started 17:12:57.8. Upload progress came every 0.2–0.4 s until 17:13:16.4, with one 2.7 s gap after 17:13:04.
  - Nothing after that. The user cancelled at 17:13:32.8, after a 16 s stall.
- **Router:** the Mac was on a router.
- **Driver counters:**
  - OwnSent 159038, OwnOk 158994, OwnRecovers 3.
  - No firmware fault, no OwnErr.
- **The per-second history did not cover the stall:** it was read four minutes later, and it keeps only 90 s.

## What the family did during the stall

The kernel log for this boot is complete.

| Time | Family log | Schedule |
|---|---|---|
| 17:13:10 | AWDLStateDump: "AWDL enabled with no data connection from 9 seconds", mid-transfer | |
| 17:13:11.236 | `monitorAWDLDataMode`: "In AW: Tx:0 Rx:0 Prev Tx:0 Rx:0" → `setScheduleState` Idle | `[149 149 149 0 0 0 0 0 6 149 149 0 0 0 0 0]` |
| 17:13:11.758 | RptDataPathThres | Data, all 16 slots |
| 17:13:16.477 | Idle again | |
| 17:13:17.000 | Data | |
| 17:13:18.573 | Idle; it stays there | |
| 17:13:24 | "Moving to low power mode" (IdleTimeout) | `[149 0 149 0 0 0 0 0 6 0 149 0 0 0 0 0]` |

The transfer stopped while the schedule flapped, and did not recover in Idle and Low Power.

## Cause

This kernel, read from the KC:

- **When the check runs:**
  - `IO80211AWDLPeerManager::reportDataPathEvents` handles our AW start event (`kAwStartMessage`).
  - When the event's AW number is a multiple of `[0x3ea8]` (8), it calls `monitorAWDLDataMode`. Right after, it snapshots the peer manager's tx counter (`+0x7a0`) and rx counter (`+0x78c`) into `0x3fe8` and `0x3fe4`.
- **What the check measures:** the change in those two counters since the previous snapshot ("Prev Tx/Rx").
- **What keeps Data:**
  - tx + rx of at least `[0x3ea4]` = 8 packets (`initParamsToDefaults`), or
  - AirPlay, Sidecar or RTG state.

  Otherwise the schedule drops to Idle, then to Low Power after the idle timeout.
- **What 1.1.78 did:**
  - `reportDataStats` (`IO80211SkywalkInterface::updateInterfaceDataStats`, then `IO80211PeerManager::updateLocalCounters`) adds our counts to `+0x7a0` and `+0x78c`.
  - The peer manager is `[ivars+0x28]`, the same one that receives the AW events (`reportDataPathEventsGated`), so the report lands.
- **Why the report missed most checks:**
  - It ran only at slot 0.
  - The AW timer runs about 2.6 times a second (AwAligned 1536 after 10 minutes), and the slot comes from the heard AW number, so slot 0 came up about once every 6 s.
  - With four AWs a slot, the check runs at every even slot. A check without a report since the last snapshot saw 0 and moved to Idle; the next report moved it back.

## Change

- `reportDataStats()` runs on every AW tick, just before `postMessage(kAwStartMessage, …)`. Each check now counts the packets sent and received since the previous one.
- `restoreRunning()` still runs at slot 0.
- **Unchanged:**
  - the 10 s scan hold and the per-second history from 1.1.80;
  - the ROC test switch (off), and llw0 off;
  - the speed-up, UMI and cache answers.

## Tests

- test-awdl-ba: the restore at slot 0, the report directly before the AW event.

All 24 suites pass.
