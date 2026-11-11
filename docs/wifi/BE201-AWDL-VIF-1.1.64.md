# AirportItlwm 1.1.64: mode 6, AWDL frames leave where link 1 is

## 1.1.63 router test, 2026-11-08 19:29 (channel-20261108-192915.txt)

The user answered "sees Mac, not moving" throughout.

| Phase | Result |
|---|---|
| Mode 5, aggregation on | OwnSentPhy2 3, nothing done |
| Mode 5, aggregation off (TID 15) | OwnSentPhy2 1, nothing done |
| Mode 5, kind 2 (P2P_DEVICE_DISCOV) | Assert as with kind 1: 0x2000150D, last host cmd 0x004B0305 SESSION_PROTECTION. Only kind 0 is usable. |

Very little reached the own queue at all, and IPv6 neighbor discovery never completed in any test.

## Root cause

In context mode 6 (`iwx_tx`), every AWDL frame that is not on the own queue uses `sc->first_data_qid`, the AP station's queue on link 0:
- action frames (MIF/PSF sync);
- multicast data (neighbor solicitations);
- unicast data that falls back.

Wherever link 1 sits, these frames go out on the AP's channel (36), never on 149. The phone, on 149, never hears this Mac's sync or neighbor discovery there, so no AWDL data session can form. The family still sees the phone, because reception on 149 works.

## Change (RAM switch, off by default)

- **Mode 6 (`debug.be201_awdl_phy2=1`, `debug.be201_awdl_phy2_te=6`):** as mode 5. In addition, after the first successful move to the second channel, the phy2 task allocates a MGMT TID queue on the AWDL station (`IWX_AWDL_STA_ID`, link 1), `phy2_qid`. Its `iwx_tvqm_enable_txq` call is guarded by the NIC lock.
- **Which frames use it:**
  - While link 1 is on the second channel, `iwx_tx` sends AWDL frames (kinds 1 and 2, and A-MSDU) on `phy2_qid`. The own queue still wins for its peer.
  - The queue is bounded: at 8 queued (`IWX_AWDL_TX_MAX_QUEUED`) the frame is dropped (Phy2QDrop), so a queue the firmware never drains cannot fill and stop the AP's traffic.
- **Completions:** counted through `txd->awdl_phy2q`: Phy2QSent, Phy2QDone, Phy2QFail, Phy2QErr, Phy2Qid.
- **Teardown:** `iwx_awdl_ctx_remove` flushes and disables the queue before the AWDL station is removed. The resets clear `phy2_qid`. The watchdog ignores frames held there, as it does for the own queue.
- **Helpers:** `iwx_awdl_te_follows` (modes 4 to 6) and `iwx_awdl_te_keeps_own` (5 and 6).
- **Accepted values:** modes 1 to 6, kinds 0 and 2 only.
- **Tool:** router only 20 s, mode 5 (comparison) 20 s, mode 6 45 s, then off.
- **Tests:** test-awdl-ba covers the helpers, queue creation, routing, the bound, the own-queue precedence, teardown order, the watchdog and the resets. The test-beacon-peer-tx stubs get the new fields.
