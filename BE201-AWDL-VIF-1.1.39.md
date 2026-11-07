# BE201 1.1.39: faster unicast

Evidence: 1.1.38, boot BF5FF678, armed 23:24. AWDL AIRDROP WORKS BOTH WAYS. awdl0 Ipkts 22184, 10 MB; Opkts 34788, 38.7 MB. ProbeDataSelf 16000+, unicast ACK 25000+, NoAck 56, DataRxRetry about 2%, so hardware ACKs MAC 1. sharingd Send StateMachine UPLOAD END 23:26:43, Receive PostAccept END 23:28:44, IPv6%awdl0 socket flows, rapportd TCP on awdl0. No fault, no panic. Mac MIF now has TLVs 7 (22) and 17 (14); phone's has 7 (20), 17 (14) and 33 (14).
User: same Wi-Fi discovers and transfers both ways; different Wi-Fi discovers under another name and cannot transfer; 0.5 to 1 MB/s.
Which of the rate TLVs or AW alignment did it is not separated. Rate TLVs are the likely one.

Different Wi-Fi: MAC 1 shares the AP PHY context, so the radio stays on the AP channel. Manager schedule at infra 36 was [149 149 149 149 149 149 36 36 6 ...] and the radio never left 36. A transfer works if the phone is reachable there. Hopping is not built. Discovery in that case was not traced.

Speed: 2.7 MB per 5 s Mac to phone, 0.55 MB/s, is the 6 Mbps legacy command rate.

## Changes

- Unicast AWDL data uses HT at 20 MHz: start MCS 7 one stream (65 Mbps), two streams after 64 clean frames if two antennas, down through MCS 4, 2, legacy after 2 straight failures. Up threshold doubles after each drop, to 4096. Group and management frames stay at the lowest rate. Counters DataRateMcsStep (0 = two streams, 1 start), DataRateUps, DataRateDowns.

## Unknowns

Whether the phone hears 20 MHz HT at every moment, and two streams. Firmware retries at the fixed rate. No A-MPDU. Phone to Mac is the phone's choice and unchanged.

## Verification

All suites and the 58-unit build. Not hardware tested.
