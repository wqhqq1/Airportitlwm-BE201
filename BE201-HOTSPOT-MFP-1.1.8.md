# BE201 1.1.8: offer MFP on iPhone hotspot associations only

Evidence, boot 872F7642-70AA-4BEB-BED9-AD9D9CB29021 on 1.1.7, phone Allow Others off:
- Rapport/BLE request succeeds, airportd associates in the same second.
- Failed joins end 110-136 ms after association starts: M3 MIC valid, M4 TX status 1,
  both key replies normal, AUTHORIZED update returned 0, then reason 3 with match mask 7.
- A correct PSK is therefore proven. 1.1.7's firmware state update did not change this.
- beacon=0 on failure is not a separate fault: the hotspot beacon interval is 300 TU
  (bi=300), so a failure inside about 136 ms precedes the first beacon. A success takes
  334 ms for the same reason.
- 13:14:13 success follows the user opening the phone's hotspot settings (phone activity
  level User at 13:14:11). It is not automatic hotspot success. Same MAC, same RSN and
  same event order succeed then, so the deciding state is on the phone.

Mismatch found: airportd requests a 28-byte RSN element that offers MFPC and BIP-CMAC
(`rsn_length` 28, `mfp=capable`, `caps=0xBC`). WCL uses it only for the group cipher and
sends a 22-byte element without MFP because iwx never sets IEEE80211_C_MFP. A real Mac
would negotiate MFP with this phone. Whether the phone's closed mode depends on that is
NOT proven; there is no phone-side log yet. This candidate is the test of that hypothesis.

net80211's MFP was also incomplete here: RX/TXMGMTPROT were never set, and a firmware
decrypted management frame would have been decrypted again in software.

Change:
- Scope `hotspotMfpScope`: OS request offers MFPC+BIP, beacon interval 300, peer offers
  MFPC+BIP, WPA2-PSK. Decided per join; anything else clears C_MFP and keeps the previous
  22-byte association. Uncached nodes stay off. The Apple vendor element is reported only.
- With C_MFP the existing builder produces byte-for-byte the requested 28-byte element.
- PTK use enables both management protection directions; teardown clears them.
- Unicast management RX uses firmware decryption with the separate management replay
  counter. Multicast BIP stays software.
- Unprotected robust frames are dropped as the standard requires, and counted once.

Diagnostics (be201_tlc_diag=1): event 32 scope bits, 33 M4-to-peer-disconnect in us,
34 unprotected robust frame dropped (subtype). `ItlwmWclHotspotMfpScope` is always set.
Expect 0x1f or 0x17 for the hotspot, event 13 (IGTK) and event 30 value 1 when active.

How to read the result:
- Automatic join and real data work: the hypothesis holds.
- Reason 3 with event 13 and event 30=1: MFP is excluded; next read phone logs and test
  hardware MAC.
- Event 34 then no disconnect: the phone sends an unprotected teardown; SA Query is next.
- Scope lacks a required bit: the gate did not match; nothing was tested.

Known risk: the manual-open hotspot now also uses MFP. Protected ADDBA/SA Query are
implemented in code but only hardware can prove them. Use the rollback config if it
regresses. Ordinary networks do not enter the scope.

Verification: scripts/test-hotspot-mfp.py (exact element bytes, gate, 500000 malformed
inputs under ASan/UBSan) plus existing disconnect, switch, STA, key, beacon, join, HE, TLC
and boot suites; 57-unit build. NOT hardware tested. Not accepted as a hotspot fix.
