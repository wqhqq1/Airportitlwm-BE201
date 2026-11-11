# AirportItlwm 1.1.76: the own aggregated queue survives a busy command ring

## 1.1.75 result, boot 2026-11-10 15:15

- **Wi-Fi off and on:** fixed, per the user. RunningRestores was 1.
- **AirDrop worked, but slowly:** four sends over AWDL ran at about 4 MB/s. The user reported "aggregation looks broken".
- **Counters:**
  - The own queue had worked earlier in the boot (OwnSent 271974, OwnAggOk 270526).
  - Now there was no own queue: OwnQueue -1, OwnActive 0, OwnAgg 0.
  - OwnErr 28 and OwnAggErr 28. No firmware fault, and no ItlwmLastCmdErr.

## Cause

- **Where 28 comes from:** errno 28 is ENOSPC. `iwx_send_cmd` returns it before sending when the host command ring is full, or when the slot at `cur` still belongs to a synchronous caller that has not woken yet. Both pass on their own.
- **First failure:** in `iwx_awdl_ownq_task`, `iwx_awdl_peer_agg` (STA_CONFIG) got ENOSPC. The task then built the queue on TID 15 without aggregation.
- **Second failure:** `iwx_tvqm_enable_txq` (SCD_QUEUE_CONFIG) got ENOSPC. That set OwnErr, and since 1.1.55 the once-a-second retry skips any OwnErr. The own queue was gone for the rest of the boot, and AirDrop data went out on the AP station's queue without aggregation.

## Change

- **`iwx_awdl_err_transient`:** returns true for ENOSPC, EBUSY and EAGAIN, either sign.
- **In `iwx_awdl_ownq_task`:**
  - A transient error from `iwx_awdl_peer_agg` ends this attempt. It does not fall back to TID 15.
  - A transient error from the queue allocation does not set OwnErr.
  - Both count OwnTransient and record OwnTransientLast. The existing retry builds the queue again a second later.
  - A queue the firmware refused (EIO, a timeout) still latches OwnErr, as before.
- **Unchanged:** the ROC test, the awdl0 running restore, and llw0 off by default.

## Tests

- test-awdl-ba:
  - the transient set;
  - a transient aggregation error returns before the TID 15 fallback;
  - a transient queue error returns before OwnErr.

All 24 suites pass.
