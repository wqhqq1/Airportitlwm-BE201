# AirportItlwm 1.1.94: link 1 moves keep rate control valid for the PHY

The defaults are the same as in 1.1.93. The ROC switch stays off, and the Bluetooth drivers are unchanged (2.7.13 / 2.5.10).

## 1.1.93 result, boot 2026-11-12 12:18, test at 12:20

- **System:** macOS 15.8.3 (24H241), 1.1.93 / 2.7.13 / 2.5.10 loaded.
- **Router:** channel 153 at 80 MHz.
- **Baseline:** system peers 2. Earlier in this boot an AirDrop had run: OwnSent 156 586, OwnAgg 1.
- **Mode 1, P2P_TXRX:**
  - 61 adds, 62 started and ended, no error.
  - Start delay 5.2 ms average (30.5 ms max), dwell 61.4 ms.
  - RocRxAwdlAny 4.
- **Link moved to 149, ROC off: firmware assert after about 2 s.**
  - Error `0x20101A28`, data `0x20004`, last command `0x7B0309` (LINK_CONFIG_CMD, MAC_CONF group).
  - FaultPhy2 `0x959501`: move running, wanted 149, and the PHY context already on 149. So the PHY update had succeeded, and the fault came on a LINK_CONFIG after it.
  - FaultRoc `0x950120`: no ROC pending or active, AUX station removed. So, as on 08:27, the ROC did not overlap the move.
  - The "last PHY command 153/80" reading is the restart's rebuild, not the move.
  - Phy2Err 35, FaultHolds 1. The tool skipped mode 4.

## Reading

- **The same move worked at 08:46 and 09:01** (RxPhy2 20 and 24). Those boots had almost no own-queue traffic (OwnSent 5 and 8 in that phase).
- **This boot had an aggregated own queue.** Its peer station's firmware rate control (TLC) had been built for the AP's 80 MHz PHY (VHT MCS 0–9, max width 80).
- **What the move left alone:**
  - It released the own queue only on a move *off* the second channel, not onto it.
  - It never re-sent TLC. Since 1.1.90 the second context is 20 MHz, so the link went active on a 20 MHz PHY with a station still configured for 80 MHz and live aggregated frames.
- **Linux (iwlmld) updates TLC for a link's stations** when the link gets a channel context, before it activates the link.
- The assert ID is in the same UMAC family as the earlier TLC assert (`0x20101A0D` at TLC_MNG_CONFIG). That fits, but it does not prove the cause. The firmware is closed. The new snapshot below says which step faults if it happens again.

## Change

- **Peer TLC follows the PHY at every step:**
  - `iwx_awdl_peer_tlc(sc, index, width)` is the TLC half of `iwx_awdl_peer_agg`. A success sets the station's bit in `peer_tlc`.
  - Before a move onto the second channel, every station in `peer_tlc` goes to 20 MHz, while still on the AP's PHY. 20 MHz is valid on both PHYs.
  - After a move home, once the link has the AP's PHY again and before it is activated, the stations go back to the AP's width (`iwx_awdl_move_tlc_narrow` / `_widen`).
  - `iwx_awdl_peer_agg` builds at 20 MHz as soon as a move is wanted (`phy2_chan || phy2_want`). A build that runs between the move's commands then fits both PHYs.
  - `peer_tlc` is cleared on context removal and on firmware restart, and per index when a peer is replaced.
- **Own queue on every move:** it is released (in mode 5, flushed) on a move onto the second channel too, before the ROC cancel and the link deactivation (Phy2OwnQuiesces). It is rebuilt afterwards by the usual retry, at 20 MHz.
- **No own-queue build during a move:** `iwx_awdl_ownq_task` returns while `phy2_moving` is set.
- **Fault snapshot:**
  - `ItlwmAwdlFaultLink`:
    - bits 0–3: the move step. 1 TE, 2 own queue, 3 ROC cancel, 4 TLC narrow, 5 inactive, 6 no PHY, 7 PHY update, 8 with PHY, 9 TLC widen, 10 active.
    - bit 4: own queue. Bit 5: aggregated.
    - bits 8–15: peer stations. Bits 16–23: peer TLC mask.
  - The step is cleared when a move ends and on restart.
- **New properties:** ItlwmAwdlPhy2TlcRefreshes, Phy2TlcErr, Phy2OwnQuiesces, PeerTlc, FaultLink.
- **ROC tool:**
  - Each phase prints the TLC error, peer stations, the TLC mask and own-queue aggregation.
  - A fault line names the move step, own queue, peers and TLC.
  - TLC refreshes and own-queue quiesces appear in the changes.

## Next test

- Reboot, then 开始ROC实验.command. Start the AirDrop first, as before, so that the own queue is aggregated when the link moves.
- In the phase "链路先移到 149":
  - Expect no firmware error.
  - Phy2TlcRefreshes should rise by the number of stations with TLC, and Phy2OwnQuiesces by 1.
  - RxPhy2 should count.
- Then mode 4 runs (the host hold from 1.1.92 has not been tested yet).
- If it still asserts, the fault line's 移动步骤 says where.

## Tests

- **test-awdl-ba:**
  - The narrow and widen rules, and the FaultLink encoding.
  - The move order: TE → own queue (outside the second-channel-only block) → ROC cancel → TLC narrow → inactive → PHY → with PHY → TLC widen → active → step cleared.
  - `peer_agg` width during a move, `peer_tlc` mark only on success, the refresh loop counters, and the clear sites.
  - No own-queue build during a move, the snapshot before `++sc_fw_errors`, the properties and the declarations.
- **Result:** all 25 suites pass. `install.py --check` PASS.

## Kit and install

- **Kit:** AirportItlwm 1.1.94, UUID `fbf77b50-6f5b-3770-a94a-ac991cbd8be0`, SHA `67b12077`. No new imports.
- **Installed:** 2026-11-12 12:36 on EFI disk0s3.
  - Backup: `EFI-backups/EFI-before-install-20261112-123610`.
  - Recovery: AirportItlwm 1.1.93 (`5630c031`).
- **Config:** compared with a copy taken just before, only the Wi-Fi row comment changed.
  - config equals pending, ocvalidate clean, boot-args unchanged, Kernel/Add 35.
  - ShowPicker False, Timeout 0, TakeoffDelay 100000, MacBookPro16,2, BE201BluetoothFirmware `bb027eb4`.
