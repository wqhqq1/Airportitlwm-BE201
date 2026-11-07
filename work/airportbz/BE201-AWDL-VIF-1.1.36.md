# BE201 1.1.36: PSFs where only MIFs are heard, and a promiscuous-after-association test

Evidence: 1.1.35, boot B89101A3. CtxStage 6, no fault, en1 gateway 40/40, Handoff normal per user, unicast ACK 10, NoAck 0. ProbeData 0: the phone's multicast mDNS did not arrive. Phone logged no presence or discovery of this Mac and sent no SYNs, so unicast RX was not tested.

## Why the phone may not accept the Mac

Peer logic in IO80211AWDLPeer (setPeerRoutable, waitForPostingPeer, shouldStopAFProcessing) rests on RSSI, band and frame counts, not on anything we found wrong in the TLVs. Mac accepted the phone from MIFs alone, so PSFs may not be required. But what the Mac sends differs by place:

| Run | Heard PSF | Heard MIF | Senders | Mac sent |
| 1.1.31, morning | 2287 | 1764 | 30 | MIF and PSF, 1279 |
| 1.1.35, evening | 0 | 415 | 2 | MIF only, 260 |

One frame per heard frame, MIF checked first at 224 ms. A lone phone's MIFs come about 385 ms apart, so the MIF is always due and no PSF is ever sent. That is the one fix-able difference found. Not proven to be the cause.

## Changes

- A heard frame can send up to one MIF and one PSF, each on its own interval. ItlwmAwdlTxPsfSent counts PSFs.
- RAM sysctl debug.be201_awdl_vif_promisc, default 0, set by vif_test.py --promisc. With it, the association command adds PROMISC to MAC 1. 1.1.33 set it on an unassociated MAC; Linux monitor_on sets it on associated stations. Other networks' infrastructure data drops before net80211, as on 1.1.33.

Two runs, one boot each, no EFI write between them: normal, then --promisc.

## Read next

Normal: phone presence for this address, ItlwmAwdlTxPsfSent, TxUnicastAck, ProbeDataSelf if the phone sends.
Promiscuous: gateway_ok, phone hears Mac mDNS, unicast ACK, ProbeData, ProbeDataSelf, DataRx. If en1 fails again, promiscuous is finished; next is a PEER station per heard address.

## Verification

All suites and the 58-unit build. Not hardware tested.
