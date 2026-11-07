# AirportItlwm 1.1.48: llw0 created without waiting in the request

1.1.47 results (test 01:15-01:21, Mac on router channel 36): UMI works. iPad and iPhone acked the Mac's UMI, RTG went Active, the phone's RTG TLV was parsed. Camera and Sidecar still had no picture: "Server ignoring low latency without local llw0", RTP "No network route". AirDrop send succeeded but waited a long time; the RTG channel sequence was 149 and 6, never 36 (inferred cause).

llw0 in 1.1.47: wifip2pd's request came at 01:19:45, IO80211SkywalkInterface init and start ran (corecapture pipe Interface_LowLatency_0), then the driver waited 10 s for the BSD interface inside the request and returned not ready. No llw0 afterwards. Driver properties were lost to a reboot, so the stage it stopped at is unknown.

## Change

The request is answered at once with the name native would give (llw0), and the interface finishes from its own timer: up to 60 s waiting for the BSD attach, then the companion id, awdl0 routing and data. Hypothesis: the request arrives on awdl0's path, which the attach needs, so waiting there blocks it. Not proven. wifip2pd has a path that waits for the interface name to appear.

Controller properties for the test: ItlwmAwdlLlwStage (1 init, 2 attach, 3 start, 4 registered, 5 BSD attached, 6 data up), ItlwmAwdlLlwFailedStage, ItlwmAwdlLlwPolls, ItlwmAwdlLlwName, ItlwmAwdlLlwRegistrationError. The camera tool saves them and the interface list, waits 75 s for llw0, and asks for the phone's 5 GHz hotspot.
