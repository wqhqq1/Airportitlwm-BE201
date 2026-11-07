# BE201 1.1.40: VHT for unicast, and read what the phone sends

1.1.39 was installed but the user asked for VHT before reporting a test of it. So HT adaptation is untested on air here too.

Phone's MIF (ItlwmAwdlPeerMifSample, 1.1.38): TLV 7 HT MCS 0-15; TLV 17 VHT cap info 0x13b1f076, rx and tx map 0xfffa, two streams MCS 0-9; TLV 33 not decoded. Peak phone to Mac 3.92 MB/s, 2620 packets/s; peak Mac to phone 0.54 MB/s.

## Changes

- Ladder for unicast AWDL data: VHT 80 MHz 2SS MCS 9 (866), VHT 80 MHz 2SS MCS 7 (585), VHT 20 MHz 2SS MCS 8 (173), HT MCS 7 (65, start), HT MCS 4, HT MCS 2, legacy. Up one after 64 clean frames, threshold doubling after each drop to 4096; down one after 2 straight failures. 80 MHz needs the AP link at 80 or wider, as the link shares its PHY context, else VHT 20. Two streams need two antennas.
- DataRateMcsStep: 0 is the top step, 3 the start, 6 legacy.
- ItlwmAwdlDataRxRateNFlags, DataRxRatePeak, DataRxAmpdu: for AWDL data to this address, from the receive descriptor.

## Unknowns

BCC, no LDPC, no A-MPDU. Whether the phone receives 80 MHz at all times: the manager's schedule flags were 0x12 (20 MHz) idle and 0x410 (80 MHz) at another time. A bad rate shows as Downs and NoAck, each failed frame costing up to 15 retries. Firmware may reject a fixed VHT rate on the AP queue; fault latch stops AWDL only.

## Verification

All suites and the 58-unit build. Not hardware tested.
