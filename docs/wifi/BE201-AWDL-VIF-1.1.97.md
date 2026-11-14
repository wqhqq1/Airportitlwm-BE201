# AirportItlwm 1.1.97: a 10 ms gap before every ROC ADD

The defaults are the same as in 1.1.93–1.1.96. ROC and the second-channel switches stay off, and the Bluetooth drivers are unchanged (2.7.13 / 2.5.10).

## 1.1.96 result (2026-11-12 21:21, `roc-20261112-212124.txt`)

The router was on 153/80. The phone was not an awdl0 peer in any phase.

- **R1 mode 1 with the DTIM cap (cap 80 TU):**
  - 65 ROCs started and ended, and 1 failed.
  - 59 of 65 ran their whole requested time; the average dwell was 77.2 ms. The firmware does **not** cap ROCs near 41 ms; 1.1.95's 41 ms came from our 16 TU slots.
  - Start was 7.4 ms late on average, 45.2 ms at most.
  - There were 13 chained ADDs, and the average gap from one ROC's end to the next start was 87 ms.
  - The radio was on 149 about 28 % of the time, discovery ROCs included.
- **Firmware assert 18 s in:**
  - Error 0x20103620, data 2.
  - Last host command 0x32030E = ROC_CMD (MAC_CONF group 3, command 0x0E, sequence 0x32).
  - FaultRoc 0x950125: an ADD pending on 149, none running, AUX station up, activity 2, mode 1.
  - AWDL latched off, so every later phase was skipped. The router ping showed 33 % loss in that phase, during the restart.
- **The same assert ID on ROC_CMD was seen on 2026-11-11 16:08**, when HOTSPOT was the activity. It is the firmware's general "ROC_CMD refused" assert, and data 2 is the activity.

**Reading:** 1.1.96 was the first version that added an ROC straight from the end notification, within about a millisecond.

- 1.1.95's ROCs always ended long before the next slot tick.
- Linux (v6.11 iwlmvm) never re-adds an activity that fast. Its `roc_done` work flushes the AUX station and removes it first. Its ADD then goes out with a max delay of up to 3 × DTIM and a duration of DTIM − 20 TU (`iwl_mvm_roc_duration_and_delay`).

The likeliest cause is that the firmware had not yet released activity 2 when the next ADD arrived. This is not proven.

## Change

- **`IWX_AWDL_ROC_READD_US` = 10 ms.** No ROC ADD goes out sooner than this after the last ROC ended, failed or was removed (`iwx_awdl_roc_readd_wait`).
  - The slot tick returns while the gap runs (`RocReaddWaits`), discovery included.
  - The chain task sleeps out the rest of the gap on its task thread, outside the gate. It then checks again in the gate and skips if it is still too soon.
  - A failed notification, a REMOVE and a stale REMOVE all start the gap, as an end does.
- **The last ADD is recorded:**
  - how soon after the previous end it went (`RocReaddMinUs` keeps the shortest);
  - at a firmware fault, `ItlwmAwdlFaultRocAfterUs` and `ItlwmAwdlFaultRocAdd`: source (1 slot, 2 chain, 3 discovery) | duration << 8.
- **`roc_test.py`:**
  - R1 now runs the phase without the DTIM clamp first (20 s). One ROC covers a whole run there, so few ADDs follow an end.
  - Then comes the clamped, chained phase (30 s).
  - The tool prints the 149 time share, the shortest end-to-ADD time, the deferred ADDs, and, on a fault, the last ADD.
  - The other phases are as in 1.1.96.

## How to read the next test

- **No fault in either R1 phase:** the gap was the cause. Then the duty figures decide route ①:
  - 149 share in the unclamped phase;
  - router ping loss and average.
- **A fault again:**
  - "距上次结束" (time since the last end) well above 10 ms points away from the gap. Then suspect the duration against `max_delay`: we send 16 TU, Linux 200–300 TU.
  - "来自接续" (from the chain) against "来自时隙" (from the slot tick) says which path sent the ADD.
