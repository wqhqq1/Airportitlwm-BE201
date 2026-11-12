# AirportItlwm 1.1.93: AWDL on by default on macOS 15.8.3 (24H241)

The user updated Sequoia from 15.7.8 (24G824) to 15.8.3 (24H241) themselves. On the first boot, 1.1.92 loaded with `ItlwmAwdlLayoutVerified` No, as designed. AWDL was off and there was no `awdl0`.

This version adds 24H241 to the verified kernels. Nothing else in the driver changes: the ROC test, with mode 4's host hold from 1.1.92, stays off by default.

## The check

The baseline is `deps/kc-24G824/`: the 24G824 Boot kernel collection and kernel, saved before the update. It was compared with this machine's 24H241 collection. The scripts are in `research/awdl/abi-diff/` (`run.sh`).

- **New kernel:** `xnu-11417.140.69.713.47~2/RELEASE_X86_64`. It still reports Darwin 24.6.0.
- **Fileset UUIDs:**
  - IOSkywalkFamily, IONetworkingFamily and corecapture keep the same UUIDs.
  - IO80211Family has a new UUID (a763ca0b → 88c53c3e), and its `__TEXT` grew by 4 KiB.
  - IOPCIFamily, IOUSBHostFamily and the kernel are new builds too.
- **IO80211Family, function by function** (normalised disassembly: call and data targets by symbol, local branches by index, member offsets and constants kept):
  - 14,131 functions are equal, 575 differ, 2 are gone and 3 are new. The removed and added ones are NAN attribute validators.
  - **333 differ only in the source line numbers** passed to logging.
    - The deltas are constant per file: +4 throughout IO80211AWDLPeerManager.cpp, +3 in IO80211Peer, +14 and more in the NAN files.
    - This includes 272 IO80211AWDLPeerManager methods, all with the same member offsets.
  - **The remaining 128 are:**
    - NAN parsers, data paths and radio resources.
    - Renamed allocation-site tags (`kalloc_type_view_*`).
    - String and table data that the disassembler mistook for code.
    - Four in AWDL-related code:
      - `IO80211AWDLPeerManager::reportDataPathEvents` gained a divide-by-zero guard and a cap of 15 on one value.
      - `IO80211AWDLPeer::updateAwdlChanSeq` and `tlvCheckBounds` gained bounds checks.
      - `IO80211PeerManager::setMaxNSS` lost an alignment `nop`.
      - The member offsets used in these functions are the same sets (184, 51 and 8 of them).
  - No changed immediate below 0x800 belongs to AWDL code, so an event number shifted by a few would have shown.
- **Vtables:** all 418 IO80211Family vtables are equal slot by slot, with every slot resolving to a named function. That includes IO80211AWDLProtocol (566 slots), IO80211SkywalkInterface (463), IO80211VirtualInterface (503) and IO80211AWDLPeerManager (101).
- **Object sizes:** all 166 static initializers pass the same immediates to OSMetaClass.
- **Imports:** all 1,116 imports of AirportItlwm resolve in the 24H241 kernel and Boot kernel collection. So do those of IntelBTPatcher and BE201BluetoothFirmware. BlueToolFixup's only unresolved import, `BaseDeviceInfo::get`, comes from Lilu, as on 24G824.

**Conclusion:** the private layouts the AWDL path depends on are unchanged in 24H241.

## Change

- **`ItlAwdlLayoutVerified`** now takes a list of verified kernels: 24G824 and `xnu-11417.140.69.713.47~2/RELEASE_X86_64` (24H241).
  - On these, `be201_awdl_vif` and `be201_awdl_auto` are on unless set to 0. Elsewhere they still need `=1`.
- **The installer** names both builds as verified (`VERIFIED_BUILDS`).
- **Docs:** the README, the install guide and the kit's notes name both builds.

## Bluetooth on 24H241 (not changed here)

`bluetoothd` is a new build (Nov 5). Of the BlueToolFixup patches, only the device-name patch still matches (NamePatchHits 1). These are all 0, so none of them is active on 24H241:
- the A2DP clock fix (ClockPatchHits)
- the LE baseline (LEBaselinePatchHits)
- the address pause (AddressPausePatchHits)
- the recent-address routing (RPAPatchedMask)

Bluetooth itself works. Porting these patches is a Bluetooth driver change and waits for the user.

## Tests

- **test-default-switches:**
  - The 24H241 kernel string is verified, and `=0` still turns AWDL off there.
  - A different build suffix or a truncated string is not verified.
- **Result:** all 25 suites pass.
