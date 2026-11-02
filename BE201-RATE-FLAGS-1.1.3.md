# BE201 1.1.3: coding flags must match the negotiated mode

User reports on loaded1.1.2: manual Wi-Fi switching now works; Handoff may
have recovered (not yet accepted as stable); automatic hotspot still fails.
Preserve all1.1.2 switch/address/diagnostic changes and the working BT pair.

Boot2732BD86-E2C7-4BDF-B89B-F485BB1B4CC7, first fault schema2/gen1:
error0x20101a0d/data1=3/header0x60050f. The final queued TLCv4 record exactly
matches the error header and generation. It has stateRUN, modeNON_HT(0),
width20, empty HT/HE rate maps, flags2(LDPC), SGI15, legacy bitmap0xff0.
Earlier NON_HT initializations had flags0. Earlier successful HE setup had
mode3/rates0xfff per NSS/LDPC2. Link deactivate and remove were captured
before the subsequent ADD/activate and failing TLC. The assert ID remains
undecoded; exact last-command correlation does not alone prove causation.

`iwx_auth` clears negotiated HT/VHT/HE node flags before rate setup, while
`ic_state` may still be RUN until the asynchronous transition finishes.
The coding-flag builder checked the old state, then read retained capability
IEs even when the rate builder selected NON_HT. Add a negotiated-mode guard
so NON_HT has no LDPC/STBC/DCM flags. All existing state/capability logic for
negotiated HT/VHT/HE remains unchanged. Do not change HE80, SGI, rate maps,
firmware, command waits, Wi-Fi join retries, AWDL or Bluetooth here.

`test-tlc-mode-flags.py` compiles the actual old/new methods under ASan/UBSan.
It reproduces the captured node-flags/state/capability scenario (2 -> 0),
then compares100000 state/mode/antenna/capability combinations, requiring
identical negotiated HT/VHT/HE behavior and zero legacy coding flags.
The old source fixture is hash pinned and included for archive-only tests.

Reboot validation: preserve normal ax80/first-attempt switching; test one
automatic hotspot wake and actual Wi-Fi connection separately. Save the
first fault before retries/manual hotspot opening. The unchanged schema2
trace can verify whether legacy coding flags are now zero and whether a
different command fails. No fault by itself is not proof of connectivity.
No promise that this alone fixes hotspot or Wi-Fi-dependent Handoff.

Deploy with full same-disk EFI backup and verified old1.1.2 recovery. Only
Wi-Fi and its row comment change; boot arguments, SMBIOS and BT are retained.
