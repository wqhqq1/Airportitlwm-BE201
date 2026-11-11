# BE201 1.1.12: separate AWDL firmware context (default off)

1.1.11 proved transmit: the iPhone's wifip2pd listed the Mac's random AWDL address as a
peer. But Handoff failed on both boots with the AP station's filter widened, and worked
on the same binary with it off. This stage stops widening that filter, and gives AWDL its
own MAC, link, broadcast station and TX queue. It publishes no interface, so AirDrop and
Watch unlock stay unavailable.

Boot arguments: `be201_awdl_ctx=1` creates the context and receives; `be201_awdl_tx=1`
also transmits. With `be201_awdl_ctx=1`, the station filter stays as in 1.1.9 even if
`be201_awdl_probe` is set. With both absent, nothing here runs.

Design: MAC id 1 of type IBSS, address random per boot, group filter only (no control,
management or promiscuous flag); link 1 on the AP's PHY context with the AWDL BSSID;
station 3 of type BCAST_MGMT; a queue on its TID 15. Added once per association from the
authorized task, so join frames are untouched. Removed in reverse order first thing in
run_stop and deauth. AWDL frames go only on this queue, never on the AP station's. Any
command failure or firmware fault latches it off for the boot.

UNPROVEN, each read from counters on a reboot:
1. Firmware accepts STA + IBSS on one PHY. Linux never pairs them; its interface
   combinations allow station with P2P client or GO. ItlwmAwdlCtxStage=5 and no fault.
2. Group filter plus BSSID match delivers AWDL frames. ItlwmAwdlProbeAction>0. If it is 0
   with the context up, this filter is too narrow, not proof that receive is impossible.
3. Own address makes ACKs work. ItlwmAwdlTxUnicastAck>0. Queue belongs to a broadcast
   station, so firmware may not expect ACKs on it; then a peer station is next.
4. Handoff unaffected: phone logs `decrypted advertisement` and payload requests. Linux
   notes that P2P is_disc_extended widens filters on all MACs, so firmware filters may
   not be fully per-MAC.
5. AP link stable, including network switch, sleep and wake with the context present.

No channel switching, AW scheduling or awdl0 yet. Beacons are not configured. This does
not settle whether the filter or transmit caused the Handoff failures; that A/B was skipped
by decision. Verification: scripts/test-awdl-ctx.py (wire layout, order, latch) and all
other suites, 57-unit build. Kernel imports unchanged. NOT hardware tested.
