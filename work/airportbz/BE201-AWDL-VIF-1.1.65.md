# AirportItlwm 1.1.65: second channel without windows (modes 7 and 8)

## 1.1.64 router test, 2026-11-08 19:44 (channel-20261108-194353.txt)

| Phase | AirDrop | Router RTT | User | Counters |
|---|---|---|---|---|
| Router only (no second channel) | **2.93 MB/s** | avg 6.6 ms | sees Mac, moving | OwnSent 40115, OwnOk 40082 on PHY 0 |
| Mode 5 | 0.07 MB/s | avg 411 ms, max 2.9 s | sees, not moving | OwnSentPhy2 47: 2 done, both failed (status 131) |
| Mode 6 | 0 | avg 52, max 376 ms | sees, not moving | Phy2Qid 11, Phy2QSent 5, Phy2QDone 0, Phy2QDrop 97 (the bounded queue stayed full) |
| Off | 1.49 MB/s | — | moving | — |

The file finished. This is the first AirDrop that worked with the Mac on a router (36), with no second channel at all. The phone came to this Mac's channel.

On the second channel, link 1's queues are almost never sent during session protection windows: neither the AWDL station's queue nor the own queue drains.

## Change (RAM switches, off by default)

- **Mode 7:** as mode 6 (link 1 follows this Mac's sequence, keeps the own queue, AWDL frames on link 1's queue), with no windows.
- **Mode 8:** link 1 stays on the automatic second channel (as mode 3), its queue, with no windows.

In both, the firmware decides when link 1's PHY gets air time. In 1.1.47 link 1 on PHY 1 without windows received about 30 frames a second while the AP kept 0% loss.

- **Helpers:**
  - `iwx_awdl_te_follows`: modes 4 to 7.
  - `iwx_awdl_te_keeps_own`: modes 5 to 7.
  - `iwx_awdl_te_phy2q`: modes 6 to 8.
  - `iwx_awdl_te_windows`: modes 1 to 6.
- **Accepted values:** modes 1 to 8, kinds 0 and 2.
- **Tool:** router only 20 s (AirDrop running), mode 7 30 s, mode 8 30 s, then off.

If link 1's queue still does not drain, this firmware does not transmit for a second MAC on another channel, and AirDrop on a router has to rely on the phone visiting this Mac's channel. That already works, at about 3 MB/s.
