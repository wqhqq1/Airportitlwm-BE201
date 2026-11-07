# BE201 1.1.9: send the Instant Hotspot station element

Phone logs, boot 346D6C12 on 1.1.8, iPhone archive 13:52-14:07 (iOS libtrace format 6,
read with work/hotspot-ie-119/conv.py and tv3.py on a copy):
- Hidden hotspot: `Enable MIS Discoverability ... hidden=1`, then wifid logs only `MIS STA
  Disassociated` for this Mac, with no `MIS STA Associated`. Attempts at 14:02:09/10/22/25.
- Broadcast hotspot: `MIS STA Associated`, `Client Type: Others`. A nearby Apple device on
  the same phone is `Broadcast iOS Client`.
- wifid's type strings: Auto Hotspot Client, Instant Hotspot Client, Broadcast iOS Client,
  Others. So the AP distinguishes clients; this Mac is never marked as an Instant client.

Native driver, this host's Boot KC:
- `AppleBCMWLANCore::setWCL_ASSOCIATE` reads word +0x1e0 of apple80211AssocCandidates:
  bit1 ", Instant Hotspot", bit2 ", Auto Instant Hotspot". decodeJoin ignored this field.
- `updateSTAAssocInfo` (AP role) walks the association elements for vendor 00:17:f2 type
  0x0b and logs "Associating STA ... has instant HS IE, flags %x"; flags are at offset 9,
  bits 0 and 1 are stored separately.
- No host code builds type 0x0b on the station side, and system binaries have no such
  bytes, so real hardware probably builds it in firmware. Not verified.

PROVEN: flag offset and bits, vendor, type and flags offset as the macOS AP role reads
them. INFERRED: the iPhone parses the same way; offsets 6-8 (copied from sibling type 6
`01 01 03`); bit0=Instant, bit1=Auto; that the missing element causes the reason 3.
The element is sent last in the association request; native order is unknown.

Change: when the OS flags the join as Instant or Auto Instant, append
`dd 0a 00 17 f2 0b 01 01 03 <flags> 00 00` to the host-built association request.
Other joins are byte-identical to 1.1.8. MFP scope stays as in 1.1.8 (inactive here).

Diagnostics: `ItlwmWclJoinAssocFlags`, `ItlwmWclJoinRSN` (public element bytes, resolves
the 1.1.8 unknown), event 35. Phone logs now answer directly: look for `MIS STA Associated`
in hidden mode and the `Client Type` value.

Reading the result:
- Hidden mode join with data: fixed; note Client Type.
- AssocFlags 0: the OS did not flag this join; the element was not sent; nothing tested.
- AssocFlags set, still reason 3: read phone logs; next vary offsets 6-8 and flags.

Verification: scripts/test-hotspot-client-ie.py plus all existing suites; 57-unit build.
NOT hardware tested and not accepted as a hotspot fix.
