# AirportItlwm 1.1.88 with BlueToolFixup 2.7.12 and IntelBTPatcher 2.5.10: switches on by default

## Why

- **No new ROC result:** the 1.1.87 ROC test has not run yet. No `roc-*.txt` exists since the 17:01 boot, and the ROC code is unchanged. The test is still to be done on this version: 开始ROC实验.command.
- **The user asked for three things:**
  - The Bluetooth and Wi-Fi boot arguments this machine uses become defaults, but the ROC experiment must not start by itself.
  - The installer gains the Apple Watch skip-ranging step.
  - The version limit is widened to all of macOS Sequoia.

## Wi-Fi 1.1.88

- **`ItlDefaultOnFlag(name, fallback)`:** a switch is on unless its boot argument is present and not 1. `be201_tlc_diag=0` turns the rate and join diagnostics off.
- **AWDL default only on the verified kernel:** `ItlAwdlFlag` gates `be201_awdl_vif` and `be201_awdl_auto`.
  - They are on by default only when the kernel version string contains `xnu-11417.140.69.711.44~1/RELEASE_X86_64`, the 24G824 kernel.
  - The AWDL path relies on private IO80211Family layouts read from that build: ivars, vtable slots and event numbers. Elsewhere it stays off unless the argument is `=1`.
  - `ItlwmAwdlLayoutVerified` shows the result.
  - `kern.osversion` was not used: it is empty when the driver starts.
- **Unchanged:**
  - `startAWDLAuto` still leaves `debug.be201_awdl_roc`, `phy2`, `phy2_te`, `amsdu` and `llw` at 0.
  - `be201_awdl_if` and `be201_diag` stay opt-in.
- **Supported systems:** the driver still refuses Darwin below 24.2. Sequoia 15.0 and 15.1 have a different IO80211 interface.
- **New import:** `_version`, a kernel export.

## Bluetooth

- **`be201Switch(name)` in `BE201Defaults.hpp`:** on unless `-be201btstock` is set. Naming a switch next to `-be201btstock` turns that one back on.
- **Default on:** `-btlfxa2dpcheck`, `-be201identity`, `-be201leadv`, `-be201addrpause`, `-be201lebaseline`, `-be201nativeaddr`, `-be201btprobe` and `-be201rparoute`.
- **Still opt-in:** `-be201privacyprobe`, `-be201peeraddr` and `-btlfx*`.
- **Other Sequoia builds:** the patches remain exact byte matches against 24G824's bluetoothd, so on another build they find nothing and change nothing.
- **Versions:** BlueToolFixup 2.7.12 and IntelBTPatcher 2.5.10. BE201BluetoothFirmware stays 2.5.3.

## Installer

- **One kit, three drivers:** it now installs AirportItlwm, BlueToolFixup and IntelBTPatcher.
  - Each driver keeps one previous copy, `<name>-recovery.kext`.
  - The kit's `kit.json` names the expected old binaries.
  - BE201BluetoothFirmware must be unchanged.
- **Boot arguments:** the eleven now-default arguments are removed from `boot-args`. Every other argument, including the audio session's `nmhdavol=1`, stays in place.
- **Rollback configs:**

  | Config | What it does |
  |---|---|
  | `rollback` | The old config and arguments, with the three previous drivers |
  | `off` | Adds `be201_awdl_vif=0` |
  | `btstock` | Adds `-be201btstock` |
  | `WiFi-disabled` | Disables the Wi-Fi driver |
  | `macpro` | Changes the model to MacPro7,1 |

  `rxonly` and `capability` are gone.
- **Systems:** any macOS 15.2 or later Sequoia is accepted. On a build other than 24G824 the installer says AWDL stays off by default.
- **Apple Watch:**
  - `install.py --watch-unlock` writes `phoneAutoUnlockSkipRanging` for sharingd and restarts it. It runs as the user. `--watch-unlock-undo` reverses it.
  - The kit adds `Apple Watch跳过测距.command`.
  - `--check` and `--install` print a reminder when the setting is missing.
- **`--restore`:** puts back all drivers of the last install.

## Tests

- **New `test-default-switches`:**
  - The helpers: absent, `=0`, `=2` and `=1`, on the verified and on another kernel string.
  - Every reader goes through them.
  - Auto start leaves ROC, phy2 and llw0 off.
  - Bluetooth: the eight switches use `be201Switch`, `-be201btstock` turns them off, and the experimental switches still need their argument.
- **`test-awdl-vif`:** mocks the new helpers.
- **Result:** all 25 suites pass.
- **Installer:** simulated on a copy of the EFI backup. Only the three row comments and `boot-args` changed, the recovery copies and rollback config are right, and `--restore` brings everything back.
