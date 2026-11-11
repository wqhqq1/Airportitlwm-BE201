# AirportItlwm 1.1.42: hold data while the peer is away, second channel test

1.1.41 results: on the phone's hotspot (149) phone to Mac peaked at 39.25 MB/s with block ack; Mac to phone 4.3 MB/s, single MPDU, no drops. On router channel 36, Mac to phone 0.25 MB/s or less at the lowest rate. The phone's schedule during transfer is 149 for 69% of slots, 36 for 25%, 6 for 6%, each slot about 64 TU. A peer station's own queue was held (3 sent, 0 finished).

## Changes, all default off and RAM only

- `debug.be201_awdl_tx_hold`: unicast data to the schedule's reference waits while that schedule has it on another channel. Nothing holds if the schedule is stale, shorter than 16 slots, for another peer, or never visits this channel. The AW timer, aligned to the heard boundaries, wakes the queue.
- `debug.be201_awdl_phy2`: link 1 inactive, sc_phyctxt[1] to this 5 GHz channel, link 1 active on it. 0 returns to the AP's PHY context. A failure latches AWDL off for the boot.
- `debug.be201_awdl_phy2_te`: with the above, session protection on link 1, 100 TU once a second. Notifications for link 1 now stay out of AP state in mode 6 too.

## Always on

- Unicast failures while the schedule says the peer is away no longer lower the rate. Results are counted apart: TxOkHere, TxFailHere, TxOkAway, TxFailAway. If failures do not concentrate in Away, the slot arithmetic is wrong and the hold must not be trusted.

## Not verified

The mapping from AW number to slot is read from family behaviour and has not been checked on air; the counters above check it. Firmware has never run link 1 on a second PHY with this context type. AWDL frames still leave on the AP queue, so the second channel test measures receive and scheduling, not transfer. No A-MSDU yet; it is the next candidate for Mac to phone.
