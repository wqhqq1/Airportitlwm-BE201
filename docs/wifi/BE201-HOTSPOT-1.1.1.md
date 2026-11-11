# BE201 1.1.1: uncached joins and first-fault TLC evidence

Target: PCI 8086:7740, Sequoia 15.7.8 / 24G824, API92 firmware and PNVM
unchanged. HE80 support remains enabled by the existing configuration.

The current Bluetooth 2.7.11 route can authenticate to the phone and activate
its hotspot. The subsequent Wi-Fi join fails. Repeated hardware UMAC asserts
reported a last-host-command header with group 5/id 0x0f (TLC_MNG_CONFIG_CMD).
This is correlation, not a decoded proprietary assertion or a proven cause.

## Functional correction

An uncached WCL join set the desired SSID but only replaced the WCL scan
channel bitmap, inheriting a previous scan's SSID and active/passive mode.
The firmware scan builder prefers those WCL fields when scan_requested is
set. It now constructs a fresh active directed scan for the join, clears
stale channel restrictions, and uses the requested valid channel or all
regulatory-allowed channels. Cached joins and rate settings are unchanged.

Most failures in the previous numeric trace used cached joins, so this fix
alone is not expected to explain all observed hotspot failures.

## Default-off diagnostic

Boot argument `be201_tlc_diag=1` enables a fixed eight-record ring (548 bytes
including header) on the serialized command queue path. It records only
28-byte TLC v4 commands at the final queue submission, retaining the real
wire header/sequence, generation, net80211 state and node rate capabilities.
It captures no other command, key, network name, MAC address or packet.
No allocation, logging or IORegistry publication occurs during capture.

The first valid UMAC error freezes and publishes `ItlwmTlcFirstFaultTrace`
on the PCI provider. Later retries cannot overwrite it. An absent trace
means no captured UMAC error; it does not imply a successful hotspot join.
`scripts/tlc_trace.py` strictly decodes this fixed public-capability schema.
No rate-policy, LDPC, HE or firmware timeout hypothesis is applied yet.

## Verification and limits

`scripts/test-hotspot-join.py` tests the production scan helper and trace
with ASan/UBSan: 384 stale-scan replacement cases, bounds and guard pages,
ABI filtering, ring rollover, command sequence/generation and immutable
first fault. Existing HE firmware/IE/PPE tests and Sequoia ABI tests also pass.
All 57 Sequoia compilation units link. The import set matches the known-good
1.1.0 binary (954 imports); seven constructors and destructors remain.

This version requires a reboot. Do not hotload it or reboot automatically.
Test normal ax80 networking, phone/iPad Handoff and text clipboard first;
then test one automatic hotspot activation without manually opening it.
Save diagnostic output before further attempts. Actual association and
hotspot routing require hardware validation, and are not claimed repaired.

Deployment must back up and hash the complete same-disk EFI UUID
65EA6FB3-72D2-4697-8E12-8815434C008E, preserve Bluetooth, SMBIOS, identifiers,
other drivers and boot arguments, and retain old Wi-Fi/disabled recovery
configurations. Never modify NVRAM, account keys, pairings or root volumes
as part of this installation. The new diagnostic boot argument in config
does not directly write live NVRAM.
