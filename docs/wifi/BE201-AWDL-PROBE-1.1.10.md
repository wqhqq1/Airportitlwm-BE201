# BE201 1.1.10: AWDL radio feasibility probe (phase A)

First AWDL stage. Answers one question: can this card, while associated, receive
AWDL action frames from nearby Apple devices? It publishes no interface, transmits
nothing and enables no AWDL capability. AWDL remains not implemented.

No reference implements AWDL radio. Firmware has no known AWDL offload, so a later
stage would need host-scheduled 16 TU windows, and that remains unproven.

`be201_awdl_probe` boot argument: 0 or absent off; 1 adds ACCEPT_CONTROL_AND_MGMT to the
station MAC only after association; 2 also adds PROMISC. Other values are off. With it
off, MAC commands and the RX path behave as in 1.1.9.

iwx_awdl_probe_rx runs before net80211 on RUN state only. It counts then drops frames the
wider filter newly admits. Own-BSS frames, infrastructure data, beacons, probe responses
and BlockAckReq still reach the stack. Foreign control frames are dropped.
Counters are numeric; sender uniqueness uses 16-bit hashes in RAM.

Classification: BSSID 00:25:00:ff:94:73; action category 127, OUI 00:17:f2, type 8;
subtype 0 PSF, 3 MIF, per the public OWL protocol analysis.

Reading the result (properties ItlwmAwdlProbe*, updated at most once a second and only
when a frame is dropped):
- Action>0: this card hears AWDL on the current channel. Go on to phase B and timing.
- ForeignMgmt>0, Action=0: filter works, no AWDL on this channel then. Retry; a channel
  dwell on 6/44/149 is the next probe. Not evidence AWDL is impossible.
- ForeignMgmt=0: firmware did not widen the filter; try mode 2.
- Passing shows receive only, not transmit, timing sync or data.

Known limit: only the associated channel is heard, and the probe is deaf during absences.
Extra interrupts are possible on busy channels; only with the argument set.

Verification: scripts/test-awdl-probe.py plus all existing suites; 57-unit build.
NOT hardware tested.
