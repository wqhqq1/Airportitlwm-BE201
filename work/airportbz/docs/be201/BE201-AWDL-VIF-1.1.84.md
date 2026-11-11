# AirportItlwm 1.1.84: AUX_STA_CMD and ROC_CMD replies complete

## 1.1.83 result, boot 2026-11-11 08:26

- **Router:** channel 157, encrypted. ItlwmApPortValid 1, ItlwmApRsnOn 1.
- **DMA pool:** 44884 KiB used, no failures. Router data queues 255.
- **ROC test at 08:33:**
  - The setup ran for the first time (RocSetups 1, then 2 on the activity-2 retry).
  - Both attempts stopped at stage 1 (AUX_STA_CMD) with error 35.
  - ItlwmLastCmdId 0x30b (MAC_CONF AUX_STA_CMD), ItlwmLastCmdErr 35. FwErrors 0.
- **AirDrop:** 0 MB/s in every phase. The phone saw the Mac but the transfer did not move. No AWDL peers in the family.

## Cause

- **What 35 means:** EWOULDBLOCK. `iwx_send_cmd` returns it when a synchronous command waits out IWX_HOST_COMPLETE_TIMEOUT_MS without completing.
- **The command itself is correct:** iwlmld and iwlmvm (`iwl_mvm_add_aux_sta_to_fw`) send AUX_STA_CMD with only `sta_id` and `lmac_id`, the same 16-byte layout as here.
- **Where it went wrong:**
  - `iwx_notif_intr` calls `iwx_cmd_done` only for responses whose code is listed in the command-response cases. Everything else goes to `default: handled = 0`.
  - AUX_STA_CMD (0x30b), ROC_CMD (0x30e) and STA_DISABLE_TX_CMD (0x30d) were not listed. Their replies were logged as unhandled, and the waiter timed out.
- **Side effects:**
  - The asynchronous ROC_CMD would have kept its slot in the command ring.
  - The ROC remove path sends ROC_CMD synchronously, and would have timed out as well.
- **Every other wide command the driver sends has a completing case.** A new test checks this for all of them.
- **Left over in that boot:** after the timeout the AUX station 12 likely exists in the firmware without `sta_added`. It is gone after a reboot.

## Change

- AUX_STA_CMD, ROC_CMD and STA_DISABLE_TX_CMD added to the command-response cases.
- **Installer, because another session (audio) also edits `config.pending`/`config.plist`:**
  - Right before writing, `install.py` compares `config.plist` with the bytes it read and stops without writing if they differ.
  - A rollback restores the old file only if the file on disk is still the one this install wrote.
  - As before, the new config is built from the live file at install time. Only the Wi-Fi comment, the `be201_awdl_*` boot arguments and TakeoffDelay change, and an assertion checks that nothing else does.
- **Unchanged:** the open-network port check (1.1.83), the DMA fix (1.1.82), traffic reports (1.1.81), the scan hold and history (1.1.80), the ROC switch (off), and llw0 off.

## Tests

- test-awdl-ba: every wide command sent has a completing response case; the three commands are in the completing block.

All 24 suites pass.
