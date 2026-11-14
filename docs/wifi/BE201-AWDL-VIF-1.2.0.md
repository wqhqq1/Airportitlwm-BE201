# AirportItlwm 1.2.0: refill the AUX ring at once; the DTIM clamp again

The defaults are the same as in 1.1.93–1.1.99. ROC and the second-channel switches stay off until the tool or `开启跨信道隔空投送.command` sets them (RAM only). The Bluetooth drivers are unchanged.

The version is 1.2.0 because a kext version allows at most two digits in the minor and revision parts, so 1.1.100 would not load.

## 1.1.99 result (2026-11-12 23:17, `roc-20261112-231713.txt`)

**The router was on 2.4 GHz channel 6**, a channel AWDL also visits.

**Baseline without ROC: 2.22 MB/s**, through the own queue on channel 6. As the user noted, this works only because the phone also stays on 6. It is not evidence that ROC is unneeded.

**R2 mode 4 default** (1.1.99: unclamped, 6 slots), 60 s:
- 0.11 MB/s.
- 185 ROCs of 148 ms average; 45 % of the time on 149.
- **About 23 frames per ROC, 0.15 frames per ms of dwell**, although the hold was full (peak 192) and the family was told to wait 270 times.
- Router: 553 ms average, 6.8 s at most.

**R2 DTIM-clamped**, 45 s:
- 0.48 MB/s.
- 218 ROCs of 72 ms; **0.97 frames per ms of dwell**.
- Router: 57.8 % loss.
- The user: the transfer failed after a while. In the next phase the router link was gone ("no gateway").

**AUX unicast data:** 4064/4066 and 15209/15213 acknowledged.

**Reading:**
- Supply was not the limit (the hold was full), and the air link was not either: frames were acknowledged.
- Each ROC drained slowly:
  - A long ROC (over the beacon interval) moved six times less per ms than a clamped one. The firmware likely interrupts it for the AP's beacons.
  - Each completion refilled the ring only through the system task queue, then the gate.
- With 6 slots per run, the AP saw this Mac too little.

## Change

1. **Refill straight away.**
   - `iwx_awdl_roc_flush` (the old task body) now runs in the gate from `iwx_rx_tx_cmd`, right after a completion on the AUX ring advances it.
   - It also runs from the ROC start notification.
   - The task remains for the slot tick and for frames that `iwx_tx` holds (`RocFlushDirect`).
2. **The AUX ring takes 64 frames while an ROC runs.** A frame caught by the end goes back to the front of the hold (1.1.98/1.1.99).
3. **The DTIM clamp is the default again, for every mode**; 0x200 unclamps. 0x400 is accepted and changes nothing.
4. **Back to 4 slots per 149 run.**
5. **Diagnostics:**
   - air time (`wireless_media_time`) and count of acknowledged AUX unicast data (`RocAirMs`, `RocAirN`);
   - the last rate (`RocLastRate`);
   - frames per ROC (`RocSentPerRocMax`).
6. **`roc_test.py`:**
   - R2 default (clamped) 60 s, then unclamped 45 s, then default at 80 MHz 45 s.
   - It prints frames per ROC, frames per ms of dwell, air time per frame and as a share of dwell, the last rate, and the direct refills.
   - It warns when the router is on 6 or 44, where AWDL stays anyway.

## How to read the next test

Test with the router on a channel AWDL does not visit (153 or 36), as at 22:49.

- **Frames per ms of dwell** in R2 default against 0.97 (clamped, 23:17).
- **Air time share of dwell:**
  - **low (under 30 %), with the hold full:** the radio is idle inside the ROC. This points at the firmware's own scheduling (beacon breaks), not at the host.
  - **high:** the rate is the limit. Look at `RocLastRate` and the 80 MHz phase.
- **Router:** 0 % loss expected again with 4 slots and the clamp.
