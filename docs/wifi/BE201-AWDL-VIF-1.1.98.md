# AirportItlwm 1.1.98: unicast frames dropped at an ROC's end go back to the hold

The defaults are the same as in 1.1.93–1.1.97. ROC and the second-channel switches stay off, and the Bluetooth drivers are unchanged (2.7.13 / 2.5.10).

## 1.1.97 result (2026-11-12 21:40, `roc-20261112-214019.txt`)

The router was on 153/80. The system saw 1–2 AWDL peers, but there was no awdl0 neighbour and no transfer.

- **No firmware error in any phase**, across about 490 ROCs, 84 of them 80 MHz. The shortest end-to-ADD time was 10.3 ms. The 10 ms gap held, so the 1.1.96 assert came from the immediate re-ADD.
- **Router:** 0 % loss in every phase, 13–27 ms average.
- **R1 mode 1:**
  - Without the DTIM clamp: 53 ROCs, all full, 105 ms average dwell.
  - With the clamp: 88 ROCs, 82 ms average dwell.
  - On 149 24–28 % of the time, discovery included. The family's own sequence put 149 in only 2 of 16 slots while idle.
- **R2 mode 4 (link on 149, clamped, honest sequence, 60 s):**
  - 144 ROCs. Dwell over covered time was 96 %: the radio is on 149 for nearly all the time it announces.
  - Multicast: 272 ok.
  - **AUX unicast: 42 sent, 8 acknowledged.** Of the 34 failures, 32 completed after their ROC had ended (`RocTxFailOut`). All were long-limit 0x83, with 45 retries over 34 frames.
  - Hold: 30 held, 29 released, 1 expired.
  - In 1.1.95 (one short ROC per run, released only at the ROC start), 32 of 34 went through.
- **A-MSDU:** never used on this path (`AmsduSent` 0).
- **80 MHz ROC:** 84 ROCs, no error, unicast 5/29.
- **S probe:** one frame; nothing to read.

**Reading:** the firmware fails what is still queued on the AUX ring when an ROC ends. These are not frames the phone ignored, which would show many retries. Chained, shorter ROCs end more often, and since 1.1.96 frames are also released mid-ROC (on every completion, 6 ms margin) behind queued multicast. So more unicast is caught by an end.

## Change

**A unicast frame dropped at an ROC's end goes back to the hold.** This applies to mode 4 only, and only to a failure that completes after the ROC ended with at most 2 retries. Each frame can come back at most 3 times (`iwx_awdl_roc_requeue_ok`).
1. At the completion (`iwx_awdl_roc_requeue_prep`), the 802.11 header that `iwx_tx` trimmed into the TX command (gen3, after the 28-byte command) is put back in front of the mbuf.
   - This happens only when the trim left that much leading room; otherwise the frame is freed as before (`RocRequeueDrop`).
   - The header lies after TB0, so the firmware never writes over it.
2. `iwx_txd_done` then moves the mbuf and its node reference to the hold's tail (`iwx_awdl_roc_requeue_take`) instead of freeing them. Ring accounting is unchanged.
3. The next ROC start flushes the hold as usual. The count travels through the flush in `hold_rq` / `flush_rq` / `awdl_rq`.

**New counters:** `RocRequeued`, `RocRequeueDrop`.

**New kernel import:** `_mbuf_leadingspace` (BSD mbuf KPI, exported by the running kernel next to `_mbuf_prepend`).

**`roc_test.py`** (about 5 minutes):
- baseline;
- R1 unclamped, 15 s;
- link to 149;
- R2 mode 4 clamped, 60 s (send again);
- R2 mode 4 unclamped, 45 s;
- R2 mode 4 unclamped at 80 MHz, 45 s;
- after off.

The A-MSDU and S phases are gone. The tool prints the requeued and dropped counts and AUX unicast data ok/fail.

## How to read the next test

- **Requeued > 0 and AUX unicast ok well above the 8/42 of 21:40:** the requeue is working. Then check whether the transfer starts and whether the family widens its 149 slots.
- **Requeued > 0 but still failing on the next ROC:** look at `RocTxFailIn` against `FailOut`. Many failures inside the ROC would mean the phone is not on 149 when we send.
- **RequeueDrop high:** the header room check failed. The frame mbufs need a copy instead.
- **Unclamped against clamped:** fewer ROC ends should mean fewer drops.
