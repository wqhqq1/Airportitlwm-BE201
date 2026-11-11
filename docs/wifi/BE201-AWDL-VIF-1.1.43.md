# AirportItlwm 1.1.43: A-MSDU to the phone, second channel retry

1.1.42 results on router channel 36: schedule arithmetic confirmed (FailAway 679, FailHere 2). Mac to phone 0.82 MB/s with the rate kept at step 0. Holding data changed nothing. The second PHY asserted firmware (0x2010330F, data1 1) at MODIFY link 1, phy 1, mask 3, active 1; en1 recovered in about 22 s.

## Changes, default off and RAM only

- `debug.be201_awdl_amsdu`: a run of packets in one transmit call, same unicast destination, at most 5 and 7900 bytes, goes as one QoS data MPDU with A-MSDU present, TID 0, normal ack, on the AP's management queue. Used only at a VHT step and for a peer holding a block ack session with this Mac. `IWX_TX_CMD_OFFLD_AMSDU` set. The QoS branch in iwx_tx skips these so they never reach the AP's TID queues. Sixteen failures with no success give up for the boot. Single packets stay as before.
- Second PHY sequence now: mask ACTIVE inactive; mask 0 no PHY; PHY update; mask 0 new PHY; mask ACTIVE|RATES active. The last two match how this link first activates.
- channel_test stops after a fault instead of running meaningless phases, and finds the peer before the switch.

The hold switch stays, unused by the tools.

## Not verified

Whether the firmware accepts QoS frames on this queue with these flags, whether the phone's AWDL receive takes A-MSDU, and whether the phone counts ACKed subframes as delivered: a stall with NoAck 0 would mean ACKed and dropped, which only the speed shows. Whether the firmware allows this link on a second PHY at all. 11454 is one phone's capability, hard coded like the rate ladder; no peer limits are read yet.
