# AirportItlwm 1.1.86: ROC mode 4, AWDL frames wait on the AUX queue

## 1.1.85 result, boot 2026-11-11 15:50

- **Router:** channel 157, the open network (ApPortValid 0, RsnOn 0).
- **Mode changes now rebuild:** RocSetups 4, Teardowns 4, and modes 2 and 3 ran.
- **Activity 2 (P2P_TXRX) beat activity 0:**

  | | Started | Failed |
  |---|---|---|
  | Activity 0, mode 1 | 45 | 26 |
  | Activity 2, mode 1 | 62 of 62 | 0 |
  | Activity 2, mode 2 | 69 of 69 | |
  | Activity 2, mode 3 | 93 | |

  Frames sent on the AUX queue during ROCs: RocTxSent 7, RocTxOk 7.
- **Discovery ROCs:** 139 of 120 TU on 149.
- **Nothing AWDL heard during the ROCs:** RocRxAwdlAny 0, RocRxDuring 0.
  - The firmware handed up 3729 frames while an ROC was active, only 31 of them on 149.
  - No AWDL peer, no awdl0 neighbour. AirDrop 0 MB/s. The phone saw the Mac.
- **Earlier in this boot, before the join:** solo AWDL had the link on a 149 PHY, and RxPhy2 counted 301 AWDL frames.
- **Router ping:** 33 to 100 ms average, maximum 606 ms. The 43 ms in the ROC-off phase came before any ROC.

## Reading

- **The radio does reach 149:** ROCs start and end, and frames sent there complete.
- **But no AWDL frame is passed up:**
  - The AUX ROC filters receive on `node_addr`.
  - The AWDL MAC, the one that accepts the AWDL BSSID and group frames, is on link 1 on the AP's PHY.
  - The phone's PSF and MIF frames, broadcast with the AWDL BSSID, match no context on 149.
- **The link side worked before:** with link 1 on a PHY on 149 (1.1.61, and solo), AWDL frames from 149 were received. TX on that link never completed, because the firmware does not schedule a client link without beacons.
- **Next combination:** the link on 149 for receive, ROC to take the radio there, the AUX queue to send.

## Change

- **ROC mode 4** (`debug.be201_awdl_roc` 4 + 16 × activity), through `iwx_awdl_roc_routes(mode, active)`:
  - As mode 3, but every AWDL frame takes the AUX queue between ROCs too, if the AUX queue is set up. It waits for the next ROC.
  - At most 8 frames wait (RocTxDrop beyond), and the watchdog already ignores that queue.
  - The OFDM minimum rate follows the same rule.
- **ROC tool:**
  - After mode 3, a 45 s phase sets `debug.be201_awdl_phy2` to 1 (link 1 on the sequence's non-AP 5 GHz channel, no windows) together with mode 4.
  - Then it sets both back to 0. Both are also reset on any exit.
  - Each phase records RxPhy2, RxHome and Phy2Chan.
- **Installer:** keeps the boot-argument order when `be201_awdl_vif=1 be201_awdl_auto=1` are already there as wanted. 1.1.85 stripped and re-appended them, which moved them behind the audio session's `nmhdavol=1`. The merge guards from 1.1.84 stay.

## Tests

- test-awdl-ba:
  - modes 0 to 4 decode, 5 does not;
  - `routes` is true while active, or in mode 4;
  - mode 4 takes every AWDL kind;
  - the TX path uses `routes` and needs a set-up AUX queue.

All 24 suites pass.
