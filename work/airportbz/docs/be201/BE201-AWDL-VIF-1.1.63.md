# AirportItlwm 1.1.63: block ack on the second channel, safe protection kinds only

## 1.1.62 router test, 2026-11-08 19:17 (channel-20261108-191642.txt)

The user answered "sees Mac, transfer not moving" throughout.

| Phase | Result |
|---|---|
| Router only | OwnSent 1, OwnOk 1; router 2.8 ms |
| Mode 5, kind 0 | Phy2SlotMoves 36, OwnKeptMoves 8, OwnRefreshes 17, OwnSentPhy2 9, OwnDonePhy2 0, RxPhy2 140, 48 windows; router avg 83, max 806 ms |
| Mode 5, kind 1 (GO_CLIENT_ASSOC) | Firmware assert at once: ItlwmFwErrorId 0x2000150D, last host cmd 0x00530305 (MAC_CONF_GROUP 0x05, SESSION_PROTECTION_CMD). TxTripped; the tool skipped kind 2. |

Reading:
- On PHY 1 own-queue frames get neither a success nor a failure: the firmware does not try them.
- The refresh after moves changed nothing.
- On PHY 0 the same TID 0 aggregation queue works, and there the firmware sets up the block ack agreement itself (BA notifications seen).
- Likely cause: that agreement never forms on 149 within the windows, and an aggregation queue waits for it.

## Change

- **Protection kinds:** only 0 and 2 are accepted; kinds 1 and 3 give 0, off.
- **New counters:**
  - OwnFailPhy2 and OwnLastStatusPhy2: TX responses that failed while link 1 is on PHY 1, and the last status.
  - OwnBaPhy2: block ack notifications there.
- **Tool (no new switch):** router only 20 s, mode 5 with aggregation 25 s, mode 5 without aggregation (`debug.be201_awdl_txagg=0`, so the own queue rebuilds on TID 15, which needs no block ack) 30 s, mode 5 kind 2 without aggregation 25 s, then off. The end restores aggregation to 1, also on exit.
- **Tests:** test-awdl-ba checks the kind restriction; the test-beacon-peer-tx stub gets the new fields.
