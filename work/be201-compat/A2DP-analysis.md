# macOS Intel A2DP Fast-Connect Patch Process

This document records the reverse-engineering and patching process to fix the "Connected but No Sound" issue when third-party Bluetooth controllers (e.g. Intel) connect to newer Apple H1/H2 chip headphones (e.g. AirPods Pro 2).

---

## 1. Symptoms and Root Cause Analysis
**Symptom**: When using a non-native (third-party) Bluetooth adapter to connect to wireless headphones with Apple W1/H1/H2 chips, Bluetooth successfully pairs and establishes an initial connection, but no A2DP audio stream is created. This is the infamous "Connected but No Sound" issue in the Hackintosh community.
> See: [IntelBluetoothFirmware Issue #462](https://github.com/OpenIntelWireless/IntelBluetoothFirmware/issues/462)

The system log repeatedly outputs:
> `Failed to read BT clock`

**Root Cause**:
The native macOS `bluetoothd` daemon relies on the underlying Bluetooth chip to provide clock synchronization data (HCI_Read_Clock). If a third-party controller does not support or fails to return this clock data in time, the validation logic treats it as a failure, logging an error via `__os_log_error_impl` and subsequently aborting the A2DP audio pipeline setup.

---

## 2. Patch Logic: Single-Gate Bypass
Through disassembly and dynamic analysis of `bluetoothd`:
We identified the key blocking point that causes devices like AirPods to have no audio after connecting — a conditional jump check that follows the HCI_Read_Clock call based on its return value.

**Bypass Logic**:
We simply replace the conditional jump `test r14d, r14d; je <os_log_block>` with an unconditional path `xor r14d, r14d; jmp`.
This single-instruction short-circuit not only successfully restores the audio stream but also maintains stable kernel flow with minimal interference to other code paths.

---

## 3. Analysis Tooling: Automated Scripts
Since each macOS update may shift memory addresses, we developed a dedicated `find_gate.py` analysis script to quickly locate the target instructions in `bluetoothd`:

1. Uses the error string `"Failed to read BT clock"` as a signature anchor.
2. Invokes `otool -tvV` to disassemble `bluetoothd`.
3. Traces the stack space and upstream functions referencing that string.
4. Filters and locates the branch logic (conditional jump) calling the error block.
5. Extracts the `test` instruction and its offset preceding the conditional jump.

---

## 4. Obtaining Legacy Versions: Bypassing HTTP 403
To ensure backward compatibility, we needed to reverse-engineer `bluetoothd` from older macOS versions.

When using OpenCorePkg's built-in `macrecovery.py` to fetch legacy `BaseSystem.dmg` images (e.g. Monterey and Ventura), Apple's servers returned:
> `HTTP Error 403`

Investigation revealed that Apple has discontinued support for some unencrypted HTTP (port 80) recovery endpoints.
By modifying `macrecovery.py` to force `http://osrecovery.apple.com` to `https://`, we successfully retrieved Recovery images from macOS 12.0 through 26.0 for offline analysis.

---

## 5. Cross-Version Testing: Architecture Summary
By extracting `bluetoothd` from macOS 12 through 26 and running `find_gate.py` for static analysis, we found that Apple's Bluetooth validation block falls into two closely related machine code architectures:

1. **64-bit Register Group (macOS 14 Sonoma, 15 Sequoia, 26 Tahoe)**
   Uses `%r14d` to store the check result:
   ```assembly
   testl	%r14d, %r14d                 # Hex: 45 85 F6
   je	+0x25                            # Hex: 74 25
   leaq	<error_log_address>, %rax    # Hex: 48 8d 05 xx xx xx xx
   movq	(%rax), %rbx                 # Hex: 48 8b 18
   ```

2. **32-bit Base Register Group (macOS 12 Monterey, 13 Ventura)**
   Uses `%ebx` to store the check result:
   ```assembly
   testl	%ebx, %ebx                   # Hex: 85 DB
   je	+0x25                            # Hex: 74 25
   leaq	<error_log_address>, %rax    # Hex: 48 8d 05 xx xx xx xx
   movq	(%rax), %rbx                 # Hex: 48 8b 18
   ```

---

## 6. Final Patch Integration
Based on the identified signatures, we finalized two replacement arrays (Mask Arrays) for the `14_0` and `12_0` generations.
After integrating these signature matrices into `BlueToolFixup.cpp`, the patch is activated via the `-btlfxa2dpcheck` boot-arg. It provides AirPods audio correction from macOS 12.0 through 26.0. The code was also verified against physical binaries using `verify_gates.py` for strict byte-by-byte validation.

---
## Contributors
This fix was developed with assistance from the following AI models:
- **codex (gpt5.4-xhigh)**: Led core reverse-engineering efforts, leveraging strong assembly and machine code analysis capabilities to design a stable, broadly compatible single-gate bypass patch architecture.
- **claude (claude-opus-4.6)**: Contributed to documentation refinement and structuring.
- **gemini (gemini-3.1-pro)**: Participated in testing, analysis, and collaborative discussion.
