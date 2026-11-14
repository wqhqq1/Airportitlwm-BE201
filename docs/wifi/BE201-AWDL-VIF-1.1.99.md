# AirportItlwm 1.1.99: speed for cross-channel AirDrop (no drops, flow control, longer stays on 149)

The defaults are the same as in 1.1.93–1.1.98. ROC and the second-channel switches stay off until the tool or the new on command sets them (RAM only, gone at reboot). The Bluetooth drivers are unchanged.

## 1.1.98 result (2026-11-12 22:49, `roc-20261112-224900.txt`)

The router was on 153/80. **The file transferred.** This is the first cross-channel AirDrop transfer.

**R2 mode 4, DTIM-clamped, 60 s:**
- 0.15 MB/s. While the file moved, the family put 149 in 12 of 16 slots.
- AUX unicast data: 5707 ok, 1 failed.
- Requeue: 0. No frame was caught by an ROC end, so the 1.1.98 change was not needed here.
- **432 frames dropped because the AUX ring was full** (`RocTxDrop`), about 7 % of what was sent.
- 5332 frames held and released, with no hold overflow.
- About 18 frames per ROC (325 ROCs, 73.6 ms average dwell).
- About 40 % of the time on 149: 4 covered slots per 6-slot run, and about 45 ms off between chained 80 TU ROCs.
- Router: 0 % loss, 57 ms average, 343 ms at most.

**Other phases:**
- Unclamped (family sequence back to idle): 615/617.
- 80 MHz: 234/236.
- No firmware error in any phase.

**Reading:** the air link is not the limit. At the VHT 2SS MCS8 20 MHz rate, one ROC could carry about 200 frames, and it carried 18. TCP was starved:
- a 7 % loss from the ring-full drops halved its window again and again;
- every RTT waited for the next ROC.

## Change

1. **No drop on a full ring.** In mode 4, a unicast frame also waits in the hold when the AUX ring is full (`RocHoldRing`). It also waits when older frames are already held (`RocHoldOrder`), so frames leave in order. Inside an ROC, the flush task is queued at once.
2. **The hold is 256 frames, and the family's queue is flow-controlled.**
   - At 192 held frames, `iwx_awdl_data_gate` returns Busy. The family keeps the packet, so TCP sees a delay, not a loss (`RocHoldStalls`).
   - At 64, the flush wakes it with `awdlTxRoom` (`RocHoldKicks`).
   - Clearing the hold also wakes it.
3. **Requeued frames go in front, in completion order** (`iwx_awdl_roc_hold_insert`, `rq_batch` reset at each ROC start).
4. **The AUX ring takes 32 frames while an ROC runs** (was 24).
5. **Cover up to 6 slots of each 149 run** (about 393 ms): one ROC of 256 TU, then a chained one.
6. **Mode 4 runs without the DTIM clamp by default.** Switch flag 0x400 asks for it, and the switch accepts values below 0x800. Modes 1–3 keep the clamp unless 0x200.
7. **`开启跨信道隔空投送.command` / `关闭跨信道隔空投送.command`** (`roc_test.py --on` / `--off`) for real use until reboot:
   - ROC off, then link 1 to 149, wait for it, then mode 4 P2P_TXRX;
   - off sets all four switches to 0;
   - if link 1 does not come up, it switches back and says so.

**`roc_test.py`:**
- R2 runs the new default first (60 s, send again), then clamped (0x400, 45 s), then default at 80 MHz (45 s).
- It prints the hold counters: queued behind, ring full, family waits, wakes, peak, overflow, ring-full drops.

## How to read the next test

- **R2 default:** AirDrop MB/s against 0.15; ring-full drops (`环满丢弃`) should be 0; a hold peak near 192 with waits and wakes means flow control works; frames per ROC = RocTxSent / RocStarted.
- **Clamped against default:** whether the DTIM clamp still costs speed.
- **80 MHz:** whether the wider ROC adds speed now that TCP is not starved.
- **Router ping:** with up to 393 ms away, expect a higher maximum; loss should stay near 0.
