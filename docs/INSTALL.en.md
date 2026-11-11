[中文](INSTALL.md) | English

# Driver installation guide

How to add the BE201 Wi-Fi and Bluetooth drivers to an OpenCore EFI, with the injection order and dependencies. Back to the [README](../README.en.md).

## Scope

- **System:** macOS Sequoia 15.7.8 (24G824), x86_64, only.
  - The Bluetooth patches match the exact code of 24G824's Bluetooth daemon and do nothing on other builds.
  - The Wi-Fi driver is checked against 24G824's kernel interfaces.
- **Hardware:**
  - Wi-Fi: Intel BE201, PCI `8086:7740`.
  - Bluetooth: Intel BE201, USB `8087:0037`.
- **Boot loader:** OpenCore 1.0.8. Check the config with the 1.0.8 `ocvalidate`.
- **SMBIOS:** this machine uses MacBookPro16,2. MacPro7,1 was used before.
- **Not needed:** root patches (OCLP). The driver uses the system's own IO80211Family and IOSkywalkFamily.

## Getting the drivers

Built drivers are not kept in the repository. Build them as the [README](../README.en.md) describes:

| Driver | Version | Build output |
|---|---|---|
| `AirportItlwm.kext` | 1.1.87 | `outputs/BE201-WiFi/`, after `python3 wifi/kit/package.py` |
| `BE201BluetoothFirmware.kext` | 2.5.3 | `build/bluetooth/firmware/` |
| `BlueToolFixup.kext` | 2.7.11 | `build/bluetooth/bluetoolfixup/` |
| `IntelBTPatcher.kext` | 2.5.9 | `build/bluetooth/intelbtpatcher/` |

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

## Boot arguments

Add these to `NVRAM/Add/7C436110-AB2A-4BBB-A880-FE41995C9F82/boot-args` and keep your existing ones.

**Bluetooth** (this machine uses the whole set):

| Argument | What it does |
|---|---|
| `-btlfxa2dpcheck` | Fixes the A2DP Bluetooth clock check. Apple Music and other Bluetooth audio need it |
| `-be201identity` | Shows the chip as Intel BE201 in System Information. The numeric identity is unchanged |
| `-be201leadv` | Makes the system use its single-advertisement LE backend |
| `-be201addrpause` | LE patch around random address updates. Needs `-be201leadv` |
| `-be201lebaseline` | Base LE patches shared by BlueToolFixup and IntelBTPatcher |
| `-be201nativeaddr` | IntelBTPatcher handles the controller address the native way |
| `-be201btprobe` | Read-only diagnostic counters. `-be201rparoute` needs it |
| `-be201rparoute` | Resolves recent random private addresses through the identities the system has verified, and routes connections by them (2.7.11). Needs `-be201btprobe` |

**Wi-Fi:**

| Argument | What it does |
|---|---|
| `be201_awdl_vif=1` | Provides the AWDL interface (awdl0). AirDrop, Universal Control and the other Continuity features need it |
| `be201_awdl_auto=1` | Starts AWDL by itself after boot. It is skipped for one boot after a kernel panic |
| `be201_tlc_diag=1` | Read-only rate and join diagnostics. This project's installer checks for it |

Without the two `be201_awdl_*` arguments, Wi-Fi still works, but there is no AWDL.

## Other settings

- **USB map:** Bluetooth sits on an internal USB port, and that port must be in the USB map. This machine uses USBToolBox with UTBDefault.
- **Kernel/Quirks:** `DisableIoMapper` is on here. It has not been tested off.
- **TakeoffDelay:** `Misc/Boot/TakeoffDelay` is `100000` so that Esc or 0 can open the picker on this machine's PS/2 keyboard. It has nothing to do with the drivers.

## Installing

### This machine: the kit installer

`outputs/BE201-WiFi/install.py` is for this machine only. It checks this machine's EFI partition UUID, Bluetooth driver hashes and SMBIOS model, and refuses to run anywhere else.

1. Mount the EFI partition on the macOS disk.
2. Run the check. It changes nothing:

   ```bash
   python3 outputs/BE201-WiFi/install.py --check
   ```

3. Install. The whole EFI is backed up first:

   ```bash
   python3 outputs/BE201-WiFi/install.py --install
   ```

4. Reboot.

The kit's `使用与回退.md` explains how to roll back.

### Other machines: by hand

1. Back up the whole EFI folder.
2. Copy the four drivers and Lilu to `EFI/OC/Kexts/`.
3. Add the `Kernel/Add` entries in the order above, and remove the conflicting drivers.
4. Add the boot arguments.
5. Check `config.plist` with OpenCore 1.0.8's `ocvalidate` and make sure it reports no errors.
6. Reboot. If NVRAM already holds an older `boot-args`, make sure `NVRAM/Delete` lists `boot-args`, or reset NVRAM once.

## Checking the result

```bash
kmutil showloaded --list-only | grep -E 'AirportItlwm|BlueToolFixup|IntelBTPatcher|BE201BluetoothFirmware|Lilu'
```

- All five drivers should be loaded, at the versions above.
- System Information → Bluetooth shows the chip as Intel BE201.
- With the AWDL arguments, `ifconfig awdl0` shows the interface.

If the Wi-Fi driver did not load, read the newest `opencore-*.txt` on the EFI root first. A RELEASE OpenCore writes no log: switch to the DEBUG build for a while and set `Misc/Debug/Target` to `67`.

OpenCore once skipped 1.1.54 because of its segment layout. Packaging now runs `oc_layout_check.py`, so that cannot happen again.
