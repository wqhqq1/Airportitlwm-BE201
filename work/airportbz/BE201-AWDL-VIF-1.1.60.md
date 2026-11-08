# AirportItlwm 1.1.60: mode 4, the AWDL link follows this Mac's own sequence

## 1.1.59 router test, 2026-11-08 06:51-06:56

The tool was closed before it saved, so there is no per-phase result.

- **Log:** the family saw 2 peers the whole time, with rtg 0.
- **Counters:** Phy2Auto 149, SeqChan5 36/149, CtxTeOwn 138 of 194 windows, RxPhy2 583.
- **User:** "during the test the phone could no longer find the Mac", and the Mac's send stayed "waiting". So before the second channel came on, the phone did see the Mac.

The family's sequence on the router is `36 0 149 0 0 0 0 0 6 0 149 0 ...`. Slot 0 is on the AP's channel, which is where the phone found this Mac. Modes 2 and 3 move link 1 to PHY 1 on 149 for good, so nothing answers in slot 0 on 36 any more.

## Change (RAM switch, off by default)

- **Next 5 GHz slot:** the AW tick now also reports the next slot (from the current one on) whose channel is 5 GHz. It is packed above the run length (`run | next5 << 8`) and kept as `slot_next5`.
- **Mode 4 (`debug.be201_awdl_phy2=1`, `debug.be201_awdl_phy2_te=4`):**
  - The wanted second channel each tick is `iwx_awdl_phy2_follow(cand, slot_next5)`: the automatic candidate when the next 5 GHz slot is on it, otherwise 0 (the AP's channel).
  - The existing phy2 task moves the link, one slot ahead: it ends any window, releases the own queue, then deactivates, rebinds and activates the link.
  - On a router on 36 that is 149 from slot 1 to slot 10 and 36 from slot 11 to slot 0, two moves a cycle (about 1 s). The 2 s stability wait does not apply in this mode.
  - Windows are as in mode 3: at the first slot of each own run on the second channel.
  - Counters: Phy2SlotMoves and SlotNext5.
- **Own queue:** it is released at every move and rebuilt by the 1 s retry. Data is expected to be slow in this mode; the test is about discovery and connection.
- **Tool:** 开始信道实验.command runs router only (20 s), mode 4 (40 s), mode 3 (30 s), then off. It saves after every phase and asks whether the phone sees the Mac. The windows mode is set before the automatic channel.
- **Tests:** test-awdl-ba covers `iwx_awdl_phy2_follow`, the mode 4 source paths and acceptance of 4 from RAM.
