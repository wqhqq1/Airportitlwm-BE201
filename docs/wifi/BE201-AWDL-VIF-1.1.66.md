# AirportItlwm 1.1.66: AWDL on its own without an infrastructure network

## 1.1.65 router test, 2026-11-08 20:11 (channel-20261108-201027.txt): the second channel is closed

- **Mode 7** (follows the sequence, link 1 queue, no windows): Phy2QDrop 173, nothing sent from link 1's queue. RxPhy2 118. Router RTT avg 19 ms.
- **Mode 8** (stays on 149, no windows): Phy2QDrop 154, RxPhy2 142.

With or without session protection (1.1.62 to 1.1.65), the firmware never sends from link 1's queues while link 1 is on another PHY than the AP's, though it receives there. A second channel beside an association is not possible with this firmware. Its RAM switches stay, off.

## What was missing

`iwx_awdl_ctx_add` ran only after an authorized association, on the AP's PHY context. Every path assumed an AP:
- the RUN state;
- `ni_port_valid`;
- `IWX_FLAG_MLD_TXQ_ACTIVE`;
- AP rates for the link;
- the AP station's queue for AWDL frames;
- receive interception only in RUN.

So with Wi-Fi on but not joined, AWDL had no firmware context, and AirDrop and Continuity over AWDL could not work. The same happened when macOS drops the network to give AWDL the radio.

## Change (on by default)

- **Trigger (`setAwdlSlot`, the AW tick):** after 5 s idle (`iwx_awdl_solo_idle`: INIT or SCAN, no transition pending, no teardown, not STA_ACTIVE, not shut down or in error), with the family's AWDL requested, context mode 6, no context yet, not tripped, and solo not failed, `awdl_solo_task` runs `iwx_awdl_solo_add`.
- **`iwx_awdl_solo_add` steps:**
  1. PHY context 1 goes to the sequence's 5 GHz channel (149 by default).
  2. MAC add, then link add.
  3. Link modify (no mask), then active with rates.
  4. AWDL station.
  5. A MGMT TID queue on the AWDL station (`phy2_qid`).
  6. The MAC is made associated.

  The same stages as `iwx_awdl_ctx_add` are used, so `iwx_awdl_ctx_remove` unwinds it. Leaving idle mid-way removes what was made. A command failure removes it, sets `solo_failed` for the boot and does not trip AWDL.
- **Link 1 parameters:** link 1 on its own uses fixed 5 GHz values: OFDM 6/12/24 Mbps ack rates, no CCK, short slot, beacon interval 100, the standard EDCA set.
- **Transmit:**
  - AWDL frames pass the no-AP-queue drop.
  - They use `phy2_qid`, bounded as in mode 6, unless the own queue takes them.
  - They never use a CCK rate or the AP-width fixed data rates.
  - The data gate, the room check and the sync-frame sender do not wait for an AP port or AP queues.
- **Receive and peers:** AWDL receive interception runs while solo too, and so does the peer station task while still idle.
- **Join:** `iwx_mld_auth` removes the solo context before the station MAC is added, so a join runs exactly as before. After an association, the existing context is built on the AP's PHY as before.
- **Teardown fix:** `iwx_awdl_ctx_remove` keeps `phy2_chan` and `solo` until the link and MAC are removed. The deactivating LINK_CONFIG then names the PHY context the link really sits on; before, it named the AP's PHY context even when the link was on the second one.
- **Second channel switches:** setAwdlRadioTest ignores them while solo.
- **Properties:** Solo, SoloAdds, SoloRemoves, SoloFailed, SoloErr, SoloErrStage.
- **Tests:** test-awdl-ba checks the solo order, failure handling, idle conditions, the trigger, the join removal, TX exemptions and rates, link parameters, teardown order, peers and receive. test-awdl-probe follows the new receive condition.
