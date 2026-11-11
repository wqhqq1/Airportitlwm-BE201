# AirportItlwm 1.1.41: answer block ack requests, wait instead of dropping

Evidence from 1.1.40 (boot 62A7A0FB, phone hotspot, channel 149): both directions held about 3000 frames a second, 4.04 and 3.81 MB/s, at VHT 80 2SS MCS 9 and HE 80 2SS MCS 11. Rate no longer limits. DataRxAmpdu was 0. `ItlwmAwdlNativeRxLastBad` read `03 00 75 03 10 90 e2 80`: an ADDBA request, TID 0, window 64, A-MSDU allowed, about one a second. Nothing answered it, so the phone never aggregated. While receiving, 14% of TCP ACKs were dropped by the full queue (2516 of 17569).

## Changes

- ADDBA requests sent to this interface in the AWDL BSS get a firmware BAID (RX_BAID_ALLOCATION_CONFIG_CMD with the peer station's mask) and a response: immediate policy, peer's TID and timeout, window at most 64, no A-MSDU since delivery takes one packet per MPDU. A sender with no station yet gets no answer; it repeats. Firmware refusal answers status 37.
- DELBA from the initiator removes the BAID. Sessions and the test queue go before stations in ctx_remove.
- Delivery has no reorder step: frames marked OLD_SN are dropped, others go up in arrival order. `RxOldSn` and TCP behaviour decide whether a reorder buffer is needed.
- Transmit keeps packets when the queue is full. legacyDequeue on 24G824 advances the ring by the count returned, so a partial return is safe. requestDequeue option bit 0 only signals, so a completion may call it. The AW timer repeats the wake in case no completion arrives.
- A dead context returns NotReady and drops, so nothing waits forever.
- No registry write per transmit call.
- RAM test `debug.be201_awdl_own_queue`, off at boot: data to the peer that holds block ack goes on that peer station's own queue, TID 15. Two looks at the counters with frames queued and none finished latch it off, back to the AP queue. This queue is the prerequisite for sending aggregates and for a channel other than the AP's. Earlier own queues (modes 3-5) were held, before association and peer stations existed.

## Not verified

Firmware accepting a BAID for these stations. Whether the phone aggregates once answered. Speed. Mac to phone stays single MPDU in this version; expect modest gain there from losing the drops. Different Wi-Fi is unchanged. Handoff is observed only.
