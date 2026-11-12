# AirportItlwm 1.1.92: in mode 4, unicast frames wait in the host for an ROC

The defaults are the same as in 1.1.88. The ROC switch stays off, and the Bluetooth drivers are unchanged.

## 1.1.91 result, boot 2026-11-12 08:59, test at 09:01

- **Router:** channel 153 at 80 MHz. No firmware error in the whole test.
- **Mode 1, P2P_TXRX:**
  - 66 ROCs, all started and ended.
  - Start delay: 6.5 ms average, 38.8 ms maximum. Dwell: 64.8 ms average.
  - Router ping: 28 ms average.
- **Link on 149, ROC off:** RxPhy2 24, system peers 1.
- **Mode 4, 90 s:**
  - ROCs: 184, all started and ended. Start delay 5.7 ms average, 90.6 ms maximum. Dwell 56.9 ms average, so 10.5 s of the 90 s were spent on 149.
  - AUX transmit: 62 sent.
    - Multicast: 38, all ok.
    - **Unicast: 24, none acknowledged.** 23 of them completed after their ROC had ended, and 1 during it.
    - All 24 failed with long limit (`0x83`), with only 3 retries among them.
    - The phone's schedule had it on 149 for 6 of them, and unknown for 18.
  - RxPhy2 24, system peers 1. The phone saw the Mac; nothing transferred.
  - Router ping: 62 ms average.

## Reading

- **The unicast frames were never really sent on 149.**
  - Almost every failure completed when no ROC was running, and the firmware spent almost no retries on them.
  - In mode 4 the driver queues AWDL frames on the AUX queue between ROCs, on the assumption that they wait there for the next ROC. They do not: the firmware ends them without sending, or sends them while the radio is away.
- **Multicast success says nothing:** a multicast frame needs no ACK.
- **1.1.90 had the same pattern:** its 311 "ok" were mostly multicast.

## Change

- **Host hold (mode 4 only, unicast AWDL frames):**
  - In `iwx_tx`, a frame waits in the host instead of entering the AUX ring when no ROC is running, or when the running one has less than 4 ms left (`iwx_awdl_roc_hold`).
  - The ROC's end is its start notification plus the duration it was requested with.
  - Up to 16 frames wait, oldest first. A full queue drops the oldest (RocHoldFull), and a frame older than 300 ms is dropped (RocHoldExpired).
  - The frame keeps its node reference, and both are freed when it is dropped.
- **Release:**
  - A task under the gate sends held frames while the ROC has time left and the AUX ring has room, through `iwx_tx` again (RocReleased).
  - It runs at each ROC start notification and at each slot tick.
- **Cleanup:** when the ROC test is torn down or the interface stops, the held frames are freed (RocHoldFreed).
- **Unchanged:** multicast frames, and modes 1–3.
- **ROC tool:** the new counters appear in each phase's changes.

## Before the next Sequoia update

This machine's 24G824 Boot kernel collection and kernel are saved in `deps/kc-24G824/` (with SHA256 and version), to compare the private IO80211Family layouts after the user updates Sequoia themselves.

## Tests

- **test-awdl-ba:**
  - The hold rule: mode, no ROC, no start, the margin, the end.
  - The ring tail and staleness.
  - The `iwx_tx` hold: before the ring, the oldest dropped when full.
  - The flush order: expiry, then the rule, then the flushing mark around `iwx_tx`.
  - Freeing of mbuf and node on a drop, on teardown and on stop.
  - The start notification and the tick trigger the flush, and the duration is recorded at ADD.
  - The task is registered and removed, and the properties are published.
- **Result:** all 25 suites pass.
