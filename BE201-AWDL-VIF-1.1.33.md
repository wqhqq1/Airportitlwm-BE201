# BE201 1.1.33: prepare received packets

Evidence: 1.1.32, boot 0A0CEED2, armed 20:20:31, panic 20:24:41 when the user opened AirDrop. Page fault CR2 0x58, IOSkywalkPacketBuffer::getMemorySegment from getDataVirtualAddress from inputDataFrame, RDI 0.

- Firmware now delivers AWDL data: the promiscuous filter works. awdl0 options=400: offload off works, ItlwmAwdlOffloadResult 0.
- Bug: allocatePacket leaves the packet's buffer slot empty; prepareWithQueue fills it from the packet's buflet. getDataVirtualAddress does not check. setDataLength would also fail, as [packet+0x64] is 0.

## Native, read from 24G824

- refillRxRing: allocatePackets(.., nosleep), then prepareWithQueue(this RX submission queue, 2, 0).
- completeWithQueue calls the source queue's packetCompletion. The base implementation panics ("default packetCompletion()"), and IOSkywalkRxCompletionQueue does not override it, so the completion queue must not be the source.
- prepareWithQueue with a null queue leaves source null and every completion callback skipped. deallocatePacket completes a prepared packet, skipping a null source.
- enqueuePacketsForNetworking then completes direction 2, which finalizes buffer and packet, and hands the chain to kern_netif_queue_rx_enqueue with flush.

## Changes

- inputDataFrame: be201PacketPrepare(packet, nullptr, 2, 0) after allocation; prepare and setDataLength failures deallocate and count.
- The test mock now models this: pool packets are unprepared, base, set length and enqueue assert prepared. The old code fails it.
- vif_test keeps counters from the PCI node and a log stream on disk for 15 minutes after the test, fsynced every 5 s; the 1.1.32 panic lost the unified log after 20:21:18 and no probe counters were saved.

## Open

1.1.32 had RxSubmitted 0 and RxInvalid 0 in the first minute, 1.1.31 had 480 and 885. Nearby BLE devices in that minute were 1 against 86, so a quiet place is the likely reason, but firmware dropping management frames under promiscuous is not ruled out. The watch file's ProbeForeignMgmt and ProbeMIF settle it.
First real netif receive: packet metadata beyond length is unset.

## Verification

All suites and the 58-unit build. Not hardware tested.
