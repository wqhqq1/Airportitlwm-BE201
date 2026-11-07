# AirportItlwm 1.1.53: why the peer's own queue holds frames

## 1.1.52 results, 2026-11-07 22:54, phone hotspot 149

AirDrop Mac to phone 4.60 MB/s baseline, 4.51 with the own queue, 4.31 with aggregation on: no change, user says about as before. The own queue did follow the destination (station 5, TID 15) and took 32 frames, then no completion at all: OwnOk 0, OwnFail 0, OwnHeld 1, so the data went back to the AP queue. STA_DISABLE_TX is unknown to this firmware (OwnTxEnErr 65535). Held stayed set, so the aggregation phase never built a TID 0 queue (OwnTid 15, OwnAgg 0): aggregation is untested. No firmware error.

## Candidates

Link 1 has only ever been sent ACTIVE and RATES_INFO in its LINK_CONFIG modify mask. iwx_awdl_ctx_link_cmd fills EDCA (cw, aifsn, txop, and fifos_mask, the TX FIFO for each AC) and bi/dtim every time, but the firmware applies only masked fields, so link 1 likely has no AC to FIFO mapping and no beacon timing. The AP link has both. Queues of stations on link 1 would then have nothing to drain into, which fits "only own queues hold, the AP queue sends A2 = MAC 1 fine". Second candidate: MAC 1 (P2P client, is_assoc, no beacons ever) never got MAC_PM_POWER_TABLE; a client in power save could hold frames for a wake that never comes.

## Change, RAM switches, off by default

- debug.be201_awdl_own_fix bit 1: MAC_PM_POWER_TABLE for MAC 1 with flags 0 (no power save, as Linux when ps is off), keep alive 25 s.
- bit 2: LINK_CONFIG MODIFY for link 1 with QOS_PARAMS | BEACON_TIMING (the AP's EDCA and bi/dtim).
- Changing aggregation or fixes now clears OwnHeld and rebuilds the queue (own_redo), so each test phase gets a fresh queue.
- Counters OwnFixDone, OwnFixErr.
- 开始隔空投送实验.command phases: baseline, own queue, plus fix 1, plus fix 1+2, plus aggregation, and on a router the second channel.
