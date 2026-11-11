# AirportItlwm 1.1.55: 1.1.54 with a kext layout OpenCore accepts

## 1.1.54 did not load, boot 2026-11-08 00:08

Wi-Fi was absent: no en1, no AirportItlwm, and IO80211Family never initialized. OpenCore's file log (opencore-2026-11-07-160735.txt on the EFI) had:

`OC: Failed to fit 64-bit kext AirportItlwm.kext (...) - Invalid Parameter`

The cause is a page gap in the file before `__LINKEDIT`:
- `__DATA`'s file content ended exactly on a page, at 0x156000.
- ld (ld-prime and ld-classic both) then placed `__LINKEDIT` at file offset 0x157000. Its VM address stayed at 0x18f000.
- OpenCore's `PrelinkedReserveKextSize` uses `MachoGetExpandedImageSize`. That requires each segment's vmaddr to equal its fileoff plus the zero-fill of the segments before it. Here that is 0x157000 + 0x39000 = 0x190000, not 0x18f000. The size comes out 0, so the kext is never injected.

1.1.52 and 1.1.53 pass the same rule. Their `__DATA` content does not end on a page.

## Change

- **`scripts/oc_layout_check.py`:** checks OpenCore's segment rule (and filesize <= vmsize) on a Mach-O.
- **Build script:** links once and runs the check. If the check fails, it relinks with a 64-byte initialized `__DATA,__data` pad (`be201_layout_pad`), which moves the end of `__DATA` off the page, and checks again. The build fails if the layout is still bad.
  - With the pad, `__DATA` filesize is 0xC000 and `__LINKEDIT` sits at fileoff 0x157000 with vmaddr 0x18f000.
  - The import count is unchanged at 1114.
- **Packager:** also runs the check on the signed binary.
- **Driver source:** the same as 1.1.54 (see BE201-AWDL-VIF-1.1.54.md). The version string and the build default are now 1.1.55.

## Deployment

1. `install.py --restore` from the 1.1.54 kit returns the EFI to its state before 1.1.54: the active kext becomes 1.1.53 again and the old config comes back.
2. 1.1.55 then installs over 1.1.53 with prefix awdlfit, so its recovery kext is 1.1.53, which loads.

The 1.1.54 recovery kext and configs (prefix awdlspeed) stay on the EFI, untouched.
