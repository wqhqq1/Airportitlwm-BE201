# BE201 1.1.31: first AWDL data path

Evidence: boot 1EB743B1, `outputs/BE201AWDL发现帧发射-1.1.30/`. Phone `Posted peer presence for xx:xx:xx:xx:xx:xx on awdl0` at 08:06:43, this boot's address. Live test: Mac advertises and browses _airdrop, MI grew to 289 bytes with service TLVs, wifip2pd reports discovery results and logical datapaths for peers, TX 3974/3974. sharingd: 13 connections `cancelled error Network is down`, because awdl0 is not RUNNING. Phone's list did not show the Mac (user).

## Native, read from 24G824

- enableDatapath (concrete) enables two completion queues and the TX submission queue, calls requestDequeue(0, 0); no RX submission enable. Then reportLinkStatus(3, 0x80) in setInterfaceEnable.
- legacyDequeue calls the TX action with (owner, queue, packets, count, ref) and advances by the return value; 0 means stall.
- getDataVirtualAddress is the buffer base without the data offset.
- formatOutputPacket writes aa aa 03 00 17 f2 08 00, then 03 04. Native goes through IO80211NetworkPacket and flow queues. This build does not: plain Skywalk queues, IOSkywalkPacketBufferPool, peers not tracked by the family's input path.

## Changes

RAM sysctl `debug.be201_awdl_vif_data`, default 0.
- After link up and monitor request: completion and TX queues enabled, requestDequeue, reportLinkStatus(3, 0x80), IFF_RUNNING, setRunningState(true) succeeds.
- TX: action copies each Ethernet packet into an AWDL data frame: 802.11 data, no DS, A1 destination, A2 this address, A3 AWDL BSSID, LLC, 03 04, sequence, pad, Ethertype. Sent on the AP management queue like the action frames, broadcast or unicast, unencrypted (ENCRYPT_DIS, as the path already does for unprotected frames), lowest rate. Every packet is completed whether sent or dropped; drops above 32 queued. ItlwmAwdlDataTx, DataTxDropped.
- RX: data frames from the monitor with A3 the AWDL BSSID, A1 this address or multicast, the expected LLC, unprotected, become Ethernet in a packet from the pool, enqueued on RX completion. ItlwmAwdlDataRx, DataRxDropped.
- awdlKind counts AWDL data too, so ACK counters and the watchdog's AWDL exception cover it. iwx_tx_fill_cmd uses the command rate for AWDL BSSID frames.
- PSFs no longer dropped by the driver's TLV walk.

## Expected

awdl0 flags include RUNNING. TX counts rise from mDNS and IPv6 ND. If the phone sends, ProbeData and DataRx rise. Then TCP on 8770 may start. AirDrop may still fail.

## Unknowns

Firmware delivery of unicast data to MAC 1 without a station; only multicast action frames are proven in. Unicast data over the AP queue: only unicast action frames proven. No AW scheduling: frames go at once, so peers off 149 miss them. Family peer state not updated by this path; it may stop routes or consider traffic absent. Packet metadata for the netif RX path unverified (link header offset default). Anything may panic: this is the first traffic through these queues. Normal boot unaffected, manual arm only, and `debug.be201_awdl_vif_data=0` before arming gives 1.1.30 behaviour.

## Verification

All suites and the 58-unit build. Not hardware tested.
