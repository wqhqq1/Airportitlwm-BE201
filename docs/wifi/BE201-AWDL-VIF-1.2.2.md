# AirportItlwm 1.2.2: family timing again, 5 slots, multicast headroom

The defaults are the same as in 1.1.93–1.2.1. ROC and the second-channel switches stay off until the tool or `开启跨信道隔空投送.command` sets them (RAM only). The Bluetooth drivers are unchanged.

## 1.2.1 result (2026-11-13 17:23, `roc-20261113-172259.txt`)

The router was on 44, a channel AWDL also visits. ROC was still exercised on 149. The user said some typed answers in the file were wrong, so this reading uses the logged counters only.

| R2 phase | AirDrop | AUX unicast data ok / fail | Frames per ms of dwell | Air share of dwell | On 149 |
|---|---|---|---|---|---|
| phone-timed (60 s, file sent again) | 0.00 MB/s | 101 / 2 | 0.02 | 0 % | 33 % |
| **family-timed, 1.2.0 behaviour (45 s)** | **1.56 MB/s** | **46188 / 4** | **2.27** | **39 %** | 45 % |
| phone-timed, unclamped (45 s) | 0.14 MB/s | 4861 / 1 | 0.34 | 6 % | 33 % |

- **Phone-timed phase:** only 128 data frames were offered. The phone's and the family's sequences widened to 12 of 16 slots on 149 during it, so this was the connection being set up.
- **Family-timed phase:**
  - the file moved (46258 frames);
  - 171 frames per ROC on average, 287 at most;
  - the hold was at its 192 limit, and the family waited 2978 times;
  - air time 173 µs per frame at VHT 2SS MCS8 20 MHz (`0xC318`).
- **Phone-timed, unclamped:** the sequences went back to idle during the phase.
- **Timing:** both clocks agreed. The slot index difference was 0, and the phone's boundary was 2.6 ms from our tick on average. Phone timing changes nothing, and misalignment did not cause the 17:03 failure.
- **Ring-full drops:** 232 frames dropped in the family-timed phase (`RocTxDrop`). Unicast waits in the hold, so these were other kinds, mostly multicast.
- **Router:** 0 % loss in all phases, 37–51 ms average, 307 ms at most.

**Reading:**
- 1.2.0's direct refill raised the ROC to 2.27 frames per ms (0.97 before), and the transfer reached 1.56 MB/s.
- What is left:
  - the time on 149 (45 %: only 4 slots of each 5- or 6-slot run);
  - the radio sending only 39 % of the ROC time (single MPDUs, each with its own channel access and ACK).

## Change

1. **The family's slots time mode 4 again by default.** The phone's schedule is now opt-in with flag 0x800 (`IWX_AWDL_ROC_F_PHONE`); the 1.2.1 code is kept behind it.
2. **ROCs cover 5 slots of each 149 run** (about 328 ms).
3. **Multicast gets 16 frames of headroom on the AUX ring** (`IWX_AWDL_ROC_MCAST_EXTRA`), so sync frames are not dropped while unicast fills it.
4. **Why a flush stops is counted:** `RocFlushStopRing` (ring cap) and `RocFlushStopRule` (no ROC, end near, or phone not there yet).
5. **`roc_test.py`:** R2 default (60 s, send again), default at 80 MHz (45 s), phone-timed (45 s).

## How to read the next test

- **R2 default** against 1.56 MB/s, with 149 share against 45 %.
- **Router** loss and maximum ping with 5 slots.
- **80 MHz:** the air time per frame drops to about a quarter. If the speed does not rise, the per-frame overhead outside the air time is the limit, and A-MSDU or aggregation is next.
- **Flush stop counters:** many ring stops and few rule stops mean the firmware is draining slower than we refill. Many rule stops mean the ROC timing is the limit.
