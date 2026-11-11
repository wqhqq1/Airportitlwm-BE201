# AirportItlwm 1.1.62: why nothing transmits on the second channel

## 1.1.61 router test, 2026-11-08 18:52 (channel-20261108-185216.txt)

The user answered "sees Mac, transfer not moving" in every phase, including router only. No firmware error.

| Phase | Own queue | Other counters | Router RTT |
|---|---|---|---|
| Router only (link on PHY 0) | OwnSent 59, OwnOk 57 | — | 4 ms |
| Mode 5 | OwnSent 65, OwnOk 0, OwnKeptMoves 6 of 60 moves (the queue was held most of the time) | RxPhy2 265, DataRx 192 | avg 137 ms, max 1.25 s |
| Mode 4 | — | similar | avg 143 ms |

1.1.60's mode 3, where link 1 stays on PHY 1 with windows, also completed no own-queue frame. So the problem is not the moves. Frames for the peer station on link 1 do not complete while link 1 sits on PHY 1, while reception there works.

Side effect: OwnRecoverFails reached 4, so the own queue gave up for the rest of the boot, on the AP's channel too.

## Change

- **Session protection kind (RAM switch, off by default):**
  - `debug.be201_awdl_phy2_te` is now mode + 16 × kind, and the kind is passed to the HAL above the mode.
  - The kinds are 0 ASSOC (as before), 1 GO_CLIENT_ASSOC, 2 P2P_DEVICE_DISCOV and 3 P2P_GO_NEGOTIATION.
  - The kind is latched only when no window is running, and adds and removes use the latched kind. The context's own TE paths stay ASSOC.
  - Property: TeConf.
- **Mode 5 peer refresh:**
  - After every successful move, the kept own queue's station gets STA_CONFIG (A-MPDU fields) and TLC again, as Linux re-inits rate control after a channel context change.
  - Counters: OwnRefreshes and OwnRefreshErr.
- **New counters:** OwnSentPhy2 and OwnDonePhy2, the own-queue frames sent and completed (TX responses or BA `txed`) while link 1 is on the second channel.
- **Fix:** turning the second channel switches off clears held and the rebuild budget and rebuilds the own queue, so a test no longer costs the boot its AirDrop speed.
- **Tool:** router only 20 s, mode 5 with kind 0, 1 and 2 for 30 s each, then off 20 s (the queue should come back). It saves after every phase.
- **Tests:** test-awdl-ba covers the encoding, latching between windows, kind use in adds and removes, the off reset and the mode 5 refresh. test-awdl-ctx gets a fallback for the MAX_ID macro.
