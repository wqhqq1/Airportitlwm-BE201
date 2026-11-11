# AirportItlwm 1.1.85: ROC rebuilds on a mode change; discovery ROC

## 1.1.84 result, boot 2026-11-11 15:26

- **Router:** the Mac was on the open channel-60 router (ApPortValid 0, RsnOn 0).
- **First working ROC:**
  - Setup completed: stage 3, AUX station 12, queue 10.
  - In 25 s of mode 1 (activity 0), RocAdds 49, Started 36, Ended 36 and Failed 13 on channel 149.
  - FwErrors 0, and the router ping stayed normal (max 37 ms).
- **No AWDL frame was heard on 149 during the ROCs:** RocRxDuring 0, no family peers, no awdl0 neighbours.
- **Mode 2 sent no ROC at all:** no counter moved, and mode 3 was skipped because of that.
- **AirDrop:** 0 MB/s. The phone saw the Mac.

## Cause

- **Mode 2:**
  - On a mode or activity change, the tick queues `awdl_roc_task` and waits.
  - The task only set up when nothing was set up, and only removed when the switch was off. With a station already set up for mode 1, it did nothing, so every tick waited.
- **Nothing heard on 149:**
  - The ROC follows this Mac's own sequence, one 16 TU slot per run in Low Power (`[60 0 149 0 0 0 0 0 6 0 149 ...]`).
  - Without a peer heard, the AW timing is free-running, so a 16 TU ROC rarely overlaps the phone's time on 149.
  - A firmware receive filter for the activity is also possible. The 1.1.84 counters cannot tell the two apart: RocRxDuring is counted after the AWDL parse.

## Change

- **`iwx_awdl_roc_task`:** a set-up AUX station whose mode or activity differs from the switch, or that is no longer wanted, is removed. Then, if still wanted and ready, it is set up again.
- **Discovery ROC (`iwx_awdl_roc_disc_due`, `iwx_awdl_roc_other5`):**
  - Condition: no AWDL frame from a peer heard on a channel other than the AP's for 2 s.
  - Then one ROC of 120 TU (max_delay 64 TU) on the sequence's 5 GHz channel that is not the AP's, at most once a second. 120 TU is longer than the PSF period of 110 TU.
  - Once the phone is heard there, the sync parser takes its AW timing, and the slot ROCs follow it.
  - Frames on the AP channel do not count as heard: other AWDL devices nearby (ProbeSenders 6) would keep discovery off.
- **New counters:**

  | Property | Counts |
  |---|---|
  | RocDiscovery | discovery ROCs sent |
  | RocRxAny | every frame the firmware hands up while an ROC is active, counted right after the CRC check |
  | RocRxAnyChan | those of RocRxAny on the ROC channel |
  | RocRxAwdlAny | AWDL frames from peers heard while an ROC is active |

  Together with RocRxDuring these separate "the radio heard nothing", "the firmware filtered" and "the phone was not there".
- **ROC tool:**
  - It now runs mode 1 with activity 0 and then activity 2 every time.
  - It keeps the activity whose phase heard more (RxDuring, then RxAnyChan, then Started) for modes 2 and 3.
  - It records the new counters.
- **Installer:** keeps the 1.1.84 merge guards; the packager now asserts they are present.

## Tests

- **test-awdl-ba, C++:**
  - discovery is due with nothing heard, not within the gap, and not within 2 s of a heard frame;
  - `other5` picks the non-AP channel from either byte and returns 0 when there is none;
  - the discovery duration is above 110 TU and within the maximum.
- **test-awdl-ba, source:**
  - the task removes, then sets up, on a mode or activity change;
  - the tick's discovery path, with its delay and counter;
  - RxAny is counted after the CRC check and before the length checks;
  - the heard rule excludes the AP channel;
  - the four properties are published.

All 24 suites pass.
