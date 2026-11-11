# AirportItlwm 1.1.52: own queue follows the destination; firmware aggregation for Mac to phone

Includes 1.1.51 (llw0 feature flags as native), which was never written to the EFI. User priority: AirDrop, including the slow Mac to phone direction.

## Why Mac to phone is slow and the second channel did not carry AirDrop

All AWDL data to peers leaves on the AP station's management queue (TID 8, first_data_qid) as plain data with a fixed rate from iwx_awdl_data_rate. That queue sends only on the AP's channel and never aggregates, so Mac to phone stays near 4.3 MB/s on 149 while phone to Mac reaches 39 MB/s with block ack. The own queue (a TVQM queue on the peer station) could leave on link 1's channel, but it followed the peer that set up block ack, not the AirDrop destination: OwnSent stayed 0 in the 1.1.50 channel test.

In this driver the MLD firmware runs TX block ack itself (comment in iwx_tx: Linux TX_AMPDU_SETUP_IN_HW with TLC offload) and only needs a TID queue, QoS data and rate control for the station. The AP station gets that from iwx_mld_sta_config_cmd and iwx_rs_init. Peer stations had only addresses and an assoc id. iwx_rx_tx_ba_notif dropped every compressed BA notification not for IWX_STATION_ID, so aggregates for a peer would never be reclaimed.

## Change, all RAM switches, off by default

- debug.be201_awdl_own_queue: the own queue follows the last unicast data destination (iwx_awdl_note_dest in sendAwdlData), moving when it changes (release, then reallocate; OwnRetargets). After allocating, STA_DISABLE_TX_CMD with disable 0 when the firmware knows the command (OwnTxEnErr, 0xffff when unknown), in case the earlier held queues were a disabled station.
- debug.be201_awdl_txagg: own queue on TID 0. Before it, STA_CONFIG for the peer with MIMO, A-MPDU exponent 7 (capped at 4M) and 4 us spacing, and TLC_MNG_CONFIG v4 VHT MCS 0-9 1-2 SS, width of the link (20 when on the second channel). Data to that peer becomes QoS data TID 0 (iwx_awdl_ether_to_qos), sequence from the ring position like the AP's aggregation queues, no fixed rate. BA notifications for that station are reclaimed and counted (OwnAggOk, OwnAggFail, OwnBaNotifs). Phone caps are assumed, not parsed.
- iwx_tx: QoS frames on the own queue keep its qid instead of being moved to the AP's TID queue.
- The second channel teardown now uses the shared release (iwx_awdl_own_release).

Not proven: that the firmware sends ADDBA to the phone by itself for a peer station, that the phone accepts it, that the held-queue behaviour of 1.1.41 is gone. Failure modes seen before were firmware asserts with a 10-20 s Wi-Fi gap and AWDL off for the boot, no panic.

## Test

开始隔空投送实验.command: send a large file Mac to phone, then 20 s phases: baseline, own queue, own queue with aggregation, and on a router channel also the second channel 149 with schedule windows. Speed from awdl0 output bytes, gateway RTT, own queue counters. All switches off at the end in a safe order.
