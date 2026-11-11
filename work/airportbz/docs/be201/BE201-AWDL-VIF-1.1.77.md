# AirportItlwm 1.1.77: peer stations are replaced, and the bulk peer gets the own queue

## 1.1.76 result, boot 2026-11-10 15:28

- **Still slow.** The own queue existed with aggregation (OwnAgg 1, TID 0, OwnQueue 10), yet only 7 of 44623 completed frames went through block ack. OwnRetargets was 11. OwnTransient stayed 0, so the 1.1.76 retry never had to act.
- **After Wi-Fi and Bluetooth off and on (15:30:46):**
  - AirDrop asks failed.
  - The QUIC Initial on awdl0 got no answer (udp summary: 1 packet out, 0 in over 0.95 s), so the connection moved to en1 (the phone's hotspot). There QUIC failed with "Message too long" (seen only after the toggle, at 15:31:04 and 15:33:12).
  - The family showed 7 to 9 AWDL peers. PeerStations stayed at the same 4 addresses all boot.

## Cause

- **Peer station table:** it has 4 places (`IWX_AWDL_PEER_STA_MAX`) and never loses an entry. `iwx_awdl_peer_note` fills it first come, first served, from any sender at -65 dBm or better, and a cache delete keeps the station.
  - With 8 devices nearby, the AirDrop target often had no station. A peer with no station cannot get the own aggregated queue, so its data went out on the AP queue at about 4 MB/s.
  - After Wi-Fi and Bluetooth are toggled, the peers come back with new AWDL addresses. None of the new addresses got a station.
- **Own queue choice:** the queue serves one peer and moves only after 1 s of quiet. A trickle to another station (Universal Control to the iPad) kept it there while the bulk went to the iPhone.

## Change

- **Replacing stations:**
  - Each station records when it was last heard (`peer_seen_us`, refreshed by every AWDL action frame from it).
  - A new sender at -65 dBm or better may take the place of a station quiet for 3 s (`IWX_AWDL_PEER_IDLE_US`).
  - A family cache request takes the least recently heard station, quiet or not. The family asks for the peer it is about to send to.
  - Neither one takes the station that the own queue uses.
  - A cache delete makes its station the first to go.
- **Peer task:** replacements run before additions, in this order:
  1. release the own queue, if it is on that station;
  2. remove that station's RX block ack sessions;
  3. `STA_REMOVE`;
  4. the new address takes the same index;
  5. `STA_CONFIG`.

  The cache answer for the new peer then follows as before. Failures:
  - `STA_REMOVE` fails: the old station stays (PeerReplaceErr).
  - The new station fails: further additions stop, as for a failed add.

  Properties: PeerReplaced and PeerReplaceErr.
- **Bulk peer:**
  - Unicast data bytes are counted per station over 500 ms windows.
  - A peer with at least 512 KB in a window, and at least 4 times the current peer's bytes, takes the own queue at once (`own_target`). Property: OwnBulkMoves.
  - The 1 s quiet rule stays for everything else.
- **Not changed:**
  - The "Message too long" on en1 belongs to the infrastructure path. It came after AWDL failed. It is not addressed here and is to be watched.
  - ROC test, running restore, llw0 off.

## Tests

- test-awdl-ba:
  - victim selection: least recent, keep, quiet only, no clock;
  - cache replacement, pending, and delete;
  - the heard-sender rules: refresh, quiet only, far;
  - bulk selection and the byte window;
  - peer task order;
  - resets and call sites.
- test-awdl-ctx: slices adjusted.

All 24 suites pass.
