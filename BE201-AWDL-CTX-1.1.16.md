# BE201 1.1.16: schedule the AWDL link, bound its queue (default off)

1.1.15 result, boot 17:15: the widened filter on MAC 1 alone received 463 AWDL frames from 3 senders
on channel 149 (PSF 131, MIF 332), with MAC 0 unchanged. Window boundaries: 174, 161, 98 and 22 over 3 TU of 455, so 95.2%
within 3 TU. Transmit: 320 frames queued, one completion,
status success on a unicast. No multicast completion and no retries reported. TxBusy 18.
FwErrors 1 with no error id, later reconnects without a context. Phone had no AWDL event in its archive,
so it cannot confirm reception. Reading: firmware holds frames on an unassociated link with no time
event; Linux protects pre-association transmit with session protection. The queue filled, and the
TX watchdog very likely restarted the device. That watchdog path is inferred, not logged.
This was a defect here: AWDL frames could stall the AP connection.

Change:
- At most 8 frames queued; beyond that they are counted (ItlwmAwdlTxQueueLimited).
- If the watchdog expires with only AWDL frames held, transmit latches off and the device is not
  restarted (ItlwmAwdlTxStalls). AP traffic still restarts it as before.
- After a fault the next association publishes the context state, which was stale before.
- `be201_awdl_ctx=4`: as 3, and marks MAC 1 associated with assoc id 1 after its queue exists, cleared
  first on removal. Unproven: firmware may then expect beacons from the AWDL BSSID. Missed-beacon
  notices for MAC 1 are ignored.

Read after reboot: ItlwmAwdlCtxStage=6, ItlwmFwErrors absent, ItlwmAwdlTxMcastOk rising with Sent,
ItlwmAwdlTxUnicastAck, ItlwmAwdlTxStalls=0, ItlwmAwdlTxQueueLimited low. Phone `Posted peer presence`
needs the AirDrop sheet on the phone that is collected. If frames stay held, next is session
protection on link 1. Verification: scripts/test-awdl-ctx.py and all other suites, 57-unit
build. NOT hardware tested.
