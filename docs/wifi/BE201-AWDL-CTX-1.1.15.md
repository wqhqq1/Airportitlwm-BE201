# BE201 1.1.15: AWDL context receive filter (default off)

1.1.14 result, boot 17:03: link activation succeeded. CtxStage=5, queue 10, no firmware fault,
so the asserts followed the old activation command with zero fields; two types failed with it
and one passed without it. Handoff normal per user with the context up, phone decrypted 6 adverts.
But ItlwmAwdlProbe* never appeared: not one foreign frame reached the host, while the phone ran
AWDL on and off from 17:06 to 17:07:56. With no heard frame, transmit never fired: frames sent
0, and no presence for this address on the phone. Wi-Fi off and on was not exercised (Adds 1,
AuthorizedUpdates 1), so removal and re-creation remain untested.

Change: `be201_awdl_ctx=3` adds ACCEPT_CONTROL_AND_MGMT to MAC 1 only, the flag Linux gives a P2P
Device. MAC 0 stays as in 1.1.9. `be201_awdl_ctx=2` keeps the group-only filter of 1.1.14.

Read after reboot: ItlwmFwErrors absent, ItlwmAwdlCtxStage=5, ItlwmAwdlProbeAction>0,
ItlwmAwdlTxMcastOk>0, phone `Posted peer presence` with ItlwmAwdlTxAddr, ItlwmAwdlTxUnicastAck>0
(first test with a source address the firmware owns), ItlwmAwdlProbeData. Firmware filters
may not be fully per-MAC. Handoff is observed by the user, not a pass or fail.

If Action stays 0, the next option is is_assoc=1 for BSSID match on MAC 1, with beacon-loss risk,
or dwelling on a listed AWDL channel. Verification: scripts/test-awdl-ctx.py and all other
suites, 57-unit build. NOT hardware tested.
