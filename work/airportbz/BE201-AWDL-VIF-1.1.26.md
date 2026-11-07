# BE201 1.1.26: AW start events and dual band for the AWDL manager

Follow-up to the 1.1.25 arm test (boot 6BD3B687, 22:08).

## What 1.1.25 showed

No panic. `configure done`, link state 2, 478 requests in about three minutes. Types 120 and 164 now succeed. The system's AWDL logic runs, with 5 services and 4 AirDrop services registered. Watch error moved from 192 to 138, "Ranging Timeout: Couldn't Find Peer", after 10 s, matching the user's spinner. awdl0 stays at 0 packets, phone still cannot see the Mac, Handoff unchanged per user.

Manager complaints:
- `configure ERROR: invalid card capabilities` (bit 34 clear).
- `Dual band not supported`, so social channels are {6, 0} and the sequence is [6 0 6 0 0 0 0 0 6 0 6 0 0 0 0 0]; it knows infra is 149 on the iPhone (bit 61 clear).
- `Did not get AW start event` continuously, and `no TX or RX`.
- `setAFTXMode FW[3] Host[3]` on the Watch attempt.

## What the manager wants, read on 24G824

- APPLE80211_M_AWDL_AVAILABILITY_WINDOW_START is 42, posted through postMessage into reportDataPathEvents. Fields used: AW number at +0, master address at +0x0e, firmware time at +0x14, channel {version, channel, flags} at +0x18.
- Sync frame template: {version, length, pointer}, payload inline right after. Observed 0x70 bytes of TLVs only (06, 18, 0c, 2d, 15...), no action header. So firmware adds the fixed header, the sync params and channel sequence TLVs.
- Received action frames enter through IO80211VirtualInterface::bpfTapInput(buffer, 0xc, ctx, len) -> manager slot 0x230 actionFrameInput. ctx layout not read yet.
- AirDrop's peer list on the phone needs the TLS /Discover exchange over awdl0 in addition to service TLVs, from public AirDrop descriptions, so it needs TX, RX and data.

## Changes

- Capability bits 34 and 61, only when be201_awdl_vif=1 and armed.
- RAM sysctl `debug.be201_awdl_vif_aw`: after link up, a 16 TU work loop timer posts AW start with an incrementing number and the slot's channel from the programmed sequence. The driver's clock, master is self, nothing moves on the radio.
- Payload copies add OOB_AUTO_REQUEST (550) and OOB_REQUEST (541), 0x300 bytes raw.

## Expected

Sequence includes 5 GHz (likely 149), `invalid card capabilities` and AW warnings go away, and we capture what the manager asks to send in each window. Still nothing on air. Phone still cannot see the Mac; Watch still ranging timeout.

## Risks

- 61 events a second on the Wi-Fi work loop; en1 latency is what to watch.
- Struct fields beyond those read are zero. Bad values may log sanity failures; a panic is possible.
- Dual band report could change what wifid does on en1 after arming only.
Manual arm only. A normal boot is unaffected.

## Next

Radio: ctx=6 started after arming with the system's address, frames sent on the AP queue built from existing iwx_awdl_build plus manager TLVs. Then RX into bpfTapInput. Then RUNNING and a data path.

## Verification

21 suites pass and the build links. Not hardware tested.
