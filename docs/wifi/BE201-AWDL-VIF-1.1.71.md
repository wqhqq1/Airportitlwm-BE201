# AirportItlwm 1.1.71: frames to IPv6 ULA destinations go to llw0

## 1.1.70 result, boot 07:58, 2026-11-09 (OpenCore 1.0.8 RELEASE)

- **llw0 bring-up:** llw0 went up through IOSkywalk: ItlwmAwdlLlwUpResult 0, LlwUpRunning Yes, no fallback.
- **Channels:** "os_channel_create … Resource busy" is gone. The camera's audio and video streams were set up, and llw0 sent 16 frames.
- **Still no picture:** 12 s after the 08:06:37 session, `VCMediaStream checkRTCPPacketTimeoutAgainstTime` reported that no RTCP had arrived. llw0 received nothing (no ItlwmAwdlDataRx).

## Cause

llw0 shares awdl0's MAC address, so the driver decides which interface a received frame belongs to. Through 1.1.70 a unicast TCP or UDP frame went to llw0 only when its destination port was one llw0 had already sent from.

For Continuity Camera the Mac is the server. RPStreamSession reports "Server", and the flows are listeners plus delegated connections on llw0, so the phone sends first. Its RTP and RTCP to the Mac's per-session ULA address (`fdxx:…`) did not match a learned port. They went to awdl0, where nothing listens on that address, and were lost.

## Change

`iwx_awdl_llw_input`:
- A unicast TCP or UDP frame whose IPv6 destination is in fc00::/7 goes to llw0. Low latency Rapport sessions use per-session ULA addresses at both ends. awdl0's AirDrop and Universal Control traffic uses link-local fe80:: addresses.
- Port learning stays as an extra match.
- ICMPv6 still goes to both interfaces. Multicast and IPv4 still go to awdl0.

test-awdl-ba checks ULA (fd and fc), TCP, link-local, multicast and ICMPv6 routing without any learned port.
