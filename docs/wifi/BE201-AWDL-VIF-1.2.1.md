# AirportItlwm 1.2.1: ROCs timed by the phone's own schedule

The defaults are the same as in 1.1.93–1.2.0. ROC and the second-channel switches stay off until the tool or `开启跨信道隔空投送.command` sets them (RAM only). The Bluetooth drivers are unchanged.

## 1.2.0 result (2026-11-13 17:03, `roc-20261113-170321.txt`)

The router was on 157. **Nothing transferred.**

The family's sequence stayed idle the whole time: 149 appeared only as single slots (2 of 16, sometimes 5).

**R2 mode 4 (clamped, 60 s):**
- 154 ROCs, all full, 80 ms average.
- **AUX unicast data: 0 of 137 acknowledged.**
  - 130 failures completed after their ROC had ended, with 22 retries over 137 frames.
  - 101 were requeued, and they failed again at the next ROC end.
- At completion, the phone's own schedule (`TxFailHere`) had it on 149 for all 137.
- Multicast: 64 ok.
- About one frame per ROC.

**Unclamped and 80 MHz phases:** the same pattern (3/93 and 0/65).

**Router:** 0 % loss.

**Reading:**
- Our ROCs follow this Mac's family slot tick and sequence, and in this run that window did not meet the phone's 149 time.
- The frames sat in the AUX ring through the ROC without being sent, while the phone's schedule had it on 149 just after.
- With single-slot runs, any slot offset or index mismatch leaves no overlap.
- At 22:49 (transfer running, 6-slot runs) and 23:17 (router on 6), the long runs hid this.

## Change

1. **Mode 4 follows the phone's own schedule** whenever its sync frames give one (`iwx_awdl_peer_run`: its sequence `sync.seq`, its AW timing `ttn`, `aw_seq` and `presence`, as `iwx_awdl_peer_slot_chan` already used). At each slot tick:
   - **The phone is in a 149 run now, or one starts at its next boundary** (at most 4 slots of the run): the ROC covers until the phone's run ends (`cov_end_us`), and the chain extends it as before.
   - **The phone has no 149 run now or next:** no ROC.
   - **No sync data:** the family timing, as before.
2. **Held unicast frames wait for the phone's run to start.**
   - Before 1.2.1, inside any ROC with time left, they were released at once.
   - Now `iwx_awdl_roc_peer_wait` checks the hold rule, the flush and `iwx_tx`.
   - When an ROC starts before the phone's run, `awdl_roc_peer_task` sleeps on the task thread until the run starts, then flushes in the gate (`RocPeerWaits`).
3. **Mode 4 announces the phone's slots** in this Mac's numbering, shifted by the slot-index difference `k` (`iwx_awdl_peer_k`), so the phone sends to us when we are there.
4. **Flag 0x800** brings back the family timing for comparison; the switch accepts values below 0x1000.
5. **Diagnostics:**
   - `RocPeerTicks` / `RocPeerIdleTicks`: ticks with and without a phone run;
   - `RocPeerK`: the phone's slot index less ours;
   - `RocPeerLagUs` / `RocPeerLagAbsMs`: the phone's boundary against our tick;
   - `ItlwmAwdlRefSeq`: the phone's 16-slot sequence.
6. **`roc_test.py`:**
   - R2 phone-timed (60 s), family-timed (0x800, 45 s), phone-timed unclamped (45 s).
   - It prints the phone's sequence, the slot-index and boundary offsets, and the waits.

## How to read the next test

- **手机时间表 (the phone's sequence) against 时间表 (ours), and 时隙号差 (slot-index difference):** a non-zero index difference, or a mean boundary difference of tens of ms, confirms the cause.
- **AUX unicast data, phone-timed against family-timed:** phone-timed should be well above 0/137.
- **If phone-timed still fails with FailOut**, the firmware is not sending inside the ROC even while the phone is there. The next step is the frames' rate and the AUX station: air time and rate are in the line.
