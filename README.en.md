[中文](README.md) | English

# BE201 Hackintosh wireless drivers: Wi-Fi and Bluetooth

Drivers for the Intel BE201 (Wi-Fi PCI 8086:7740, Bluetooth USB 8087:0037) on macOS Sequoia: 15.2 or later, verified on 15.7.8 (24G824).

- **Wi-Fi:** the goal is native AWDL and Continuity (AirDrop, Universal Control, Handoff and so on). The scope ends at ax/80 MHz: no be, 160 MHz, 6 GHz or MLO.
- **Bluetooth:** firmware loading and BE201 patches in BlueToolFixup and IntelBTPatcher, including the Apple Music fix and recent-address routing.

**Installing:** see the [installation guide](docs/INSTALL.en.md) for the injection order, dependencies, drivers to remove and optional boot arguments. Since Wi-Fi 1.1.88, BlueToolFixup 2.7.12 and IntelBTPatcher 2.5.10, no boot arguments need to be added by hand.

## Status

All results below were measured on this machine: macOS 15.7.8 24G824, Wi-Fi driver 1.1.87, Bluetooth 2.5.3 / 2.7.11 / 2.5.9. 1.1.88 / 2.7.12 / 2.5.10 only turn these features on by default; the features themselves are unchanged. Speeds depend heavily on the channel and the surroundings.

### Working

| Feature | Notes |
|---|---|
| Wi-Fi | 2.4 and 5 GHz, 802.11ax, up to 80 MHz. Open and encrypted networks, switching between networks |
| Personal Hotspot / Instant Hotspot | Joins an iPhone hotspot. The first join occasionally times out; trying again works |
| AWDL | awdl0 starts by itself at boot, with nothing to do by hand |
| AirDrop | Both directions. With the Mac and the phone on the same 5 GHz channel: about 27–33 MB/s Mac to phone and about 39 MB/s phone to Mac, and a 4 GB transfer runs without stalling |
| AirDrop while joined to a router on another channel | Works, but only at about 3 MB/s: transfers wait for the phone to visit the Mac's channel |
| Universal Control | Works |
| Apple Watch unlock | Works after running `install.py --watch-unlock` once to skip ranging (see "Not possible yet" and the [installation guide](docs/INSTALL.en.md#apple-watch-unlock)) |
| Bluetooth | Firmware upload, Classic and Low Energy, Bluetooth audio |
| Apple Music and other Bluetooth audio | Fixed (`-btlfxa2dpcheck`) |
| Handoff, Universal Clipboard | Confirmed working, but not on every boot (see "In progress") |

### In progress

| Feature | State |
|---|---|
| Full-speed AirDrop on a second channel while joined to a router | Uses firmware remain-on-channel (ROC) to receive and send on the phone's channel. 1.1.86 exchanged frames with the phone on channel 149 for the first time, but hit firmware errors. With the P2P ROC type, 1.1.88 hit firmware errors when the link moved to channel 149. 1.1.89 keeps ROCs and link moves apart and waits for a test |
| Continuity Camera, Sidecar | The low-latency interface llw0 exists, UMI is answered and RTG goes active, but no picture yet. Paused for now |
| Handoff reliability | Works on some boots and not on others; the cause is still open, so this is only being watched. The boots checked since AirPlay Receiver was turned off all worked |

### Not possible yet

| Feature | Why |
|---|---|
| Wi-Fi 7 (be), 160 MHz, 6 GHz, MLO | Outside this project's scope |
| Two channels at once (second PHY) | This firmware does not transmit from a link on another PHY. That was tested and the approach is closed; ROC is the replacement |
| NAN | This firmware (-92) has no NAN capability |
| Ranging for Apple Watch unlock | The driver has no FTM ranging, so ranging can only be skipped |
| iPhone Mirroring | Fails in sharingd's authentication step. Most likely because there is no T2 chip, not Wi-Fi, but that is not proven |
| Sequoia 15.0, 15.1 and older systems | The Wi-Fi driver needs the IO80211 interface introduced in 15.2 |
| AWDL and the Bluetooth patches on Sequoia builds other than 24G824 | AWDL relies on private layouts read from 24G824, so it is off by default; it can be forced on, untested. The Bluetooth patches find no matching code there and do nothing, while Bluetooth itself still works |

## Layout

| Path | Contents |
|---|---|
| `wifi/airportbz` | Wi-Fi driver AirportItlwm, forked from AirportBZ with the upstream history kept |
| `wifi/kit` | Wi-Fi build, test, packaging, install and experiment tools, shared by every version |
| `bluetooth/firmware` | BE201BluetoothFirmware: uploads the Bluetooth firmware. The Intel firmware is in `fw/` |
| `bluetooth/bluetoolfixup` | BlueToolFixup: BE201 patches for the system Bluetooth daemon |
| `bluetooth/intelbtpatcher` | IntelBTPatcher: patches for controller commands and events |
| `bluetooth/rpa-payload` | Generates `AuthenticatedRPAPatch.hpp` for BlueToolFixup |
| `bluetooth/release.json` | Version, note, fixed build date and installed binary hash of each Bluetooth driver |
| `docs/wifi` | Technical notes for each Wi-Fi version: what changed, test results, reasoning |
| `docs/BE201-CURRENT.md` | Running log of test results and conclusions |
| `research` | Research scripts and reference code for AWDL, the Intel firmware interface and the Bluetooth stack |

## Dependencies

Dependencies live in `deps/`. They are not committed and stay on the local machine:

| Path | Used for |
|---|---|
| `deps/MacKernelSDK` | Wi-Fi build. Packaging checks its hash (`wifi/kit/sdk-manifest.sha256`) |
| `deps/MacKernelSDK-3f75008` | Bluetooth build (acidanthera MacKernelSDK 3f75008) |
| `deps/Lilu` | Bluetooth build (Lilu 1.7.3 source, for `Library/plugin_start.cpp`) |
| `deps/ocvalidate` | OpenCore 1.0.8 config checker |
| `deps/system-symbols-24G824.txt` | 24G824 kernel exports, to check the driver imports nothing missing |
| `deps/python` | capstone 5.0.9 (for `rpa-payload`) |

Build output goes to `build/wifi` and `build/bluetooth`. Reference repositories live in `reference/`.

## Wi-Fi workflow

The version and the driver comment written into the config are in [`wifi/kit/release.json`](wifi/kit/release.json). Run these from the repository root.

1. Change the source, and write this version's note in `docs/wifi/` as `BE201-AWDL-VIF-<version>.md`.
2. Update `version` and `comment` in `release.json`.
3. Build:

   ```bash
   bash wifi/kit/build.sh
   ```

4. Run the 24 offline test suites:

   ```bash
   python3 wifi/kit/run_checks.py
   ```

5. Package. The kit always goes to `outputs/BE201-WiFi/`:

   ```bash
   python3 wifi/kit/package.py
   ```

   When the version changes, the kit's previous driver moves to `outputs/BE201-WiFi/上一版/` ("previous version"), and the installer expects exactly that driver in the EFI. EFI backups, deployment records and experiment logs stay where they are.
6. Mount the EFI, then run `install.py --check` and `install.py --install` in `outputs/BE201-WiFi/`. The kit's `使用与回退.md` covers usage and rollback.

## Bluetooth build

```bash
python3 bluetooth/build.py
```

- **Output:** each driver is built into `build/bluetooth/<folder>/`.
- **Check against the EFI:** each result is compared with the binary in the EFI. While the versions are unchanged, the builds are byte-identical to it.
- **New release:** change `version`, `note` and `source_date_epoch` in `release.json` together.
- **Firmware driver version:** set in `bluetooth/firmware/Info.plist`.

## Installer constraints

The [installation guide](docs/INSTALL.en.md) has the full steps. This project's own installer also keeps to these rules:

- It writes only to the EFI partition on the macOS disk.
- Another project on this machine (an audio driver) edits `config.plist` too. The installer builds the new config from the config as it is at install time, and changes only three things: the driver comments, this project's boot arguments (the now-default ones are removed) and TakeoffDelay. It compares the file again just before writing, and stops if anything changed meanwhile.
- The kit installs AirportItlwm, BlueToolFixup and IntelBTPatcher together and keeps the previous copy of each for recovery. The Bluetooth firmware driver, the SMBIOS model and OpenCore itself stay unchanged, and the installer checks each of them.

## Not in the repository

These stay on the local machine and are excluded by `.gitignore`:

- **`outputs/`:** deployable kits. They hold kexts, EFI backups, configs with this machine's serial numbers and runtime logs.
- **`deps/`, `build/`, `reference/`:** dependencies, build output and reference repositories.
- **Test results:** `wifi/kit/checks.json` and `wifi/kit/tests/`.
- **Test records, captures, plists, json and generated patch pages in the Bluetooth and research folders:** they can contain device addresses, account details or Apple's code.

Peer MAC addresses and IDS handles in the notes have been replaced with placeholders. The `runtime-*.json`, `roc-*.txt` and phone logs written by the experiment tools can contain device, network and account details: never commit or upload them.

## Licences

- **Wi-Fi driver:** the AirportBZ / itlwm licence, see `wifi/airportbz/LICENSE`.
- **Wi-Fi firmware:** see `wifi/airportbz/LICENCE.bz-firmware`.
- **Bluetooth drivers:** the `LICENSE` in each folder.
- **Intel Bluetooth firmware:** see `bluetooth/firmware/fw/LICENCE.ibt_firmware`.
