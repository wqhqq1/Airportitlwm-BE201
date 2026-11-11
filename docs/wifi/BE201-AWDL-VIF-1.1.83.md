# AirportItlwm 1.1.83: an open network counts as an open AP port

## 1.1.82 result, boot 2026-11-10 21:08

- **DMA pool fixed:**
  - After two network changes and one big AirDrop: MldDataQueues 255, OwnErr 0, ItlwmDmaFailures 0, RetiredKiB 0.
  - UsedKiB was 46064 and HighKiB 47244, of the 64 MiB pool. That is the steady footprint (firmware images, paging, RX and TX rings), not growth.
- **Network change at 21:14:50:** from a channel-149 network (beacon 100) to the channel-60 router.
  - The router is an open network: Security None, WclAssocLowerAuth 1, WclJoinRSN empty.
  - The change took 0.22 s, with no handshake.
- **ROC test at 21:15:**
  - AirDrop 0.00 MB/s in every phase. The user answered "sees Mac, not moving".
  - In both ROC phases RocBlocked was 32 (bit 5: AP port), and RocSetups 0.
  - Router ping was fine.

## Cause

- **Where the flag is set:** `ni_port_valid` is set only by the key path (`AirportItlwmSkywalkInterface` after the GTK, `ieee80211_pae_input`) and by HostAP joins. On an open network it stays 0.
- **Places that already allow for this:** the MLD authorized step (`ni_port_valid || !RSNON`) and the authorized-update check.
- **Places that tested the bare flag:**
  - `iwx_awdl_roc_blocked` (bit 5);
  - `iwx_awdl_data_gate`: AWDL data;
  - the AWDL sync-frame sender (`iwx_awdl_tx_maybe` path);
  - `iwx_awdl_native_task`: the AWDL context bind;
  - two AP TX choices: high priority at the lowest rate, and the management queue for "pre-auth" data.
- **Result:** on an open AP these held back the ROC and possibly AWDL data and sync frames.
- **Unconfirmed:** ItlwmTxPreAuthMgmtQ never appeared in this boot, so the AP TX path may have seen the port as valid. 1.1.83 publishes both flags to settle this.

## Change

- **`iwx_ap_port_open(ic, ni)`:** `ni && (ni->ni_port_valid || !(ic->ic_flags & IEEE80211_F_RSNON))`.
  - Used in all six places above.
  - On RSN networks nothing changes: the port still waits for the handshake.
- **New properties, once a second with the history sample:**
  - ItlwmApPortValid: the raw flag;
  - ItlwmApRsnOn.
- **ROC tool:** records both flags each phase.

## Tests

- **test-awdl-ba:** the helper; the data gate, the ROC mask, the native task and the AP TX choices use it; both properties are published.
- **test-awdl-native:** the mock takes the real helper and an RSN flag.
  - Case 2 (RSN, port not valid) still blocks.
  - New case 9 (open network, port flag 0) binds.
- **test-awdl-tx:** the sync sender uses the helper.

All 24 suites pass.

## Note for the router test

- **The router's channel:** 60 is a DFS channel.
- **Baseline expectation:** when the Mac stays on 60, the phone has to come to 60 for AWDL. The 1.1.64 router test (channel 36) did this at about 3 MB/s. On a DFS channel it may never do so, so the baseline phase can stay at 0.
- **The ROC phases are what matter here:** whether the firmware grants time on 149, and whether frames are heard there.
