# BE201 1.1.19: observe how the system asks for awdl0 (default off)

1.1.18 result, boot 18:01: AWDL radio works. MAC 1 and link 1 received 1361 frames from 3 senders, with the AP
filter unchanged. On the AP queue with MAC 1's address, 609 of 609 multicast completed and 222 of 235 unicast
were ACKed. No fault. Handoff failed per user. Phone archive had no wifip2pd events, so no presence evidence.

Findings from /usr/libexec/wifip2pd on 24G824 (x86_64, read-only), and its live log:
- wifip2pd already tries on demand: "Cannot create AWDL interface because the device is missing the
  capability", then "Failed to create interface AWDL on en1 with error <Apple80211Error Operation Not Supported>".
- 0x100041350 builds the request with ioctl parameter 0xc, then bit-tests the capability bytes
  (0x100093db0: byte index >> 3, bit & 7). Caller 0x10003d960 passes type 1, role 6, bit 32 for one
  branch; bit 72 with roles 9 and 10. Role 6 is APPLE80211_VIF_AWDL in the local header.
So AWDL is capabilities[4] bit 0. Type-to-name mapping was read from the error path's strings, not traced fully.

Change: `be201_awdl_if=1` sets that bit on the WCL path, so wifip2pd passes its check and calls
VIRTUAL_IF_CREATE. The handler records requests, version, role, address and name on the interface
(ItlwmAwdlIfCreate*) and still returns unsupported. No interface exists, nothing reports success.
This capability is claimed before it is true, only under the boot argument, only to observe. Other
daemons also read it: sharingd, rapportd and airportd behaviour may change, including Handoff.

Config: `be201_awdl_ctx=6 be201_awdl_if=1`, transmit off, which also gives the rx-only Handoff sample.

Read after reboot: ItlwmAwdlIfCreate* with `ioreg -l`; wifip2pd "Failed to create interface"; which other
AWDL ioctls appear; sharingd WiFiP2P lines. Native path to follow next: IO80211Controller::attachVirtualInterface,
IO80211VirtualInterface::init/start, AppleBCMWLANCore::createVirtualInterface and createSkywalkInterface
in work/awdl/. Verification: scripts/test-awdl-if.py and all other suites, 57-unit build. NOT hardware tested.
