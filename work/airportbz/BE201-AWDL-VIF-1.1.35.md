# BE201 1.1.35: associate the AWDL context for data receive

Evidence: 1.1.34, boot 32A5C2DD, armed 21:13:08, `outputs/BE201AWDL独立网络-1.1.34`. No panic. Firmware error 0x200014FC, data1 149, command 0x590309: LINK_CONFIG activating link 1 as an IBSS. FailedStage 3, error 35, Tripped 1, DataTx 0, DataTxDropped 59. So AWDL was off for the whole run; phone list, Mac send, Handoff and Watch results say nothing about AWDL.
en1 stayed healthy through the fault: gateway ping OK in all 41 rows, Tx rate 1134259 to 1200980 kbps, en1 counters rising. A refused context is a safe failure. This also confirms the 1.1.33 en1 loss came from promiscuous.
1.1.12 had also failed with IBSS, but its zero-field link command confused the result (0x2010303E, with P2P client too). This run has correct activation and a different error, naming the channel: this firmware refuses IBSS here. Likely regulatory on 149, not proven.

## Changes

- Removed the IBSS path. MAC 1 is a P2P client again.
- After activation the native mode adds station 3 at the AWDL BSSID, then marks MAC 1 associated, the same firmware commands as mode 4 without its queue. Frames still go on the AP queue. Removal undoes them, no queue teardown.
- Reasoning: AWDL data has no DS bits and A3 the BSSID, as TDLS does. A client filters to its own BSSID, and unassociated took no data on 1.1.31. Whether unknown A2 passes is the question.
- Gates on stage ACTIVE now accept later stages.

## History

Mode 4 ran on 1.1.16 with no fault, 288 action frames, hotspot, Wi-Fi off/on and Handoff normal per user. ProbeData was 0 but no phone was using AWDL then, so that says nothing on data. Its own queue held frames; not used here. TX on the AP queue from an associated MAC 1 is new.

## Read next

ProbeDataSelf and ProbeData, TxUnicastAck, gateway_ok, CtxStage 6, FwErrors. If multicast arrives and unicast does not, next is a PEER station per heard AWDL address.

## Verification

All suites and the 58-unit build. Not hardware tested.
