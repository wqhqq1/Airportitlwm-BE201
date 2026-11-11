# BE201 1.1.11: AWDL sync and transmit (default off)

1.1.10 proved receive: 1311 AWDL action frames from 5 senders on channel 149 while
associated. It proved nothing about transmit, the largest unknown. This stage follows
the peers' timing and sends real frames. It publishes no interface, so AirDrop and
Watch unlock stay unavailable. This code is first slice of the implementation, not
another probe. Wire format comes from the public OWL analysis; iOS 26 may differ.

Boot arguments: `be201_awdl_probe=1` (receive) and `be201_awdl_tx=1` (transmit, needs
the probe). With both absent, MAC commands, RX and TX behave as in 1.1.9.

Sync: parses sync, election and channel sequence TLVs. Follows one cluster, changing
reference only after 1 s of silence. Numeric stats: per-sender window boundary error
(jitter buckets, OWL's limit is 3 TU), host latency spread, channel slots.

Transmit: at most one frame per heard frame, within 20 ms of it, on the AP channel,
through the AP station's management queue at the lowest basic rate. Multicast PSF at
most every 110 TU and MIF every 1 s; unicast MIF to the last heard sender every 1 s.
Requires an authorized link and a free queue. Source address is random per boot,
never the Wi-Fi address (`ItlwmAwdlTxAddr`). Node name is the fixed "be201". Metric 60
and height+1 keep it from becoming master. Channel sequence lists only the AP channel.

Evidence, strongest first:
- ItlwmAwdlTxUnicastAck>0: a peer's radio acknowledged our frame. Proves on-air delivery.
- UnicastNoAck only, McastOk>0: firmware sends, but no ACK: address, window or channel.
- McastFail or LastFailStatus: firmware rejects this frame or queue.
- ItlwmAwdlTxTripped=1: a firmware fault followed; transmit stopped for this boot.

ACK proves radio delivery only, not that a peer accepts this node.

Known limits: the card cannot receive frames sent to the random address (no ACK, no
data), since the firmware filter holds only the station address. No channel switching,
so only peers visiting the AP channel are reachable. Completion counts cover the last
frame of a coalesced response. No scheduled transmit: frames follow heard frames.
Each frame logs one rate line from the existing TX path.
The wider receive filter returns with this build: it is also the retest of the Handoff
failure seen on the first probe boot.

Firmware fault latch: iwx_nic_error stops transmit for the boot if any frame was sent.
AWDL TX losses stay out of the AP link's antenna toggle and error count.

Verification: scripts/test-awdl-tx.py (ASan/UBSan: built frames parse back, wrap,
rate limits, 300000 mutated frames), all other suites, 57-unit build. Kernel imports
are unchanged from 1.1.10. NOT hardware tested.
