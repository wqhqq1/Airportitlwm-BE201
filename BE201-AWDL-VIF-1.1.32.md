# BE201 1.1.32: peer data into the stack

Evidence: boot AA116410, `outputs/BE201AWDL数据通路-1.1.31/`, phone archive iPhone-20261103-085702. No panic.

- awdl0 RUNNING, options=6460. sharingd `Network is down` 13 to 0. DataTx 148, dropped 0. TxUnicastAck 78, NoAck 0, retries 0.
- Mac to phone works: Mac mDNSResponder sent a 245-byte response at 08:52:55.308; phone received a 245-byte response on awdl0 at 08:52:55.498.
- Phone wifip2pd at 08:52:55.276: `Received a new discovery result xx:xx:xx:xx:xx:xx [196a555281dc._airdrop._tcp.local] at -33 dBm`, resolve done, `datapath established`. Phone sharingd sent six TCP SYNs to port 8770 and hit DISCOVER timeout.
- Mac: ProbeData 0, ProbeDropped == ForeignMgmt, no data frame of any BSS reached the driver. So firmware filters data on MAC 1. Mac DISCOVER to the phone also times out, needing the same replies.

## Changes

- MAC 1 (native only) gets IWX_MAC_CFG_FILTER_PROMISC. Linux sets this on station contexts for monitor_on. The AP station MAC is unchanged.
- With promisc, infrastructure data whose BSSID is not this AP drops before net80211. ds 1 compares A1, ds 2 and 3 compare A2. New ProbeForeignData shows the filter admits data; ProbeDataSelf counts AWDL data to this address.
- iwx_awdl_rx_wanted forwards only management frames and no-DS AWDL data for this address or a group to the interface.
- awdl0 advertised TSO4, TSO6, PARTIAL_CSUM, ZEROINVERT_CSUM; en1 only CHANNEL_IO. xnu leaves TCP checksums to the driver with PARTIAL_CSUM, so Mac SYNs were likely invalid. enableData calls ifnet_set_offload(0) and records ItlwmAwdlOffloadResult. iwx_awdl_fix_l4_csum also rewrites IPv6 TCP and UDP checksums on send; ItlwmAwdlTxCsumFixed counts wrong ones. Over 1514 bytes drops into ItlwmAwdlDataTxOversize.
- allocatePacket option bit 0 is nosleep (kern_pbufpool_alloc_nosleep); this was 0 and could sleep holding the Wi-Fi work loop.
- enqueuePackets guards read: returns an error rather than faulting if not enabled, [+0x78] null takes the kpipe path. Result in ItlwmAwdlDataRxEnqueueResult.
- Diagnostics: DataRxBad, DataRxLastBad (first 16, 48 bytes), DataRxRetry.

## Expected

options=400 on awdl0. ProbeForeignData rises. ProbeDataSelf and DataRx rise while the phone browses. Then phone logs a completed TCP connect and TLS on 8770.

## Unknowns

Whether firmware delivers data on a P2P client context with no station even when promiscuous. Whether hardware ACKs MAC 1; a high DataRxRetry share means no. RX packet metadata: length and offset only, first real use. Promiscuous load. Unicast ACK with zero retries may not be a real ACK. No TLS verification yet: firmware rate and AW scheduling may break a long transfer.

## Verification

All suites and the 58-unit build. Not hardware tested.
