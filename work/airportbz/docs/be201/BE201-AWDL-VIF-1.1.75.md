# AirportItlwm 1.1.75: remain-on-channel test for the second channel

Includes 1.1.74, which was not installed on its own:
- awdl0 runs again after Wi-Fi off and on (`restoreRunning`);
- llw0 is off by default.

## Why ROC

See BE201-AWDL-VIF-1.1.74.md. In short:
- The firmware schedules a client link on another PHY from its AP's beacons, and AWDL has none.
- Intel's Linux driver (iwlmld `roc.c`) sends off-channel frames during an `ROC_CMD`, through an AUX station, with `node_addr` as the receive filter.
- This firmware lists `ROC_CMD` version 4. The version-5 layout is used, as iwlmld does for versions below 6.

## Test switch

`debug.be201_awdl_roc` is a RAM switch, 0 by default. Mode in bits 0-3, activity in bits 4-5:

| Mode | What it does |
|---|---|
| 0 | off |
| 1 | ROC only: does the firmware grant it, and does the radio hear AWDL there (RocRxDuring) |
| 2 | also AWDL management and multicast frames on the AUX queue during an ROC |
| 3 | also unicast AWDL data (bypasses the own queue for that frame) |

Activity: 0 hotspot, 1 P2P discovery, 2 P2P action frames, 3 P2P negotiation.

## Driver

- **Conditions:** only beside a working AP link: context mode 6 active, not solo, not tripped, RUN, AP port valid, MLD queues active.
- **Setup** (`iwx_awdl_roc_task`, a task under the gate):
  1. `AUX_STA_CMD`: station 12, lmac 0, as iwlmld.
  2. `SCD_QUEUE_CONFIG` ADD for that station on TID 8, as iwlmld's AUX queue.

  A failure removes what was made and stops the test until the switch goes to 0 and back. Properties: RocSetupErr and RocSetupStage.
- **Scheduling** (`iwx_awdl_roc_tick`, from the AW tick at each slot start):
  - One ROC is requested where a run of the sequence's slots starts on a 5 GHz channel other than the AP's.
  - The ROC lasts the run in 16 TU slots, at most 128 TU, with max_delay 16 TU. It is sent with `IWX_CMD_ASYNC` and `node_addr` set to the AWDL address.
  - One ROC at a time. If no notification ends it within 1 s, it is removed (RocStale).
- **Notification:** `ROC_NOTIF` (MAC_CONF 0xF8) updates RocStarted, RocEnded and RocFailed, and sets the active flag.
- **Transmit:**
  - While an ROC is active, `iwx_tx` sends the frames the mode takes on the AUX queue: at most 8 waiting (RocTxDrop), completions in RocTxOk and RocTxFail.
  - The own queue does not take them back.
  - The rate is OFDM 6 Mb/s or more (5 GHz).
  - The TX watchdog ignores frames held on that queue between ROCs.
- **Receive:** AWDL frames heard on the ROC channel are counted in RocRxDuring.
- **Teardown:**
  - In `iwx_awdl_ctx_remove`, before the context: ROC remove, flush, queue remove, then `STA_REMOVE`.
  - `iwx_stop` forgets the state, because the firmware is gone.
  - `iwx_txq_owned` includes the AUX queue.

## Tool

`开始ROC实验.command` needs the Mac on a router channel other than 149. Phases:
1. Baseline, 20 s.
2. Mode 1 with activity 0, 25 s. If nothing started, mode 1 again with activity 2.
3. Mode 2, 30 s, then mode 3, 40 s, only if an ROC started.
4. Off.

Each phase records the counters, the peer counts, the router and phone RTT and the user's answer. The results file is roc-*.txt in the kit.

## Tests

- test-awdl-ba:
  - the mode and activity decoding, what each mode sends, the duration;
  - the `ROC_CMD` v5 field order;
  - the tick and the teardown order, the setup order and failure;
  - the readiness conditions and that `ctx_remove` removes the ROC first;
  - routing ahead of the own queue, completions, the watchdog, ownership, the rate and the notification.
- test-awdl-vif: 21 sysctls.
- test-beacon-peer-tx: mock fields.

All 24 suites pass.
