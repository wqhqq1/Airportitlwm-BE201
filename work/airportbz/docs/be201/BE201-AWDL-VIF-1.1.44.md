# AirportItlwm 1.1.44: AWDL starts by itself

New boot flag `be201_awdl_auto=1`, with `be201_awdl_vif=1`. At load the driver sets the same RAM gates the test tool set (accept, link, AW, radio, RX, TX, data, arm), so the capability bits are there when wifip2pd first looks and its first request creates awdl0. One attempt per boot as before. The test switches (own queue, hold, second PHY, windows, A-MSDU) stay 0 and no tool in this kit sets them.

wifip2pd reads the capability at its own start: on boot 22:52 it logged "missing the capability" at 22:54:34 and created awdl0 only after a restart at 22:55:35, so a delayed arm cannot work without restarting it. On that boot wifip2pd first found en1 about two minutes after boot, so the create should land near login, not in early boot; that is one boot's timing.

Guard: if `aapl,panic-info` is in NVRAM at load, read only, auto start is skipped for this boot and `ItlwmAwdlAutoSkippedAfterPanic` is set. A hang leaves no record, so this does not cover a stuck boot.

## Universal Control and Continuity Camera, findings, not fixed

Universal Control to the iPad (iPad16,3): `SendRequestID 'com.apple.universalcontrol' ... kTimeoutErr (On-demand discovery timeout)`, every 15 s, rapportd "Start on-demand connection discovery over AWDL ... timed out". ProbeSenders 1: this boot the driver heard one AWDL sender, the phone. The iPad was never heard on the air, which may mean it was asleep or on other channels.

Continuity Camera to the phone: rapportd "Deferring connection until found", BLE NearbyActionV2 advertiser started, and the session is invalidated 12 s later (23:20:03 to 23:20:15). Phone-side logs are needed to see whether it heard the advert.

Both fail at finding the peer, before any data. wifip2pd also logs on every start "Failed to create the companion low latency interface for AWDL": COMPANION_SKYWALK_IF_CREATE is unsupported here. Native has AppleBCMWLANLowLatencyInterface (llw0), set through IO80211VirtualInterface::setCompanionLowLatencySkywalkInterface. Whether either feature needs it is unknown; building it is the next candidate once phone logs are read.

## Not verified

Automatic creation in the boot flow, sleep and wake with awdl0 up, and creation before en1 has joined.
