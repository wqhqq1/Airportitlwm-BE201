# AirportItlwm 1.1.78: the family sees AWDL traffic and keeps the data schedule

## 1.1.77 result, boot 2026-11-10 15:47

- **Speed:** good. Aggregation worked: OwnAggOk 1542617, OwnBaNotifs 74506, about 2.3 GB on awdl0, no firmware error. PeerReplaced was 0, because the table was not full of stale peers this time.
- **Large files stalled after a while.** The user cancelled the second upload at 15:50:17 (started 15:48:41). OwnRecovers was 4: the own queue was held by the TX watchdog and rebuilt four times.
- **What the family saw during the uploads:**
  - "monitorAWDLDataMode: In AW: Tx:0 Rx:0", then the schedule went Idle and then Low Power.
  - The Low Power sequence was `[149 0 149 0 0 0 0 0 6 0 149 0 0 0 0 0]`, which leaves 3 of 16 slots on 149. A peer follows this Mac's advertised slots.

## Cause

`IO80211AWDLPeerManager::monitorAWDLDataMode` (disassembled from the KC) decides data mode from the peer manager's packet counters at [pm+0x7a0] (transmitted) and [pm+0x78c] (received).
- The family's own path updates them in `preQueuePacket`, `skywalkLogTxPacket`, `inputPacket` and `skywalkInputPacket`. This driver's data path uses plain Skywalk queues, so it never passes through those functions.
- Drivers report their own counts with `IO80211SkywalkInterface::updateInterfaceDataStats(apple80211_data_path_interface_stats *)`. It is exported by the family and imported by AppleBCMWLAN. It calls `IO80211InterfaceMonitor::recordInterfaceTxRxCounts`, then `IO80211PeerManager::updateLocalCounters`, which adds struct +0x08 to [0x7a0] and +0x18 to [0x78c].

## Change

- **`AirportItlwmAWDLInterface::reportDataStats`:** at slot 0 of every AW cycle (about every 260 ms), if any packets went out or came in since the last report:
  - it fills a zeroed 0x700-byte struct with the transmitted delta at +0x08 and the received delta at +0x18 (the struct is read up to 0x640);
  - it calls the base `updateInterfaceDataStats`, named by its mangled symbol because it is a private virtual (slot 0xe28) in the headers.
- **Properties:** ItlwmAwdlDataStatsReports and ItlwmAwdlDataStatsResult. A result of 0xE0000001 means the interface has no InterfaceMonitor, and nothing was counted.
- **Imports:** unchanged at 1115. The vtable already referenced `__ZN23IO80211SkywalkInterface24updateInterfaceDataStatsEP36apple80211_data_path_interface_stats` (defined in the family, T).

## Tests

- test-awdl-vif:
  - the deltas reach the call;
  - no new packets means no call;
  - a later packet is reported alone.
- test-awdl-ba: call site and struct offsets.

All 24 suites pass.
