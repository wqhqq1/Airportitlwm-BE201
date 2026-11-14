[中文](INSTALL.md) | English

# Driver installation guide

How to add the BE201 Wi-Fi and Bluetooth drivers to an OpenCore EFI, with the injection order and dependencies. Back to the [README](../README.en.md).

## Scope

- **System:** macOS Sequoia 15.2 or later, x86_64.
  - The Wi-Fi driver refuses Darwin below 24.2: 15.0 and 15.1 have a different IO80211 interface.
  - **AWDL (AirDrop, Universal Control and so on):** on by default on 15.7.8 (24G824) and 15.8.3 (24H241).
    - AWDL uses private IO80211Family layouts that were read from 24G824.
    - 24H241 was checked against them function by function, along with every vtable and object size, and matches.
    - On any other build, AWDL is off by default. You can force it with `be201_awdl_vif=1 be201_awdl_auto=1`, at your own risk.
    - After a system update, `research/awdl/abi-diff/run.sh` repeats the check.
  - **Bluetooth patches:** they match the exact code of 24G824's Bluetooth daemon. On other builds they find no match and change nothing, and Bluetooth itself still works.
    - On 24H241 only the device-name patch still matches. The A2DP clock fix, the LE patches and the recent-address routing do not, so they are inactive.
- **Hardware:**
  - Wi-Fi: Intel BE201, PCI `8086:7740`.
  - Bluetooth: Intel BE201, USB `8087:0037`.
- **Boot loader:** OpenCore 1.0.8. Check the config with the 1.0.8 `ocvalidate`.
- **SMBIOS:** this machine uses MacBookPro16,2. MacPro7,1 was used before.
- **Not needed:** root patches (OCLP). The driver uses the system's own IO80211Family and IOSkywalkFamily.

## Getting the drivers

Built drivers are not kept in the repository. Build them as the [README](../README.en.md) describes. After `python3 wifi/kit/package.py`, the first three are in `outputs/BE201-WiFi/`:

| Driver | Version | Where |
|---|---|---|
| `AirportItlwm.kext` | 1.2.25 | `outputs/BE201-WiFi/` |
| `BlueToolFixup.kext` | 2.7.14 | `outputs/BE201-WiFi/` or `build/bluetooth/bluetoolfixup/` |
| `IntelBTPatcher.kext` | 2.5.11 | `outputs/BE201-WiFi/` or `build/bluetooth/intelbtpatcher/` |
| `BE201BluetoothFirmware.kext` | 2.5.3 | `build/bluetooth/firmware/` |

You also need [Lilu](https://github.com/acidanthera/Lilu) 1.7.3 or later (RELEASE build).

Both the Wi-Fi and the Bluetooth firmware are built into the drivers. No separate firmware files are needed.

## Drivers to remove

These drivers share names with this project's drivers, or claim the same device. Remove or disable them in `Kernel/Add`:

| Driver | Why |
|---|---|
| `IntelBluetoothFirmware.kext`, `IntelBluetoothInjector.kext` | `BE201BluetoothFirmware.kext` replaces them. Its driver class is also called `IntelBluetoothFirmware`, so loading both conflicts |
| any other `IntelBTPatcher.kext` | Same name as this project's IntelBTPatcher |
| the `BlueToolFixup.kext` from BrcmPatchRAM | Same bundle id (`as.acidanthera.BlueToolFixup`): keep only this project's copy |
| `itlwm.kext`, any other `AirportItlwm.kext` | They also match `8086:7740`, and a card can have only one Wi-Fi driver |

Leftover `*-recovery.kext` folders in the EFI are harmless as long as `Kernel/Add` does not enable them.

## Dependencies and injection order

OpenCore injects kexts in `Kernel/Add` order, top to bottom, so a dependency must come before the kexts that need it.

| Driver | Depends on | Order |
|---|---|---|
| `Lilu.kext` | nothing | first |
| `IntelBTPatcher.kext` | Lilu, IOUSBHostFamily | after Lilu |
| `BE201BluetoothFirmware.kext` | IOUSBHostFamily (not Lilu) | next to IntelBTPatcher |
| `BlueToolFixup.kext` | Lilu | after Lilu |
| `AirportItlwm.kext` | IO80211Family, IOSkywalkFamily, IONetworkingFamily, IOPCIFamily, corecapture (all built into macOS; not Lilu) | no hard rule; after the Bluetooth drivers is fine |

The order verified on this machine:

```text
Lilu.kext                    (first)
... other kexts ...
IntelBTPatcher.kext
BE201BluetoothFirmware.kext
BlueToolFixup.kext
AirportItlwm.kext
```

Here are the four `Kernel/Add` entries. Note that the executable inside `BE201BluetoothFirmware.kext` is named `IntelBluetoothFirmware`, not after the bundle.

| BundlePath | ExecutablePath | MinKernel | MaxKernel |
|---|---|---|---|
| `IntelBTPatcher.kext` | `Contents/MacOS/IntelBTPatcher` | `24.0.0` | `24.99.99` |
| `BE201BluetoothFirmware.kext` | `Contents/MacOS/IntelBluetoothFirmware` | `24.0.0` | `24.99.99` |
| `BlueToolFixup.kext` | `Contents/MacOS/BlueToolFixup` | `24.0.0` | `24.99.99` |
| `AirportItlwm.kext` | `Contents/MacOS/AirportItlwm` | `24.2.0` | `24.99.99` |

In all four entries, set `Arch` to `x86_64`, `Enabled` to `true` and `PlistPath` to `Contents/Info.plist`.

These are Sequoia (Darwin 24) builds, and they stay out of the way on other kernels even without these ranges: AirportItlwm does not start before 24.2 or outside 24, and Lilu starts BlueToolFixup 2.7.14 and IntelBTPatcher 2.5.11 only on Sequoia. BE201BluetoothFirmware only uploads the firmware, has no Sequoia-specific code, and relies on the `MaxKernel` above.

## Boot arguments: none needed by default

Since Wi-Fi 1.1.88, BlueToolFixup 2.7.12 and IntelBTPatcher 2.5.10, these features are on without any boot argument:

| Feature | Argument it used to need |
|---|---|
| A2DP Bluetooth clock fix (Apple Music and other Bluetooth audio) | `-btlfxa2dpcheck` |
| Chip shown as Intel BE201 in System Information | `-be201identity` |
| Single-advertisement LE backend | `-be201leadv` |
| LE patch around random address updates | `-be201addrpause` |
| Base LE patches shared by BlueToolFixup and IntelBTPatcher | `-be201lebaseline` |
| IntelBTPatcher handles the controller address the native way | `-be201nativeaddr` |
| Read-only diagnostic counters | `-be201btprobe` |
| Connection routing for recent random private addresses | `-be201rparoute` |
| AWDL interface (awdl0) | `be201_awdl_vif=1` |
| AWDL starts by itself at boot (skipped for one boot after a kernel panic) | `be201_awdl_auto=1` |
| Read-only rate and join diagnostics | `be201_tlc_diag=1` |

Leaving the old arguments in `boot-args` does no harm.

**To turn something off:**

| Argument | Effect |
|---|---|
| `-be201btstock` | Turns off all of the BE201 Bluetooth patches above. Naming one switch as well turns that one back on |
| `be201_awdl_vif=0` | Turns AWDL off |
| `be201_awdl_auto=0` | Keeps the AWDL interface but does not start it by itself |
| `be201_tlc_diag=0` | Turns the rate diagnostics off |

**Experiment switches stay off and never start by themselves:**
- ROC and the second channel: `debug.be201_awdl_roc`, `debug.be201_awdl_phy2`. They are turned on only for the duration of `开始ROC实验.command`, which turns them off again at the end.
- The low-latency interface llw0.
- Bluetooth's `-be201privacyprobe` and `-be201peeraddr`.

## Other settings

- **USB map:** Bluetooth sits on an internal USB port, and that port must be in the USB map. This machine uses USBToolBox with UTBDefault.
- **Kernel/Quirks:** `DisableIoMapper` is on here. It has not been tested off.
- **TakeoffDelay:** `Misc/Boot/TakeoffDelay` is `100000` so that Esc or 0 can open the picker on this machine's PS/2 keyboard. It has nothing to do with the drivers.

## Installing

### This machine: the kit installer

`outputs/BE201-WiFi/install.py` is for this machine only. It checks this machine's EFI partition UUID, the Bluetooth firmware driver's hash and the SMBIOS model, and refuses to run anywhere else. It installs three drivers at once: AirportItlwm, BlueToolFixup and IntelBTPatcher.

1. Mount the EFI partition on the macOS disk.
2. Run the check. It changes nothing:

   ```bash
   python3 outputs/BE201-WiFi/install.py --check
   ```

3. Install. The whole EFI is backed up first, and the arguments that are no longer needed are removed from `boot-args`:

   ```bash
   python3 outputs/BE201-WiFi/install.py --install
   ```

4. Reboot.

The kit's `使用与回退.md` explains how to roll back.

### Other machines: by hand

1. Back up the whole EFI folder.
2. Copy the four drivers and Lilu to `EFI/OC/Kexts/`.
3. Add the `Kernel/Add` entries in the order above, and remove the conflicting drivers.
4. Check `config.plist` with OpenCore 1.0.8's `ocvalidate` and make sure it reports no errors.
5. Reboot.

## Apple Watch unlock

This Wi-Fi driver has no FTM ranging, and macOS measures the distance before it unlocks, so the system has to skip ranging.

Run this as your own user (not with sudo), or double-click `Apple Watch跳过测距.command` in the kit:

```bash
python3 outputs/BE201-WiFi/install.py --watch-unlock
```

It runs:

```bash
defaults write com.apple.sharingd phoneAutoUnlockSkipRanging -bool true
```

```bash
killall sharingd
```

Without ranging, only the Bluetooth signal-strength check remains. The Mac may unlock with the watch a little farther away, which is less secure.

To turn ranging back on:

```bash
python3 outputs/BE201-WiFi/install.py --watch-unlock-undo
```

## Checking the result

```bash
kmutil showloaded --list-only | grep -E 'AirportItlwm|BlueToolFixup|IntelBTPatcher|BE201BluetoothFirmware|Lilu'
```

- All five drivers should be loaded, at the versions above.
- System Information → Bluetooth shows the chip as Intel BE201.
- On 24G824 and 24H241, `ifconfig awdl0` shows the AWDL interface.
- `ioreg -l | grep ItlwmAwdlLayoutVerified` shows `Yes` when the running kernel is the verified one, which is why AWDL is on by default.

If the Wi-Fi driver did not load, read the newest `opencore-*.txt` on the EFI root first. A RELEASE OpenCore writes no log: switch to the DEBUG build for a while and set `Misc/Debug/Target` to `67`.

OpenCore once skipped 1.1.54 because of its segment layout. Packaging now runs `oc_layout_check.py`, so that cannot happen again.
