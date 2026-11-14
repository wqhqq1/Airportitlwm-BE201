# AirportItlwm 1.1.95: AWDL rates fit the 20 MHz channels; session windows on 149 get a new test

The defaults are the same as in 1.1.93/1.1.94. The ROC switch and the second-channel switches stay off, and the Bluetooth drivers are unchanged (2.7.13 / 2.5.10).

## 1.1.94 result, boot 2026-11-12 15:49, test at 15:54

- **System:** macOS 24H241, router on channel 153 at 80 MHz.
- **No firmware error in the whole test**, for the first time with mode 4 included.
  - (The boot before, 12:39, had failed to start the card: UMAC assert 0x20100506 at firmware-wait-alive, after a warm restart. A second reboot was fine.)
- **Mode 1:** 48 adds, 44 started and ended, 3 failed. Start delay 8.7 ms, dwell 60.8 ms.
- **Link on 149, ROC off:**
  - RxPhy2 23. One peer station appeared, with TLC (PeerTlc 0x01).
  - When the link moved there were no peers with TLC, so the 1.1.94 TLC narrowing had nothing to do (Phy2TlcRefreshes 0). The 12:20 condition was therefore not repeated exactly.
- **Mode 4, 90 s:**
  - 179 ROCs, start delay 5.5 ms, dwell 43.9 ms.
  - Host hold: 59 held, 37 released at ROC start, 22 expired.
  - AUX unicast: 39 sent, **6 ok, 33 failed**. 32 of the failures completed after their ROC (FailOut). All were long limit (0x83), with **no retries counted**.
  - Multicast: 120 ok.
  - RxPhy2 89. The phone saw the Mac; the transfer waited, then failed.
- **Rate:** by the end, the AWDL rate step had fallen to the lowest legacy rate (DataRateMcsStep 6, 6 downs).

## Reading

- **Releasing frames at ROC start does not get unicast frames sent in the ROC.** They still complete after it, untried.
  - So the firmware does not schedule them on the AUX queue during the ROC.
  - Multicast "ok" needs no ACK, and most multicast frames are AWDL action frames.
- **Linux uses the AUX station only for P2P management frames.** AirDrop's frames are unicast data.
  - Whether the AUX station sends data at all is now counted (RocTxOkUcastData / RocTxFailUcastData).
- **Rate bug found:** the AWDL unicast rate was capped only by the AP's width. With the AP at 80 MHz, a climbed step sent VHT 80 MHz rates on 20 MHz ROCs, and on link 1 at its 20 MHz 149 context (1.1.90). Those frames cannot be sent there.
- **Session protection windows on link 1 (1.1.60–1.1.63) were never tested on a valid PHY.** They had OwnOk 0 on the second channel, but then the 149 context had the AP's width (wrong centre, fixed in 1.1.90) and the peer's TLC was 80 MHz (fixed in 1.1.94). The route is worth one more test.

## Change

- **`iwx_awdl_rate_fits`:** an 80 MHz AWDL rate only when the AP's PHY is 80/160 MHz **and** the frame is not for an ROC **and** link 1 is not on the second channel. Otherwise the 20 MHz top step (VHT 2SS MCS 8) is used.
  - Default behaviour is unchanged (no ROC, link on the AP's PHY).
- **AUX unicast data counted apart:** RocTxOkUcastData, RocTxFailUcastData. The rest of the unicast is management.
- **ROC tool:**
  - After mode 4 (link still on 149), a new 60 s phase: ROC off, `debug.be201_awdl_phy2_te=3` (windows at this Mac's 149 slots, kind 0 — kinds 1 and 2 asserted in 1.1.63).
  - Each phase prints window requests, starts, ends and failures, and the own queue on 149: sent, done, failed, block acks and last status.
  - A fault, the end, and any exit turn the windows off before the link leaves 149.
  - The whole run takes about 5 minutes.

## Next test

- Reboot, start an AirDrop, then run 开始ROC实验.command.
- **Mode 4:** compare RocTxOkUcastData / FailUcastData with the management count.
- **Window phase:**
  - CtxTeStarted should follow CtxTeRequests.
  - The key numbers are OwnDonePhy2 and OwnBaPhy2 against OwnFailPhy2. Any completion there would be the first own-queue frame sent on 149.

## Tests

- **test-awdl-ba:**
  - The rate rule (80 MHz only on an 80 MHz PHY, never for ROC or phy2), its use in `iwx_tx_fill_cmd` (the old AP-only check is gone), and the data counters at the AUX completion.
  - ROC tool order: windows only after mode 4 and before the link leaves 149, and off first on a fault and at exit.
- **test-beacon-peer-tx:** stubs extended for the new completion lines.
- **Result:** all 25 suites pass.

## Kit

- AirportItlwm 1.1.95, UUID `e0d946ac-d03e-36a2-8eef-a1686bb78486`, SHA `80c53cb0`. No new imports.
- **Installed:** 2026-11-12 16:07 on EFI disk0s3 (mounted by the user).
  - Backup: `EFI-backups/EFI-before-install-20261112-160713`.
  - Recovery: AirportItlwm 1.1.94 (`67b12077`). Bluetooth untouched.
- **Config:** compared with a copy taken just before, only the Wi-Fi row comment changed.
  - config equals pending, ocvalidate clean, boot-args unchanged, Kernel/Add 35.
  - ShowPicker False, Timeout 0, TakeoffDelay 100000, MacBookPro16,2, BE201BluetoothFirmware `bb027eb4`.
