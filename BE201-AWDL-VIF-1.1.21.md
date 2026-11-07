# BE201 1.1.21: AWDL interface creation behind a manual arm

Follow-up to the failed 1.1.20 boot. Boot 893F5869 (19:07, `be201_awdl_vif=1`) never reached the desktop.

## What the logs show

The persisted log stops for every process at uptime about 100 s, right as wifip2pd starts. There is no panic report and no `aapl,panic-info`, although NVRAM was not reset (the earlier test marker is still there) and panic reports were saved on this machine before with the same `debug=0x100`. So a panic is not proven; a hard hang fits too. The last persisted line is not the failure point.

On 1.1.19 wifip2pd issued VIRTUAL_IF_CREATE by itself at uptime 127 s, about 26 s after starting, with no AirDrop request. So 1.1.20 entered interface creation on every boot, before login. Creation is the prime suspect, not proven.

## Defects found by comparing with native 24G824

1. Queues were never added to a work loop. Native BCM AWDL and Apple's generic Skywalk driver both call `addEventSource` on all four before registering. `IOSkywalkTxSubmissionQueue::enable` calls `IOEventSource::closeGate` without a check, and that dereferences `workLoop`, so the first enable would fault on null.
2. The failure path called `terminate(kIOServiceSynchronous)` while holding the command gate. Termination can need that gate, so any failed step could deadlock Wi-Fi ioctls.
3. Registration info was preallocated with `IOMalloc`. Native does not; `copyRegistrationInfo` overwrites the pointer, leaking the block.
4. `getBSDNamePrefix` was inherited. Native returns "awdl"; the base can fall back to "en".
5. Pool and queue arguments came from an old experiment. They now follow Apple's generic driver: pool type 0, flags 0, queue arguments 0, 0, (1, 0), 0.

Which of these caused the failed boot is unknown.

## Changes

`be201_awdl_vif=1` no longer creates anything by itself. It registers `debug.be201_awdl_vif_arm`. Until root sets it, capability bit 32 is not advertised and a create request is refused before any allocation, so a normal boot behaves as if the feature were off. The value lives in RAM, so every boot starts unarmed and a failed test cannot block the next boot. One arm allows one attempt. `be201_awdl_if=1` still advertises the bit from boot for the case where arming after boot does not reach wifip2pd.

Each creation step sets `ItlwmAwdlVifStep` on the controller, logs `BE201VIF step=...` and pauses 200 ms. The kit's test tool polls the property and follows the log stream, saving both with F_FULLFSYNC, so the last step survives a crash. Unsupported requests log their id, first 64 only.

## Verification

21 suites pass. `test-awdl-vif.py` runs the real interface and controller code under ASan and UBSan against mocks: 1216 failure schedules, queues on the loop before registration, native stop before removal before release, no synchronous terminate under the gate, unarmed refusal with no allocation, one attempt per arm. Removing the arm check or the `addEventSource` call makes it fail. `kmutil libraries` resolves the 4 new sysctl imports through com.apple.kpi.bsd.

The mocks do not model native internals. Nothing here is hardware tested, and creation may still fail or crash; the arm limits that to a test the user starts from the desktop.
