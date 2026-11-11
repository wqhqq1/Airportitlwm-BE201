# AirportItlwm 1.1.79: no off-channel scans while AWDL carries bulk data

## 1.1.78 result, boot 2026-11-10 15:58

- **The stats report runs:** DataStatsReports 65, DataStatsResult 0. The family's "Prev Tx" in `monitorAWDLDataMode` still showed 0, so these counts do not reach the AWDL peer manager this way. The schedule alternated between "Data + Infra Data" and "Scan + Data".
- **The upload still stalled.** It started at 15:59:50, and the user cancelled it at 16:01:02. OwnRecovers was 6.
- **What happened at the stall:** from 16:00:03.9 to 16:00:11 the family's ScanManagerFamily issued 22 background scans back to back, of 2 to 3 channels each, lasting 0.06 to 0.91 s, with the next one 3 to 16 ms after each finished.
  - Each scan takes the firmware off 149, so AWDL data stops for the whole run.
  - The held-queue recoveries point the same way: the TX watchdog reaches 1 only after about 14 s with no TX completion at all (any completion clears it).

## Why the family scans

`IO80211ScanManager::isScanDisallowedByAwdl` (disassembled) blocks infrastructure scans in the AWDL states it tracks: real-time, HT mode and others ("InfraScanAllowed 1 ... HTMode 0" in the log). This driver's data path never puts the family into those states. The 1.1.78 report, for one, does not reach the AWDL peer manager counters.

## Change

- **`ItlHalService::awdlBulkActive`** (ItlIwx: `iwx_awdl_bulk_active`):
  - at least 256 KB of unicast data to peer stations in the last closed 500 ms byte window plus the open one;
  - that window closed no more than 1.5 s ago.
- **`AirportItlwmSkywalkInterface::startWCLScan`, associated (RUN) case:**
  - With bulk AWDL data, and a real scan within the last 30 s, the background scan does not start. `wclScanDeferred` is set, and the scan timer fires 300 ms later.
  - `completeWCLScan` then ends that scan with success: no new results, and the cache stays as it was.
  - Otherwise the scan runs as before and records `wclLastRealScanUs`. The first scan during bulk data is always real.
  - Property: ItlwmWclScanDeferred.
- **`finishWCLScan`** clears the deferred flag. That covers aborts and offline as well.
- **Unchanged:**
  - Scans while not associated.
  - The 1.1.78 stats report: harmless. Its result is published.
  - All earlier fixes.

## Tests

- test-awdl-ba:
  - the bulk check: empty, threshold, open window counted, stale, clock before the window;
  - the scan gate order and the 30 s allowance;
  - completion of a deferred scan and the flag cleared in `finishWCLScan`;
  - init.

All 24 suites pass.
