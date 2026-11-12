# AirportItlwm 1.1.91: why AUX frames on 149 fail

This version adds diagnostics only. How frames are sent does not change. The defaults are the same as in 1.1.88, the ROC switch stays off, and the Bluetooth drivers are unchanged.

## 1.1.90 result, boot 2026-11-12 08:44, test at 08:46

- **Router:** channel 153 at 80 MHz, encrypted.
- **No firmware error in the whole test.** The 20 MHz second PHY context fixed the PHY_CONTEXT_CMD assert: the last PHY command was channel 149, width 0 (20 MHz).
- **Mode 1, P2P_TXRX:** 48 ROCs added, 49 started, 49 ended, none failed. Router ping: 7.4 ms average.
- **Link on 149, ROC off:**
  - RxPhy2 20 and RocRxDuring 20.
  - System peers 1.
  - Router ping: 16 ms average.
- **Mode 4 with the link on 149, 90 s:**
  - ROCs: 166 added, 161 started, 161 ended, 5 failed.
  - Received on 149: RxPhy2 366, RocRxAwdlAny 11. DataTx 448, DataRx 128.
  - System peers 1–2.
  - Router ping: 0 % loss, 20 ms average, 147 ms maximum.
  - **AUX transmit:**
    - 634 frames sent: 311 ok, 321 failed, 18 dropped.
    - Over the whole boot: multicast 533 ok and 0 failed; unicast 730 acknowledged and 427 not.
    - Last failure status `0x83` (long retry limit). Only 144 retries were spent across those 427 failures.
  - The phone saw the Mac. The transfer waited a long time and then failed.
- **After ROC off:** DataRx 3712 and own-queue 611 ok on the AP's channel, but no transfer.

## Reading

- **The link and ROC now work together without a fault.** Frames go both ways on 149 beside the router.
- **About half the unicast frames sent on 149 get no ACK.** The counters cannot tell why. The candidates:
  - The phone was on another channel in its own schedule. The ROCs follow this Mac's sequence, not the phone's.
  - The ROC ended or started late, so a frame went out at the edge of the window or waited in the queue.
  - Frames waiting between ROCs expired.
- **So this version measures** before changing when frames are sent.

## Change

- **Per AUX frame result, `iwx_awdl_roc_note_tx`:**
  - Unicast and multicast results are counted apart.
  - Failures are bucketed by status: short limit, long limit, drain, lifetime, destination power save, FIFO flushed, aborted, other. Published as `ItlwmAwdlRocTxStatus`.
  - Whether the ROC was still running at completion: RocTxFailIn and RocTxFailOut.
  - The reference phone's slot channel at completion: the ROC's channel, another channel, or unknown (RocTxOk/FailHere, Away, Unknown).
  - Retries spent on acknowledged and on failed frames.
- **ROC timing from its notifications:**
  - How long after the ADD each ROC started: RocLateN, RocLateSumMs, RocLateMaxUs.
  - How long each ROC ran: RocOnN, RocOnSumMs.
- **ROC tool:** each phase line adds the failure reasons, the average and longest start delay, and the average dwell. The new counters appear in the changes.

## Tests

- **test-awdl-ba:**
  - The status buckets.
  - The note helper: multicast, unicast, here, away, unknown, in or after the ROC, and retries.
  - Start delay and dwell, including an end without a start.
  - Source checks for the TX completion and notification hooks, the properties, and the restart reset.
- **test-beacon-peer-tx:** mocks for the new completion call.
- **Result:** all 25 suites pass.
