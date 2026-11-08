# AirportItlwm 1.1.57: teardown disables the own queue on its real TID

## 1.1.56 result, boot 2026-11-08 00:35

- **Speed:** the user says AirDrop speed is fine now. OwnSent 1597521, OwnOk 1597387, OwnAgg 1, OwnRetries 1, OwnRecovers 6, OwnRetargets 13, OwnQuietSkips 15, OwnFixDone 3.
- **Firmware error:**
  - After the transfer the user moved from the phone hotspot (149) to a router (36). The firmware asserted once: ItlwmFwErrorId 0x20101F49, ItlwmFwErrorCmd 0x004D0517.
  - The command header decodes as command 0x17, group 0x05 (DATA_PATH_GROUP): SCD_QUEUE_CONFIG_CMD, sequence 0x4D.
  - TxTripped is 1 and CtxStage 0, so AWDL is off for the boot. The family logged `enableAWDL ERROR: ioctl awdl_cap failed` at 00:38:07, on channel 36.

## Cause

- **The faulty call:** `iwx_awdl_ctx_remove` disabled the own queue with `iwx_mld_disable_txq(sc, c->own_sta, IWX_MGMT_TID)`.
- **Why it now fails:** with aggregation the queue is made on TID 0 (`c->own_tid`), so this disabled a (station, TID 15) queue that does not exist. Until 1.1.52 the own queue was always TID 15, which is why this never showed.
- **What was already right:** `iwx_awdl_own_release` (retarget, rebuild, second channel) already used `c->own_tid`.

## Change

- **Fix:** `iwx_awdl_ctx_remove` uses `c->own_tid`.
- **Test:** test-awdl-ba checks that teardown disables the own queue on `c->own_tid` before the station is removed, and that no own-station disable uses the management TID.
- **Unchanged:** everything else is as in 1.1.56.
