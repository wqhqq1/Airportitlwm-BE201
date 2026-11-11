# AirportItlwm 1.1.74: awdl0 runs again after Wi-Fi off and on; llw0 off by default

## 1.1.73 result, boot 2026-11-10 12:05

- **AirDrop worked at first.** Four sends over AWDL from 12:06 to 12:09, including one large upload to the iPad.
- **12:10:07, Wi-Fi off:** user space powered Wi-Fi off ("user space power off", apple80211 reason 5), then on again. It did this again at 12:10:53.
- **Every send after that failed:**
  - Asks were cancelled after 5 to 25 s.
  - sharingd resolved the peer on awdl0. QUIC then failed 1 ms later with "received error: Network is down", and the connection failed with TLS error 50.
- **State at the time:** awdl0 flags 0x8803 (UP without RUNNING). The driver side was healthy: context active, monitor ready, peers 2, no firmware error.
- **The fault re-arm from 1.1.73 was not needed.** SoloFailed 1 (SoloErr 5, stage 4) came without a firmware fault.

## Cause

- Native drivers set IFF_RUNNING from `enableDatapath`, which runs each time the family enables AWDL.
- Here `enableData` runs once, at the first link-up, and keeps `dataActive` set.
- Turning Wi-Fi off cleared IFF_RUNNING while awdl0 stayed up. Nothing set it again, so the stack refused every send on awdl0 with ENETDOWN.

## Change

- **`restoreRunning`:** with the data path active, awdl0 UP, RUNNING clear, and the family's link state up, it does what native `enableDatapath` reports:
  1. `reportLinkStatus(3, 0x80)`;
  2. sets IFF_RUNNING;
  3. calls the base `setRunningState(true)`.

  It is called after a successful `setLinkState(up)` and at slot 0 of every AW cycle as a fallback. It does nothing when awdl0 is down or the link is down. Property: ItlwmAwdlRunningRestores.
- **llw0 off by default:** `startAWDLAuto` stores 0 in `debug.be201_awdl_llw`, and ItlwmAwdlLowLatencyDefault is false. The two-channel AirDrop work is measured without llw0. `sudo sysctl -w debug.be201_awdl_llw=1` still creates it.
- **Unchanged:** UMI, peer cache answers, RTG cache answers, own queue with aggregation, solo AWDL, and the queue and fault fixes from 1.1.73.

## Two channels: what the firmware supports (research, no code yet)

The firmware is iwlwifi-bz-b0-fm-c0-92. There is no public firmware documentation. The reference is Intel's own Linux driver (iwlmld, v6.15), plus the command-version table in the firmware file.

- **Concurrent channels in iwlmld:**
  - `iwl_mld_iface_combinations` allows `num_different_channels = 2` for up to 2 stations, 1 P2P client or GO (or AP), and 1 P2P device.
  - For a client link, `iwl_link_config_cmd.dtim_interval` is documented as "Relevant only for GO, otherwise this is offloaded". The firmware takes a client's timing from its AP's or GO's beacons.
  - Our AWDL MAC is `FW_MAC_TYPE_P2P_STA` with the fixed AWDL BSSID. Nothing beacons from that BSSID, so the firmware has no timing to schedule link 1 on another PHY.
  - This matches 1.1.42 to 1.1.65:
    - Receive worked on the second PHY (RxPhy2).
    - Nothing queued for link 1 was ever attempted (OwnDonePhy2 0, no success and no failure), with or without session protection.
  - The tests were consistent; the approach (a client link without a beaconing GO) does not fit the firmware's scheduling model.
- **What the driver can request instead:**
  - **`ROC_CMD`:** MAC_CONF 0x0E, version 4 in this firmware's table, with notification ROC_NOTIF 0xF8. iwlmld (`roc.c`) uses it for P2P device remain-on-channel:
    - An AUX station (`AUX_STA_CMD` 0x0B) carries the frames sent during the ROC.
    - `node_addr` sets the receive filter.
    - `max_delay` and `duration` are in TU.
    - The version-5 layout (no interval or repetitions) applies to versions below 6.
    - Activities: HOTSPOT 0, P2P_DISC 1, P2P_TXRX 2, P2P_NEG 3.
  - **Session protection:** valid only for association of a BSS_STA or P2P_STA, and for a P2P device's listen or negotiation.
  - **A GO MAC:** scheduled by the firmware, but it beacons, so it is not usable for AWDL.
- **Other projects:** OWL on Linux needs a card in monitor mode with injection. The MediaTek AirDrop work keeps Wi-Fi up by running AWDL on the AP's own channel, as this driver does on one channel.
- **Next step:** an ROC-based second channel, off by default.
  1. An AUX station with its own queue.
  2. ROC on the AWDL sequence's 5 GHz channel for the length of its run of slots, with `node_addr` set to the AWDL address.
  3. While an ROC is running, AWDL frames for that channel go out on the AUX queue.
  4. ROC_NOTIF start, end and failure are counted.

  Open questions, to be measured:
  - whether the firmware sends data frames, not only management frames, from an AUX station;
  - the shortest ROC it grants next to an associated station.

## Tests

- test-awdl-vif:
  - RUNNING is restored on link up;
  - it is not restored while awdl0 is down or the link is down;
  - it is restored only once.
- test-awdl-ba: llw0 is off by default; the restore is called from `setLinkState` and the AW tick.

All 24 suites pass.
