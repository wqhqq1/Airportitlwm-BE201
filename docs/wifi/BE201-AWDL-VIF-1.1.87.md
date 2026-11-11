# AirportItlwm 1.1.87: sending ROC modes use P2P_TXRX

## 1.1.86 result, boot 2026-11-11 16:04

- **Router:** the open router on 157. The Mac was back on 60 afterwards.
- **Mode 1, both activities, no error:**

  | Activity | Adds | Started | Failed | RxAnyChan |
  |---|---|---|---|---|
  | 0 (HOTSPOT) | 73 | 43 | 30 | 6 |
  | 2 (P2P_TXRX) | 48 | 48 | 0 | 0 |

  The tool picked activity 0 by RxAnyChan.
- **Modes 2 and 3 with activity 0:**
  - The firmware asserted twice. FwErrors went 1, then 2, and FaultRearms reached 2.
  - The router ping lost 98 % and then 32 %.
- **Mode 4 with `phy2` 1 (link 1 on 149) — the first exchange on 149 beside the router:**
  - RocRxDuring 189, RxPhy2 189 and RocRxAwdlAny 4: the phone's AWDL frames were received on 149.
  - System peers went from 0 to 2.
  - RocTxSent 279: TxOk 143, TxFail 104, TxDrop 16.
  - DataTx 128, DataRx 45.
  - A third firmware error followed. TxTripped 1 latched AWDL off, and the router link dropped ("no gateway").
  - The error: ItlwmFwErrorId 0x20103620, ItlwmFwErrorCmd 0x23030e (MAC_CONF ROC_CMD).
- **AirDrop:** 0 MB/s. The phone saw the Mac.

## Reading

- **Receive on 149 needs the AWDL link there.** Mode 4 with `phy2` gave the first AWDL frames heard on 149 beside a router, and peers in the family.
- **The firmware errors came only in modes that send on the AUX queue with HOTSPOT:**
  - Mode 1 with HOTSPOT sends nothing, and had no error.
  - In 1.1.85, modes 2 and 3 with P2P_TXRX ran 160+ ROCs with AUX transmit and had none.
  - In iwlmld, HOTSPOT is the activity of station ROC without P2P frames. P2P_TXRX is the one for off-channel P2P transmit and receive.

## Change

- **`iwx_awdl_roc_activity`:** returns 2 (P2P_TXRX) for every mode from 2 up, whatever the switch's activity bits. The setup, the task and the tick all use it, so they agree and there is no rebuild loop. Mode 1 still takes the requested activity.
- **ROC tool:**
  - Phases: baseline 20 s, mode 1 with P2P_TXRX 20 s, mode 4 with `phy2` 1 for 90 s, during which the user sends the file again. Then both switches go off.
  - Modes 2 and 3 and the activity comparison are dropped: they cost firmware errors and answer nothing mode 4 does not.
- **Installer:** keeps the 1.1.84 merge guards and the 1.1.86 boot-argument order. The packager asserts all three.

## Tests

- test-awdl-ba: the activity decode, where modes 2, 3 and 4 give 2 whatever the bits, and mode 1 keeps 0, 1 or 3.

All 24 suites pass.
