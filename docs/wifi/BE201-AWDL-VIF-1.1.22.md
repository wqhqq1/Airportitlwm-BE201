# BE201 1.1.22: publish before waiting for the BSD interface

Follow-up to the 1.1.21 arm test, which panicked. Report Kernel-2026-11-02-204354.panic: page fault, CR2 0x20, in `IO80211InfraInterface::postMessage` from `IO80211PostOffice::outForDelivery` on a timer thread, uptime 271.43 s, message 0xc9, length 0x147.

## What the test showed

The saved registry steps were native-init, attach, native-start, pool, queues, event-sources, register, running-state. So `registerEthernetInterface` succeeded with the queues on the work loop. "publish" was never reached.

## Cause

The fault is `call [rax+0x20]` with rax 0: retaining the object in the controller's AWDL pointer (`[controller+0x120]+0x188`), whose vtable was already zero. Native `IO80211VirtualInterface::createPeerManager` stores the role 6 interface there, and nothing in IO80211Family clears it for an interface going away.

`getBSDName` and `getBSDInterface` were checked before `registerService`. `IOSkywalkNetworkBSDClient` is a personality matching on the published service, so the BSD interface could not exist yet, and the name check always failed. Failure released the object while the controller still pointed at it. The next delivered message used the freed object. This reading fits the registers and the steps; the final moments were not logged, so it is inferred, not observed directly.

The same order was in 1.1.20, so its create attempts could not have succeeded either. Whether that caused its failed boot is still unknown: that boot left no panic report, and a 1.1.21 boot later stuck at login with no create request at all.

## Changes

1. `start` publishes right after registering, as native does. Native waits synchronously. Here the controller waits for the BSD interface in 100 ms steps, up to 10 s, with the command gate released, because the BSD client attaches from the matching thread. The running state is set once the interface exists.
2. After native init a failed creation keeps its object. It stays referenced from `awdlInterface`, later requests get NotReady, and arming does not retry. Controller stop tears it down and clears the AWDL pointer first. There is no free on failure any more.

## Verification

21 suites pass. `test-awdl-vif.py` now models the BSD client attaching only after publishing, and asserts the pointer is valid or null in every failure schedule. Removing the publish, or restoring the free on failure, makes it fail. Mocks do not model native internals.

Not hardware tested. Reaching `awdl0` exposes new native paths, because wifip2pd will start driving the interface, and they may also crash. The arm still confines this to a test started from the desktop.
