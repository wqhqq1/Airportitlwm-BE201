# AirportItlwm 1.1.61: mode 5 keeps the own queue across the link moves

## 1.1.60 router test, 2026-11-08 18:23 (channel-20261108-182220.txt)

When the AirDrop started, the family's sequence was `149 149 149 0 0 0 0 0 6 149 149 0 ...` (more 149 slots, no 36). By the end of the first phase it was back to `36 0 149 0 0 0 0 0 6 0 149 0 ...`.

| Phase | Phone sees Mac | Counters | Router RTT |
|---|---|---|---|
| Router only | no | OwnSent 3 | 3.7 ms |
| Mode 4, 40 s | **yes** | Phy2SlotMoves 78, RxPhy2 140, 55 windows, OwnSent 55 / OwnOk 8, OwnRetries 39, DataTx 64 / DataRx 64 | avg 59, max 328 ms |
| Mode 3, 30 s | no | RxPhy2 70, 56 windows | avg 116, max 357 ms |
| Off | no | — | 3.4 ms |

- **All phases:** no awdl0 neighbor, rtg 0, no firmware error. The transfer never started.

Reading:
- Mode 4 restores discovery.
- Data fails: every move away from 149 released the own queue, and the 1 s retry rebuilt it too late, so it was almost never active. Unicast AWDL data then went on the AP station's queue on 36 (`first_data_qid`), where the phone was not listening. Even IPv6 neighbor discovery never completed.

## Change (RAM switch, off by default)

- **Mode 5 (`debug.be201_awdl_phy2=1`, `debug.be201_awdl_phy2_te=5`):** the same as mode 4, except when leaving the second channel. While the own queue is active, the phy2 task flushes the own station's TIDs (TXPATH_FLUSH) and keeps the queue, instead of releasing it. Counter: OwnKeptMoves.
- **Risk:** the 06:29 assert on 2026-11-06 (0x2000320F at LINK_CONFIG) happened with a window running and the own queue allocated. The window is still removed first, so this mode shows whether a live queue alone is a problem. An assert trips AWDL for the boot, and the tool then stops.
- **Tool:** router only 20 s, mode 5 45 s, mode 4 25 s (comparison), off 15 s. It saves after each phase and asks about visibility.
- **Tests:** test-awdl-ba checks that only mode 5 flushes and keeps the queue (other modes still release it), and that 5 is accepted from RAM.
