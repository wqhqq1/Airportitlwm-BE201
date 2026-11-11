# AirportItlwm 1.1.80: the scan gate holds after bulk data; a per-second stall history

## 1.1.79 result, boot 2026-11-10 16:12

- **Still stalls.** Two uploads (16:14:53 and 16:15:26) were cancelled by the user after 25 and 40 s. OwnRecovers was 4.
- **Scans:** ItlwmWclScanDeferred 7, ItlwmWclScanRunStarted 54, out of 88 scan requests.
- **No log for the stall:** the unified log has no kernel lines between 16:13 and 16:16. Only a few minutes around it survive, flooded by "_monitorPacket is null can't send to BPF" and IOC DEBUG lines, so the stall moment itself is not in the log.

## Change

- **Scan hold:**
  - The AW tick records `bulk_last_us` when a closed window shows bulk data.
  - `awdlBulkActive` now returns `iwx_awdl_bulk_recent`: bulk now, or within 10 s of `bulk_last_us`.
  - A stall no longer reopens back-to-back scans that keep it going. One real scan per 30 s stays allowed.
- **History:** `setAwdlSlot` adds one sample a second to a 90-entry ring and publishes it as ItlwmAwdlHistory, oldest first, 44 bytes each. Each sample holds:
  - the time;
  - OwnSent, OwnOk, OwnAggFail, OwnBaNotifs, TxBusy, DataStalls, OwnRecovers and McastSent;
  - the own queue and AP queue depths;
  - flags: own active, held, BGSCAN, TX timer armed, solo, data stalled, bulk, scan held.
- **Tool:** `卡顿记录.command` (`stall_history.py`) prints the per-second deltas and saves stall-*.txt in the kit. It is read only.

## Tests

- test-awdl-ba:
  - the hold window;
  - the ring order and its 44-byte record;
  - the source order in `setAwdlSlot`;
  - the gate using `bulk_recent`.

All 24 suites pass.
