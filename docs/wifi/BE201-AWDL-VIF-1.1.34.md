# BE201 1.1.34: IBSS context in place of promiscuous

Evidence: 1.1.33, boot before 7AA09E78, armed at 20:43:15, kits `outputs/BE201AWDL收包修正-1.1.33`. No panic. The prepare fix works.

- Phone to Mac works: phone sent a 118-byte mDNS query at 20:45:03.613, Mac mDNSResponder received 118 bytes on awdl0 at 20:45:04.035. DataRx 64, netstat Ipkts 88, DataRxBad none.
- Unicast to this address never arrived: ProbeDataSelf 0. Phone logged no presence and no discovery of xx:xx:xx:xx:xx:xx.
- Mac to phone broke: phone received none of the Mac's 206, 245, 197, 349, 208-byte responses (1.1.31 received 245). Unicast ACK 0, NoAck 65, status 0x83 long retry limit, 896 retries (1.1.31: 78 ACK, no retries).
- en1 broke at the same moment: last healthy TCP closed 20:42:50, then only SYN_SENT closes; en1 mDNS receive 257 per minute to about 4. Tx rate 1200980 NSS 2 to 36029 NSS 1. AP queue backed up from 20:49, en1 link down 20:50:11 and CtxAdds 4.

The only firmware-facing change from 1.1.31 is promiscuous on MAC 1. That matches all of the above, though firmware internals are not visible. Earlier mode 1 on the AP MAC also coincided with Handoff loss, so the AP MAC is not an alternative.

## Changes

- MAC 1 for the native interface: type FW_MAC_TYPE_IBSS, group and management filter, no promiscuous. Link carries ibss_bssid_addr = AWDL BSSID on every command before activation. This is what Linux does for an ad hoc MAC; AWDL data is no-DS with A3 the BSSID, which is IBSS framing.
- Removed the promiscuous infrastructure data drop.
- vif_test watch adds en1 byte counts, a gateway ping, and AP Tx rate, so en1 health is recorded every 5 s.

## Unknowns

Whether this firmware allows an IBSS MAC beside a station. Linux does not offer that combination; it may reject or assert. An assert needs a reboot; arming is once per boot and normal boots never reach this. Whether frames from unknown peers are delivered and ACKed with no station. TX still on the AP queue, A2 this MAC.

## Verification

All suites and the 58-unit build. Not hardware tested.
