# BE201 1.1.4: observe Instant Hotspot association and key-handshake failures

1.1.3 is confirmed loaded on boot D725F9A3-5B04-4292-8D22-DDFED9D33A61.
The user reports direct Instant Hotspot still fails; earlier occasional success
may have followed manually opening the phone's Personal Hotspot settings.
That is not accepted as Instant Hotspot success. Manual Wi-Fi switching remains
improved, Handoff is provisional, and Bluetooth stays at the working 2.5.9/2.7.11.

The 11:39:29 attempt receives the system's hotspot-enabled result at
11:39:33.915723 (channel149). WCL accepts an Instant Hotspot WPA2-PSK/PMK
join at33.960279 and reports association completion at34.006095. At34.065166
native WCL handles a peer teardown with IEEE reason3 before link-up. Its
internal retry associates at34.351586 and tears down at34.430903, again
reason3. airportd ends with-3906. Later attempts also report enabled then fail
association. No first UMAC fault snapshot is present at11:45:57; that does not
establish all faults are fixed or prove a successful connection.

Reason3 does not identify the failing handshake step, prove a bad password,
or establish AWDL as the cause. WCL association is not RSN port authorization
or DHCP. User opening the phone settings is a confounder; future Instant
Hotspot tests should leave that page closed and Allow Others to Join disabled.
Apple's documented Instant Hotspot path permits the latter setting to be off:
https://support.apple.com/en-us/109321

This is an OBSERVATION RELEASE, not a claimed hotspot fix. It preserves1.1.3
coding flags and1.1.2 teardown ordering. The existing default-off numeric
`be201_tlc_diag=1` also enables a separate bounded join snapshot. No new boot
argument, firmware command, retries, authentication decisions, security
exceptions, Bluetooth changes or claimed AWDL capabilities are added.

A preallocated32-entry scalar ring records: message1 entry, message2 send
attempt/return with supplicant state, message3 entry/MIC/decryption checks,
message4 attempt/successful function return, key installation stages, local
message3 abort reason, received deauth reason and three address equality bits,
association status and link events. Submission is not delivery/acknowledgement.
Only equality booleans are recorded, never actual MACs, SSIDs, passwords, PMKs,
nonces, keys, authentication payloads or whole frames. Scalar notes perform no
allocation, logging, IORegistry writes or extra I/O in the receive fast path.

At a pending join's terminal event, WCL publishes a fixed360-byte metadata
snapshot plus ring. First failure is retained, last failure and last success
are separate, so successful router auto-join cannot overwrite the failure.
Deferred joins omit the previous peer's trace. Metadata includes request/start
counts, state, negotiated AKM/cipher, reason/status, RSN IE length, key cipher
type, association/beacon/port flags, channel and existing cumulative counters.
First/last can refer to other joins; correlate request/boot/window before use.
Counters are boot cumulative, not per-peer. The raw deauth-address match mask
can help reject misattribution without storing identifiers; it is not proof of
an authenticated management frame.

Verification: actual ring/publisher ASan/UBSan tests cover disabled behavior,
100000 writes, wrap, saturation, first-failure retention, failure/success
separation, deferred-peer isolation. Strict decoder validates exact ABI/length,
ring indices/events and metadata. Removing only scalar-note lines makes both
modified net80211 security files byte-identical to hash-pinned1.1.3 fixtures;
all prior branches/calls/returns remain unchanged. Production switch/teardown
and boot helpers are checked because the internal shared controller struct
changed. Full57-source build, fixed firmware/SDK, imports/entry/constructors and
signature are audited before same-disk EFI deployment with1.1.3 rollback.

Reboot is required; never hotload or automatically reboot. After one direct
Instant Hotspot failure, collect the fixed snapshots before manual opening or
retries. Next action depends on the first missing stage: no message1 (RX/queue),
message2 then peer teardown (PMK/IE/address/airtime), message3 validation/keys,
or port valid then upper-layer completion. Do not add guesses to those paths
before the trace is available.
