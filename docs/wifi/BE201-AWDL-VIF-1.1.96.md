# AirportItlwm 1.1.96: chained ROCs over whole 64 TU slots (route ①)

The defaults are the same as in 1.1.93–1.1.95. ROC and the second-channel switches stay off, and the Bluetooth drivers are unchanged (2.7.13 / 2.5.10).

## Why

The 1.1.95 test (16:12) acknowledged AUX unicast (32/34 ok, data 26/28), but this Mac was on 149 for only 7.9 % of its 149 time. Of 101 held frames, 73 expired. The sync frames claimed 149 in every slot. The second Fable 5.2 review traced this to host limits (`docs/wifi/下一步方案-20261112.md`):
- 16 TU ROC slots, while a sequence slot is 64 TU;
- one ROC per run;
- a flush only at ROC start and at slot ticks, capped at 8 queued frames;
- a 16-frame / 300 ms hold.

## Change

- **Slot length:** `IWX_AWDL_ROC_SLOT_TU` is 64.
- **The family's sequence reaches the HAL:** the AW timer passes the whole 16-slot sequence and the current slot (`setAwdlSequence`, new HAL hook) before each slot tick.
- **Coverage:** `iwx_awdl_roc_cover`: the 149 slots within the first 4 of each 149 run (`IWX_AWDL_ROC_RUN_MAX_SLOTS`, about 262 ms, so the AP keeps its beacons).
  - Each tick records the covered slots left and when they end.
  - Covered time is summed while ROC is on (RocCovSumMs).
- **ROCs:**
  - Any covered tick with no ROC running adds one for the covered time left.
  - The time is capped at `iwx_awdl_roc_cap`: 256 TU, and under the DTIM interval less 20 TU (the Linux rule) unless switch flag 0x200 is set (RocCapTu).
  - The ADD is shared (`iwx_awdl_roc_add`).
- **Chain:**
  - An end notification queues `awdl_roc_chain_task`, which adds the next ROC at once while more than 15 ms of covered time is left.
  - It follows the tick's rules: no ROC pending, ready, no link move, same mode and activity.
  - Counters: RocChainAdds/Skips, and RocChainGapN/SumMs (the time between an end and the next start).
- **Dwell:** each ROC's run time against its request, in four buckets (RocDwell25/50/75/Full). RocReqSumMs sums the requests.
- **Hold:**
  - 128 frames and 1 s (was 16 and 300 ms).
  - The AUX ring takes 24 frames while an ROC runs (8 otherwise, `iwx_awdl_roc_ring_cap`).
  - A 6 ms margin.
  - Each AUX completion also runs the flush.
- **Honest sequence (mode 4):** while ROC mode 4 runs with its AUX station, both channel-sequence TLVs (4 and 18) carry 149 only in covered slots and 0 elsewhere (`iwx_awdl_put_chanseq16`, RocAnnounce). Other modes keep every slot on the current channel.
- **80 MHz probe:** switch flag 0x100 sends the ROC at 80 MHz with the control position inside its block (`iwx_awdl_ctrl_pos80`: 149 is "2 below" 155). ROC frames may then use 80 MHz rates (RocWideAdds).
- **The ROC switch** `debug.be201_awdl_roc` accepts values below 0x400: the mode and activity as before, plus the flags.

## ROC tool (about 7 minutes)

1. Baseline.
2. **R1:** mode 1 for 30 s with the DTIM cap, then 20 s without it. Each prints the 149 duty (dwell ÷ covered time), the chain counts and gap, the cap and the dwell buckets.
3. Link on 149.
4. **R2:** mode 4 for 60 s with the honest sequence.
5. Mode 4 plus A-MSDU (`debug.be201_awdl_amsdu`), 40 s.
6. Mode 4 plus 80 MHz ROCs, 40 s.
7. **S probe:** ROC off and the link back on the router (153/80) for 20 s. TxOk/FailHere/Away show whether unicast frames to the phone on 149 are acknowledged from 153/80.
8. After off.

The first firmware error switches ROC, windows, A-MSDU and the second channel off (the link last). The session-window phase from 1.1.95 is gone: it carried no frames.

## Pass marks

- **R1:** 149 duty ≥ 50 %, RocFailed < 10 %, no firmware error, router loss < 5 %, ping < 150 ms.
  - If dwell stays near 41 ms whatever is requested and the duty stays under 30 %, the firmware caps it.
- **R2:** HoldExpired < 10 % of Held, AUX unicast ok ≥ 90 %, a 100 MB AirDrop completes at ≥ 0.5 MB/s.

## Tests

- **test-awdl-ba:**
  - Unit tests for coverage, the wrap-around, coverage when the channel fills every slot, covered slots left, the cap, the chain rule, dwell buckets, the 80 MHz positions, the ring cap, the switch decode and the honest sequence bytes.
  - Source checks for the tick (covered time, discovery first, then the cap), the shared ADD, the chain task's guards, and the notification order (dwell, end, chain).
  - Source checks for the task registration, the flush on completion, the announcement in both TLVs, the HAL hook, the switch range and the tool's phase order.
- **test-beacon-peer-tx, test-awdl-vif:** stubs extended.
- **Result:** all 25 suites pass. `install.py --check` PASS.

## Kit and install

- **Kit:** AirportItlwm 1.1.96, UUID `ce7e5b91-0c9e-3c6f-9876-a8c5f03291de`, SHA `aaa2ab31`. No new imports.
- **Installed:** 2026-11-12 18:46 on EFI disk0s3.
  - Backup: `EFI-backups/EFI-before-install-20261112-184611`.
  - Recovery: AirportItlwm 1.1.95 (`80c53cb0`). Bluetooth untouched.
- **Config:** compared with a copy taken just before, only the Wi-Fi row comment changed.
  - config equals pending, ocvalidate clean, boot-args unchanged, Kernel/Add 35.
  - ShowPicker False, Timeout 0, TakeoffDelay 100000, MacBookPro16,2, BE201BluetoothFirmware `bb027eb4`.
