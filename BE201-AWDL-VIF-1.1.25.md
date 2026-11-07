# BE201 1.1.25: let the family's AWDL manager start

Follow-up to the 1.1.24 arm test (boot E234B40E, 21:42).

## What 1.1.24 showed

The system now uses awdl0: wifip2pd browses and advertises _airdrop._tcp and _companion-link._tcp, sharingd listens on port 8770 scoped to awdl0, and the AirDrop browser reported one peer (maxPeersDiscovered 1, first discovery 3.6 ms). awdl0 carried 0 packets, so that peer did not arrive over AWDL; the Mac is on the phone's hotspot, so en1 is the likely path, unproven. The phone cannot see the Mac. Handoff also failed that boot.

Kernel log (com.apple.p2p):
- `IO80211AWDLPeerManager::interfaceStateChange Interface link is down, nothing to do. Source = Mdns`
- `updateLocalRequests Received service request but not configured (_stateFlags:0x0)! bailing..` (the ENXIO, type 120)
- `handleAssistedDiscoveryTrafficReg Received TrafficReg request but not configured (_stateFlags:0x0)! bailing..` (the EPERM, type 164, Watch error 192)

## What that means

Correction of earlier notes. Type 120 is not a native stub to ignore, and the EPERM on type 164 does not come from a driver handler. IO80211Family contains the AWDL protocol logic in IO80211AWDLPeerManager (election, channel sequence, MI and sync frame building, service TLVs, action frame input, peer table). The manager pushes settings down through the same set calls we were accepting. So AWDL does not have to be written from scratch. The driver has to provide the firmware side.

The manager never started because of this driver: linkState() always returned Down and setLinkState(Up) was refused. Native path on 24G824: concrete setInterfaceEnable(true) calls IO80211VirtualInterface::setInterfaceEnable(true), which calls setLinkState(Up, 1), which calls IO80211PeerManager::enable, then doEnable, configure, interfaceStateChange, enableAWDL. Native then calls reportLinkStatus(3, 0x80). The BSD client's ioctl handler sets IFF_RUNNING when setRunningState(true) returns success.

## Changes

- New RAM-only sysctl `debug.be201_awdl_vif_link`, default 0. With it off, behaviour matches 1.1.24.
- With it on, the first setRunningState(true) from the BSD client starts a one-shot timer on the Wi-Fi work loop. The timer calls the native base setInterfaceEnable(true), under the same gate as en1's link changes and not on the ifnet ioctl thread, since native runs the manager inline. linkState() and setLinkState(Up) then pass through.
- setRunningState(true) still returns unsupported and reportLinkStatus is not called, so no IFF_RUNNING and no packets reach the queues. The queue callbacks are untested with traffic, so they stay out of this round.
- `ItlwmAwdlRequestCounts` (u32 per id from 500) covers every request, since the manager repeats itself past the first 256. The last payload of sync params, sync enabled, BSSID, channel sequence, master channels, sync state, AF TX mode and the sync frame template is kept in `ItlwmAwdlPayload<id>`. The template copies 0x200 bytes: on 24G824 it is inline on the caller's stack, not the pointer layout in the SDK header.
- The test tool also restarts Finder, since the user saw AirDrop appear only after that, and waits 60 s instead of 20 s.

## Expected

Kernel log reaches CONFIGURED and ENABLE-AWDL, and types 120 and 164 stop failing. We learn the exact firmware calls, channel sequence and sync frame. Accepted settings still do nothing on air and the driver sends no availability window events, so the manager should log `aw start event missing`. The phone still cannot see the Mac.

## Risks

The manager now runs on real timers against a fake firmware. The family has panic sites in handleUmiTimer, removePeer and similar; none should be reached with no peers, unproven. selfDiagnosticsReport on missing AW events was not fully read. Manual arm only: a normal boot is unaffected and a crash does not repeat.

## Next, after this works

AW start events and channel hopping driven from the manager's channel sequence (session protection on MAC 1 from the ctx work), sync frame and MI TX on the AP queue (ACKs seen on 1.1.18), action frame RX into actionFrameInput, then RUNNING and a real data path.

## Verification

21 suites pass and the build links. Not hardware tested.
