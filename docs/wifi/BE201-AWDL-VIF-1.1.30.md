# BE201 1.1.30: send the system's discovery frames

Evidence: boot 74113322, test 06:46, `outputs/BE201AWDL收帧与事件修正-1.1.29/`. No panic.

## What 1.1.29 showed

All three fixes worked. Capability cache correct (`0e560e20`), social channels 6, 149, 44, sequence [149 0 149 0 0 0 0 0 6 0 149 0 ...] with infra 149. NativeRxSubmitted 448, none invalid. Kernel: `New Peer discovered`, `peers:1`, Peer Count 2 at one point, `programChipWithNewMaster`. `awdl0` still 0 packets. Watch still 138. User: Handoff worked before and after arming this boot, and has been seen failing both before and after, or working only after, so no link to arming.

Manager now waits on us: `actionFrameReport: Waiting set routable for Peer ... to see this DUT`.

New complaints:
- `slot 0 start too soon (17ms), ignore`, 3 of every 64 events. Slot = (number mod 64) / 4, and slot 0 is ignored within 64 ms of the last. So AW start is per 64 TU slot, with the number advancing by 4, not per 16 TU. Inferred, not seen natively.
- `mismatch of channel sequence with Firmware, force to program`, reprogrammed 250 times, because the getter failed.
- `getAwdlSyncEnabled enable state mismatch`.

## What firmware must add, read from the family

- `buildMasterIndicationTemplate` and `updateSyncFrameTemplate` produce TLVs only: election v2, service params, service responses, data path state, version and others. No action header, no sync params TLV 4, no channel sequence TLV 18.
- MI request (OOB_AUTO_REQUEST, set by updatePrimaryPayloadMI): address at +4, BSSID at +0x16, length word at +0x28, pointer at +0x30 into the manager's buffer. Observed length 0x220. +0x0c is 6600, meaning unread.
- Sync template: {version, length, pointer}.

## Changes

- RAM sysctl `debug.be201_awdl_vif_tx`, default 0. With it, after the monitor is requested, native transmit is on.
- `iwx_awdl_build_native`: MAC and action header, sync TLV 4, election TLV 5, channel TLV 18 as in `iwx_awdl_build` (following the heard cluster, all slots on the current channel, because the radio does not hop), then the system's TLVs. PSF every 110 TU, MI every 224 ms, broadcast only. Still sent only within 20 ms of hearing a peer, on the AP's management queue, as on 1.1.18.
- System TLVs are walked for well-formedness and bounded to 1024 bytes before they are stored. `ItlwmAwdlTemplateMif`, `ItlwmAwdlTemplatePsf` keep a copy; `ItlwmAwdlTemplateBad` counts rejects.
- AW start: one per 64 TU, number advancing by the sequence's step count + 1 (byte 7 of the request, observed 3), channel from slot number / steps.
- Set values are read back for sync params, sync enabled, channel sequence, master, secondary master, sync state, AF TX mode. Other getters stay refused.

## Expected

Phone's wifip2pd logs this address as a peer. Manager's "Waiting set routable" may clear, and "too soon" and sequence mismatch lines stop. ItlwmAwdlTxMcastOk rises with Sent. `peers:` stays above 0.

## Not expected

The phone listing the Mac in AirDrop. That needs unicast data on awdl0, IFF_RUNNING and queue callbacks. Watch: the system asks for channel 6 with the Watch as forced master, and this radio stays on 149, so 138 should stay. Ranging itself is an unknown for this card.

Handoff: earlier notes saw failures on boots with frames on air, but also without. It is not a pass criterion.

## Risks

Real frames from the system's address with the system's services on air for the first time. First unverified layer: TLV 5 and sync TLV describe the heard cluster, while the system's election v2 may name a different master; how the phone treats that is unknown. Firmware fault latches TX off (`tx.tripped`). Manual arm only; a normal boot is unaffected. sysctl tx=0 before arming gives the 1.1.29 behaviour with the corrected AW timing.

## Verification

All suites and the 58-unit build. Not hardware tested.
