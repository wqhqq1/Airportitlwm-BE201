# AirportItlwm 1.1.45: answer the family's peer cache requests

1.1.44 results, boot 23:39: AWDL started by itself and transfers work. Universal Control works. Continuity Camera reaches the phone's page but no video. iPhone Mirroring fails.

## Continuity Camera at 23:51:34

1. `handleEnsembleTrafficReg: Waiting for caching of HP-RTG Peer`, then 3 s later `ERROR: Peer cache operation failed`. Then `Ensemble start Failure, waiting for UMIStatus umi: b000000`, and AWDL_PEER_TRAFFIC_REGISTRATION for RemoteCamera returns kIOReturnIOError.
2. `Server ignoring low latency without local llw0`.
3. The RTP nw_connection `IPv6#04a208b8.49688` is unsatisfied, No network route, and times out at 5 s: `Failed to create nw_connection for RTP`. The address shows no interface scope, unlike the Rapport connection's `%awdl0`. Why is not established; llw0 is the suspect.

## Change

setPEER_CACHE_CONTROL used to be taken and dropped. Now the address (+8) becomes a peer station with no RSSI limit, and once the station is in the firmware the driver posts event 51 (`reportDataPathEvents` case 0x33 to `handleCacheControlMessages`), 0x1d0 bytes, version 1, operation 1 at +4, address at +8. Request operation 2 is a delete and gets operation 3; the station stays, as it does for every heard peer, so four distinct addresses fill the table and later requests get no answer (CacheFull). The family then waits and fails as before, nothing claims success it did not get. RAM switch `debug.be201_awdl_cache_off`.

Whether UMI then completes is unknown: family code sends it, and the Mac's frames carry the family's TLVs only through the MIF template.

## iPhone Mirroring, not changed

sharingd sends the pre-pairing request, receives the phone's pairing request 5 s later, then logs `Unexpected error`; the app gets com.apple.sharing.authentication Code=10 and ScreenSharingKit.RemoteAuthenticationError Code=3. So Wi-Fi and IDS reached the phone. Apple lists Apple silicon or T2 as a requirement and this machine has neither, only the MacPro7,1 model name, which is the likely cause; the error text is private in the log, so this is not proven.

## Next

llw0: native AppleBCMWLANLowLatencyInterface derives from IO80211InfraProtocol, withProvider calls setLowLatencyEnabled(true), setParentInterface(awdl) and setCompanionLowLatencySkywalkInterface; it is created through COMPANION_SKYWALK_IF_CREATE on awdl0. Not built yet.
