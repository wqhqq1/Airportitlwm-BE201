# BE201 1.1.38: advertise rates, follow the cluster's AW numbers

Evidence: 1.1.37, armed 22:54, both-ends capture 23:06 (capture-*-20261103-230613).

- Peer stations admit group data without promiscuous: ProbeData 171, Ipkts 171. en1 fine, gateway all OK, unicast ACK 179, NoAck 0.
- The transfer the user saw at 23:09 went over USB (en5, C37 IPv6%en5), corrected by the user. Not AWDL.
- Phone capture: Mac QUIC 1262-byte UDP to port 53379 reached the phone's awdl interface at 23:08:54 and 55. The phone answered at once, 1262 and 596 bytes. Also 169 phone SYNs to 8770. Mac tcpdump and ProbeDataSelf saw none of it. So Mac to phone unicast works end to end, and the only break is phone's interface to Mac's driver. The capture's io field is 1 for everything, so direction comes from addresses.

## Finding

buildMasterIndicationTemplate adds buildEnhDataRateTlv from _htCapabilityLength and an element container (TLV 0x11, VHT) when the VHT query succeeds. They come from IO80211PeerManager::getHtCapabilityIE, ioctl 0x9a through the infrastructure protocol, which answers Unsupported here. So the Mac's frames carry no rates. Native firmware's own frames would. A phone with no rates for a peer may hold unicast for it. Not proven; the phone's chip cannot be read.

SYNC_INFO showed the phone's sequence against our window off by a constant 4326 with SyncErrors rising: the AW timer free runs. User asked about this too.

## Changes

- en1 getHT_CAPABILITY and getVHT_CAPABILITY answer, once armed only: 2 streams, LDPC, SGI, 40 and 80 MHz, MCS 0-9, A-MPDU minimum. Normal boots still Unsupported.
- AW start events take number and phase from the heard cluster (iwx_awdl_sync_next), kept to 64-100 ms per slot, free running when nothing heard for 2 s. ItlwmAwdlAwAligned.
- First nearby MIF saved as ItlwmAwdlPeerMifSample, to compare TLVs directly.

## Read next

Template now longer, with the rate TLV and 0x11; compare with ItlwmAwdlPeerMifSample. SYNC_INFO SyncErrors, SameTree. ProbeDataSelf, DataRx with unicast. Phone capture again if needed: 开始抓包.command works in this kit. Family reaction to the number jump is unverified.

## Verification

All suites and the 58-unit build. Not hardware tested.
