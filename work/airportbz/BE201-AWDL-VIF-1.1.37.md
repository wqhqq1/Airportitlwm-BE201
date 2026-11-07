# BE201 1.1.37: a firmware station for each nearby AWDL sender

Evidence: 1.1.36, three runs, 22:04, 22:16 (normal) and 22:28 (promiscuous), archives iPhone-20261103-222059 and -223130.

- The PSF fix worked. Phone accepted the Mac every time in the quiet place: `22:05:43 Posted peer presence for xx:xx:xx:xx:xx:xx`, `22:06:35 Received a new discovery result ... _airdrop ... at -38 dBm`, datapath established; same for xx:xx:xx:xx:xx:xx and xx:xx:xx:xx:xx:xx. TxPsfSent 740 by 22:11.
- Phone then opened TCP to port 8770: repeated connections with SYNs: 6, 79 SYN retransmits logged in the first archive. ProbeDataSelf 0 in all runs. Mac unicast ACK 7, NoAck 0, gateway OK until reboot.
- Promiscuous after association: ProbeData 45 and DataRx 45 (group), ProbeDataSelf 0 even with the phone sending SYNs. Unicast ACK 0, NoAck 23, status 0x83, Tx rate 68055, user lost network. Same as 1.1.33. Promiscuous is finished, removed.

Whether the phone's unicast gets on air cannot be read from its logs (no AWDL kernel lines). Group data arrives under promiscuous and unicast to this address does not, which points to the address-matched path needing a known transmitter.

## Changes

- Up to 4 firmware stations, ids 4 to 7, on link 1, type PEER, for AWDL action frame senders at -65 dBm or better. Staged on receive, sent from a task, none added once one fails. Removed first on context removal. Counters ItlwmAwdlPeerStations, ItlwmAwdlPeerStationErrors, ItlwmAwdlPeerStationAddrs.
- Promiscuous sysctl, HAL call, filter flag and its other-network drop removed.
- vif_test watch: a failed sample is recorded instead of ending the watch; the 22:28 run wrote 0 rows.

## Unknowns

Firmware may refuse a PEER station beside the AP-like one, safe failure seen on 1.1.34. Stations carry no rates or keys. If the frame is delivered but protected, DataRxBad and DataRxLastBad show it. If ProbeDataSelf stays 0 with a station present, the next question is whether the phone transmits at all, which needs the AW schedule it computes from our sync TLV: AW numbering is not aligned (SYNC_INFO SyncErrors, SameTree=N).

## Verification

All suites and the 58-unit build. Not hardware tested.
