# BE201 1.1.29: fixes found reading the 1.1.28 test

Evidence: boot B303DAB8, test 23:29, `outputs/BE201AWDL原生管理帧接收-1.1.28/`. No panic. 191 Apple AWDL action frames from one sender, ParseBad 0. NativeRxSubmitted 0, NativeRxInvalid 234. `invalid card capabilities`, `Dual band not supported` and `aw start event missing` still logged.

## Three errors

1. RX validator inverted (1.1.28). `iwx_awdl_rx_prepare` required body[5] to be zero. body[5] is the AWDL version; the family's actionFrameHasCorrectOUI requires it nonzero. No real frame reached the manager. Both test fixtures used version 0, so tests passed.
2. Wrong message number (1.1.26). reportDataPathEvents handles AW start in case 41 (0x29): monitorTimeline, logAWStart, sanityCheckAWStart, with its own log string naming APPLE80211_M_AWDL_AVAILABILITY_WINDOW_START. The SDK header says 42, and I used it. Case 42 only logs. That is why 14k posted events changed nothing.
3. Wrong capability bits (1.1.26). loadCardCapabilities passes controller ivars +0xb20 as apple80211_capability_data, so the version is at +0xb20 and capabilities[0] at +0xb24. I read +0xb24 as capabilities[4]. configure tests capabilities[0] bit 2. Dual band is capabilities[3] bit 5. The bits I set, capabilities[4] 0x04 and [7] 0x20, were meaningless here and are removed. The non-WCL path in this file has capabilities[3] = 0x2B, consistent. Also, the family loads this cache at boot, before arming, and otherwise only in resetInterface and getSetHandler.

## Changes

- Validator requires a nonzero version. Fixtures use 0x10. Zero is now a rejection test.
- AW start posted as 41.
- Armed: capabilities[0] |= 0x04, capabilities[3] |= 0x20. Just before link up, the timer calls native IO80211Controller::loadCardCapabilities(fNetIf), so the manager's configure reads them. Cache copied to `ItlwmAwdlCapabilityCache` (0x18 bytes).
- RX metadata time is now the host microsecond clock, the same clock as AW start. It was GP2, which nothing relates to AW start. Whether the manager's timing math accepts this is untested.
- Non-action frames are skipped before validation, so Invalid means an action frame failed. `ItlwmAwdlNativeRxLastBad` keeps its first 8 body bytes (no addresses, no TLVs).
- Test tool enables AW events along with the receive gates.

## Expected

For the first time the manager should see real peers: `peers:` above 0, and likely a sequence with 149. AW warnings should stop or change. Still no TX, so the phone cannot see the Mac, and Watch likely stays at 138. Not hardware tested.

## Risks

This is the first run with peers in the manager and with AW events it accepts. Family `_panic` sites include handleUmiTimer, removePeer, cleanUpForPeerRemovedFromNDP, mSecSinceAWDLON. AW start fields beyond those read are zero. wifip2pd may react to peers it cannot reach. loadCardCapabilities runs under the work loop gate and goes through sendIOUCToWcl for en1, as at boot; that context is new. Manual arm only, a normal boot is unaffected.

## Verification

All suites and the 58-unit build pass.
