# BE201 1.1.7: complete the firmware station AUTHORIZED transition

1.1.6 boot3FFAD770-10F7-4B72-A7FF-A549FE11DAE9 loaded; user confirms the
long connecting spin is gone, but direct Instant Hotspot still fails. Preserve
that lifecycle improvement. FirstFailure/request3 and LastFailure/request15
show valid message3 MIC, message4 TX status1, both SEC_KEY normal replies,
then received reason3/matchmask7. Port-valid is published before the key
command replies. The success snapshot has the same command ordering, so this
ordering alone does not establish the failure's cause. A normal reply is not
a decoded status-payload success. No first UMAC fault is present at12:51:15.
PTK tag0x01000002 and GTK tag0x01010042 have the expected CCMP/group distinction.

A separate confirmed implementation mismatch: API92 enables capability114
STA_EXP_MFP_SUPPORT. The STA_CONFIG builder therefore sets mfp=1 before
port authorization. It currently never sends the AUTHORIZED update. All three
captured nodes have negotiated NODE_MFP clear, yet their firmware STA state
remains in the temporary preauthorization MFP mode. Linux v6.12's
`iwl_mvm_mld_cfg_sta()` sets this temporary bit only before AUTHORIZED, or
when actual MFP was negotiated:
https://github.com/torvalds/linux/blob/v6.12/drivers/net/wireless/intel/iwlwifi/mvm/mld-sta.c
The mismatch is a real porting omission; its contribution to this phone's
reason3 still requires a hardware test. Ordinary-network success does not
prove the mismatch harmless or establish it as this hotspot's cause.

Functional change: the STA builder preserves temporary MFP before authorization
and negotiated MFP at every stage. On an authorized non-MFP connection it
clears only that temporary firmware bit. All other STA command fields remain
unchanged. Open networks become authorized at RUN; RSN networks require the
existing valid-port result. No MFP capability is newly advertised and no peer
security requirement, MIC verification or key-acceptance logic is bypassed.

An optional internal net80211 authorization hook queues a dedicated task.
Initialize the hook to null for all interfaces, register it only in iwx after
attach/task setup, and cancel its task at stop. It does not block RX waiting
for firmware. A separate association epoch advances on MLD auth/deauth;
request/done epochs are reset on those transitions and stop. The worker uses
the existing main gate, requires current RUN/STA/PHY/authorization and no
teardown/shutdown, then sends the existing synchronous STA_CONFIG command
outside RX. After its command wait releases/reacquires the gate, validate both
firmware generation and association epoch, requested RUN and teardown state.
Do not commit stale work or errors as a successful current authorization.
Successful duplicate updates for that epoch are suppressed. This changes no
key command from asynchronous to blocking RX and adds no arbitrary delays.

Default-off numeric diagnostics retain the existing boot option
be201_tlc_diag=1. Ring events29/30/31 record queued authorization epoch,
requested negotiated MFP bit and command-return error. Numeric registry
properties expose ItlwmMldAuthorizedError/Updates/MFP. No address, SSID,
key, nonce or authentication payload is recorded. Existing key ACK and
post-completion disconnect observations remain. No fake beacon or forced
connection-complete is introduced.

Verification:100000 comparisons of actual old/new96-byte STA builders cover
firmware capability, association/authorization, RSN/open, negotiated MFP,
HT/VHT/HE flags, NSS and aggregation values. Only the MFP field differs in
the intended authorized non-MFP cases; negotiated MFP stays enabled and all
other fields match. Pinned API92 parsing confirms capability114 is present.
Actual callback/worker tests cover15 schedules: normal, stale epoch, shutdown,
non-RUN, teardown, invalid port/PHY, reset or association change during command
wait, command error, gate dispatch, duplicates and open networks. ASan/UBSan
passed. Production disconnect/link-state tests continue to pass in WCL/legacy
modes, ring/decoder and boot helpers pass. Full57-unit build, fixed SDK/firmware,
entry/import/constructor/signature audits precede EFI installation.

Runtime status: requires reboot. This candidate is not accepted as an Instant
Hotspot fix. Preserve working1.1.6 rollback, Wi-Fi-disabled recovery, current
Bluetooth/Music pair, MacPro7,1 and identifiers, HE80 and switching improvements.
Dynamically verify the same macOS physical disk, fully back up/hash EFI before
writing only65EA6FB3-72D2-4697-8E12-8815434C008E. Do not hotload or reboot
automatically. Test one direct Instant Hotspot selection with phone Allow
Others to Join disabled and its hotspot settings page closed; collect before
manual opening or power cycling. Require actual data connectivity. Use the
new authorization result and the unchanged real teardown trace to choose the
next step if reason3 persists. AWDL/AirDrop/Watch lock-screen unlock remain
separate unaccepted goals.
