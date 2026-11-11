# BE201 1.1.13: AWDL context as an unassociated P2P client (default off)

1.1.12 result, boot 16:32: IBSS MAC, link add and link modify were accepted. Firmware then
asserted 0x2010303E, last host command LINK_CONFIG (0x3d0309), the activation of link 1 on
the AP's PHY context. The last command is correlation, not proof. The latch worked: one fault, Wi-Fi back
in about 36 s, no re-entry, no AWDL frame sent. Handoff was normal on that boot, which tests nothing
about AWDL: the context was down and the station filter was never widened.

Change: MAC type P2P client (7), never associated, group filter only; link 1 on the AP's
PHY context; a PEER station at the AWDL BSSID, the state a station holds before
authentication. Linux allows station plus P2P client on one PHY context, but always with a
real GO, so this unassociated form is unproven. Boot argument `be201_awdl_ctx=2`; value 1
(IBSS) is now off. Rest as in 1.1.12: added after authorization, removed first in
run_stop and deauth, AWDL frames only on this queue, any failure latches off.
A missed-beacon notice for MAC 1 is ignored so it cannot touch the AP link.

UNPROVEN, read from counters on a reboot:
1. Link activates: ItlwmAwdlCtxStage=5, ItlwmFwErrors=0.
2. AWDL frames arrive: ItlwmAwdlProbeAction>0. An unassociated MAC may filter foreign BSSIDs;
   if 0, this MAC can take ACCEPT_BEACON or ACCEPT_CONTROL_AND_MGMT on its own.
3. Peer tracks us: phone wifip2pd `Posted peer presence` with ItlwmAwdlTxAddr.
4. ACK: ItlwmAwdlTxUnicastAck>0. Frames to other peers use a station for the BSSID, so
   firmware may still not expect the right ACK.
5. Handoff: phone `decrypted advertisement` and payload requests, with the context up.
6. AP link stable, including Wi-Fi off and on.

If link activation asserts again, the next candidate is the P2P Device type with ROC, which
Linux uses with a station, but it needs time-limited windows. Filter-versus-transmit
A/B remains skipped. Verification: scripts/test-awdl-ctx.py and all other suites, 57-unit
build. NOT hardware tested.
