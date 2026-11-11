# BE201 1.1.2: ordered network transitions

Target remains 8086:7740 / Sequoia 24G824 / API92 / HE80.

## Hardware observations

1.1.1 UUID866A633D-A121-35F5-8F64-8EED17E9E45F loaded after reboot.
The phone's BLE hotspot activation succeeded at 10:25:05.453; Wi-Fi reported
its first association failure at 10:25:05.641, approximately 187 ms later.
The internal retry then saw driver unavailable. This is not a normal join
timeout. Manual network switching also fails first and succeeds on retry.

The first frozen assert is 0x20003215/data1=300/last command0x170309,
generation1: group3/id9 LINK_CONFIG, not a captured TLC command. Its exact
time and LINK payload were not retained in 1.1.1, so do not assign this
assert to a particular user action or decode its proprietary error ID.
By 10:52 firmware error count rose5->11, ready events15->33, offline join
aborts7->16. Rate policy is unchanged because TLC causation is unproven.

## Functional corrections

* WCL leave queues INIT asynchronously. Previously startWCLJoin immediately
  copied the new BSS and queued AUTH. A coalescing HAL task can replace INIT,
  and the teardown can read the next peer's channels/rate/security state.
* Keep one accepted request, preserve the departing BSS/BSSID, yield the
  workloop, and resume only after actual INIT cleanup has finished and the
  driver is running. A 20 ms timer observes completion; the existing bounded
  30 s wait fails if cleanup never finishes. Firmware command timeouts are
  unchanged. A visible INIT alone is insufficient while its callback runs.
* The HAL rejects delayed non-INIT state requests while explicit INIT is
  pending. Completion or firmware reset clears this marker. Old peer
  association/deauth/beacon/link-up events cannot finish the queued join.
* WCL may already have changed the BSD/private address. Existing firmware
  MAC/LINK contexts retain their successful ADD address through MODIFY and
  teardown, then successful REMOVE clears it. New ADD takes the new address.
  Failure/reset paths cannot retain a falsely successful context.

Private state fields are internal to this fully compiled driver; no native
Sequoia vtable or imported interface is added.

## Diagnostics and verification

Existing numeric boot option `be201_tlc_diag=1` is retained. Default remains
off when no option is provided. Schema2 keeps the same548byte, eight-record
first-fault snapshot, adding LINKv2's seven numeric fields: action, link_id,
mac_id, phy_id, modify_mask, active, listen_lmac. No link/BSSID address bytes
are copied. TLCv4 remains limited to28byte capability payloads. The reader
also accepts the prior schema1 hardware snapshot. Capture has no allocation,
logging or IORegistry writes; only the first UMAC error publishes it.

Counters distinguish INIT deferrals, completed cleanups and wait failures.
These are not connection-success counters.

Production methods are exercised with ASan/UBSan under a coalescing HAL,
early READY and visible-INIT-before-cleanup schedules, delayed peer events,
cancel/offline/deadline/start-error cases, and actual MACv2 builder errors.
384 cold-scan cases and the fixed trace's guard-page/ring/filter tests pass;
HE/PPE/parser and BZ startup checks pass. Reboot/RF tests remain necessary.

## Continuity boundaries

User reports Handoff works with Wi-Fi off but disappears after Wi-Fi on,
while Watch admin approvals and BLE hotspot activation keep working.
Logs contain repeated _needsAWDL events and infrastructure Rapport links;
this does not establish which request or peer caused Handoff failure.
The selected10:32–10:54 window has no explicit AWDL-info failure tied to
that Handoff attempt. Method names containing allowDuringAWDLRealTimeMode
or error: are not AWDL session failure evidence. Missing logs are not proof
AWDL is uninvolved. Fix infrastructure transition faults before attributing
all failures to radio coexistence or AWDL, and do not patch Bluetooth here.

Watch lockscreen failure was independently proven at10:11:50 with Code103
AWDL info retrieval failed. Watch admin approval is a separate successful
path. This release does not implement AWDL, ranging, AirDrop or lockscreen
Auto Unlock and does not claim to fix Wi-Fi-dependent Handoff disappearance.

Deploy only to the authorized same-disk EFI, preserving Bluetooth2.7.11,
IntelBTPatcher2.5.9, MacPro7,1 and identifiers. Keep full EFI backup, prior
1.1.1 Wi-Fi and disabled-Wi-Fi recovery configs. No automatic reboot/hotload.
