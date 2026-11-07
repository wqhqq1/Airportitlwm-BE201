# BE201 1.1.6: WCL owns reconnects after peer teardown

1.1.5 boot A6AF4592-B015-482D-AC47-78F57D36AE51. The user clarified that
manual hotspot opening alone did NOT immediately connect; Mac Wi-Fi was also
powered off/on. A controlled test keeping Allow Others to Join off and the
phone's hotspot settings page closed still fails after only Mac Wi-Fi cycling.
Do not count either earlier eventual connection as direct Instant Hotspot
success. Successful snapshots can be later router/manual joins, not this test.

FirstFailure/request1 and LastFailure/request4 (12:23:12 capture), plus
request8 in the12:33:46 controlled-failure capture, show association0, valid
message3 MIC, message4 submission and firmware TX success1, local key-command
acceptance and port-valid, followed by received reason3/matchmask7. No first
UMAC snapshot. No bad MIC/replay count. This is now stronger than merely a
send function returning0: the fourth frame has a real successful NIC completion.
It still does not prove the peer accepted its MIC or the key installation
commands completed: the current key backend sends those asynchronously.

One attempt at12:20:41.963503 really reaches native WCL connect-complete0
and WAITING_FOR_IP, then receives reason3 at41.966015, about2.5ms later.
Thus absence of the first beacon is not a complete explanation of all failures;
1.1.5's beacon forwarding remains useful but does not establish a hotspot fix.
Between12:20:51 and12:21:57, WCL reports repeated311 events without new native
JOIN_REQs; the driver continues key exchanges. Do not decode311 as a physical
IEEE reason without corresponding receive evidence. Wi-Fi off12:21:59.281
and on12:22:00.513 precede a fresh join at12:22:05.008 and success05.523.
Manual opening and power cycle are confounded and were both reported by user.

A real lifecycle inconsistency explains uncontrolled retries: after posting a
failure to WCL, net80211's DEAUTH handler unconditionally starts AUTH again.
DISASSOC similarly starts ASSOC and did not notify WCL. This makes the lower
layer reconnect even when the system has completed/cancelled its request.
On WCL station mode only, queue INIT before notifying WCL, so synchronous
native retries see the existing teardown fence and defer until actual cleanup.
Notify one teardown and do not run legacy autonomous AUTH/ASSOC. Preserve the
old logic in non-WCL builds. Suppress late LINK_STATE_UP during the pending
teardown before either BSD/controller link publication. Current-peer teardown
is still honored; foreign-frame filtering, real beacon requirements and normal
new WCL joins remain. This fixes a demonstrated ownership defect; RF testing
is still required to establish whether the visible long spin is gone.

Observation only: at the existing default-off be201_tlc_diag=1, reuse command
slot tags/cookies to record SEC_KEY v1 submission and normal reply/explicit
failure. Inspect only public action/key-id/flags at bytes0..15 of the80-byte
command; never read or retain key/sequence bytes16..79. Reset every host-command
slot tag before submission; pending-slot, opcode and join cookie scope replies.
The key transport stays asynchronous, with no blocking wait in the RX callback.
A normal reply event is not a decoded status-payload success. No authentication
policy or key acceptance logic is changed here. A post-success peer disconnect
also publishes LastFailure so it cannot be hidden by the preceding success.

Primary references (limitations, not a drop-in fix):
- https://openintelwireless.github.io/itlwm/FAQ.html
- https://github.com/OpenIntelWireless/itlwm/issues/749
The FAQ documents recognition with manual hotspot enabling required. The older
issue offers ordinary hotspot workarounds; neither implements native joining.
Linux v6.12 mld-key.c sends key ADD synchronously in its different mac80211
context, a useful ordering reference, not permission to block this RX callback:
https://github.com/torvalds/linux/blob/v6.12/drivers/net/wireless/intel/iwlwifi/mvm/mld-key.c

Verification: compile actual DEAUTH/DISASSOC methods in WCL and legacy modes;
48 schedules each cover state/reason/early retry, exactly one INIT+notification,
no autonomous reauthentication, truncated frames and legacy AUTH/ASSOC behavior.
Compile actual link-state method to reject late UP during cleanup. Protected
memory tests allow only the16 public key-command bytes, making secret bytes
unreadable; malformed tags/cookies rejected. Actual command-completion method
covers216 queue/index/pending/cookie/opcode combinations and preserves original
free/wakeup/queue accounting. Ring/publisher/decoder and boot checks pass, plus
full57-unit build, fixed firmware/1232-file SDK, signature/import/entry audit.

Not accepted as repaired: direct Instant Hotspot, AWDL, AirDrop or Watch lock
screen unlock. Keep1.1.5 recovery, working BT/Music pair, MacPro7,1 and machine
identifiers, HE80 and existing switching improvements. Full backup and dynamic
same-physical-disk verification precede EFI writes; only authorized
65EA6FB3-72D2-4697-8E12-8815434C008E. No hotload or automatic reboot.

After reboot test one direct Instant Hotspot attempt without opening its phone
settings page. Record prompt/spinner duration and actual Wi-Fi/data availability
separately. Collect before a workaround. If reason3 persists, use key-command
replies and real post-complete disconnect evidence to select the next fix;
do not call the previous software key submission a confirmed firmware install.
