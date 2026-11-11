# BE201 1.1.5: associated beacon delivery and teardown peer validation

Boot24ADC69C-3C19-459B-AB5E-F8C1EE09B6B7 confirms1.1.4 loaded. Direct
Instant Hotspot still fails. No first UMAC snapshot was present at12:05:33.
FirstFailure/request2: association status0, message1/2, message3 MIC verified,
decryption passed, message4 send function returned0, PTK/GTK installation,
port-valid and link-up callback, then remote deauth reason3/matchmask7. The
metadata port flag is0 because the deauth handler clears it before publishing;
the ordered trace proves it had become valid. Beacon flag remains0.

Therefore this particular failure is after local key-handshake acceptance,
not a demonstrated wrong PMK, BLE establishment failure or UMAC assert. A send
function returning0 does not prove message4 was acknowledged over the air.
Later LastFailure/request15 has reason39/mask1: only destination matches the
current local MAC, while transmitter and BSSID both differ from the current
peer. The receiver nonetheless notified WCL and failed the join. Native logs
show repeated reason3 and foreign reason39 events during the retry sequence.
The genuine matching-peer reason3 still needs hardware investigation; fixing
foreign frames does not erase it or establish the whole hotspot is repaired.

Two bounded functional changes:

1. On this WCL station path, DEAUTH/DISASSOC during AUTH/ASSOC/RUN must match
   the active peer source and BSSID and target the current local MAC or the
   broadcast address. Apply this before duplicate detection or peer callbacks,
   avoiding unrelated frames changing either current RX sequence or join state.
   Do not ignore a valid active peer's teardown. Monitor, scan and unrelated
   management/data traffic retain their existing behavior. Existing management
   protection/decryption checks still execute for accepted peer frames.
2. Keep MAC_CONFIG_CMD ACCEPT_BEACON set after association on WCL. WCL requires
   real associated frames for FirstBeacon, BEACON_INFO and LQM, while the
   current MLD command builder removed explicit beacon forwarding at RUN.
   Firmware beacon filtering is already disabled on this path. Keep actual
   beacon receipt and key authorization as prerequisites; no fabricated beacon,
   immediate fake completion, timeout workaround or security bypass is added.
   Linux v6.12 mld-mac.c is a command-layout reference, not proof that its
   mac80211 beacon-consumer policy is sufficient for Apple's WCL frontend.

The existing opt-in numeric diagnostic also labels unprotected preauthorization
EAPOL TX using only its public8-byte SNAP header and supplicant stage. A slot
stores the diagnostic join cookie and message-context tag. Before the data
queue doorbell the bounded ring records queue/TID; the existing validated
single-frame completion records firmware status (1=success; e.g.0x82=no ACK).
Stale-cookie completions are ignored; slot tags are overwritten on submission
and cleared on reclaim. No additional command, payload retention, log output
or IORegistry writes occur in the TX/RX fast path. Rekeys on authorized ports
and encrypted/non-EAPOL frames are not classified. Absence of a completion
before the terminal snapshot does not prove no subsequent completion occurred.

Tests: actual peer filter integrated before duplicate detection,288 foreign
address mutations, valid local/broadcast reception, non-teardown traffic and
lifecycle preservation; unreadable/short SNAP guards; production TX completion
for2304 status/kind/cookie combinations preserving original TX error handling;
ring/publisher, deferred-peer isolation and strict360-byte decoder ASan/UBSan;
production MAC builder checks associated/unassociated beacon acceptance plus
address ownership;200 coalescing join schedules and boot helper regressions.
All existing PAE security branches/calls/returns remain identical to1.1.3 after
removing scalar diagnostic notes. The input source additionally has the tested
strict peer filter. Full57-source build, fixed SDK/firmware, imports, entry and
signature audits are required before deployment.

Status: hardware result pending reboot. This is a targeted candidate, not
accepted Instant Hotspot, AWDL, AirDrop or Watch lock-screen unlock support.
Preserve HE80, manual switching, Bluetooth/Music pair, SMBIOS and identifiers.
Back up and verify only EFI65EA6FB3-72D2-4697-8E12-8815434C008E on the macOS
physical disk. Preserve1.1.4 rollback and a Wi-Fi-disabled recovery configuration.
Never hotload or automatically reboot. Test once with phone hotspot settings
page closed and Allow Others to Join disabled; collect before manual opening
or additional retries. Read first failure, last failure and success separately.
