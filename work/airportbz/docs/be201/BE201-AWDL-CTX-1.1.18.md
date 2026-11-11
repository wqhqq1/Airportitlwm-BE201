# BE201 1.1.18: AWDL receive on its own MAC, transmit on the AP queue (default off)

1.1.17 result, boot 17:41: firmware accepted session protection on link 1 (14 requested, 13 started,
13 ended, 0 failed), network speed unchanged per user, yet 8 frames queued, 0 completed. So windows
did not free this queue either; no mode with its own station has transmitted reliably.
A real removal ran for the first time (Removes 2). Re-adding then failed at the queue with EIO:
the old ring still counted held frames, which the driver's check for a new queue rejects (from
reading the code). Transmit latched. Firmware then asserted 0x20101E08, data1 3, last command
UMAC scan 0x37010D, at about 17:44:23. Scan is correlation only; the held-queue path may be involved.
Handoff per user: only the phone side showed an entry. Phone decrypted 10 Mac adverts, Mac decrypted 16,
no payload requests. Phone wifip2pd had no record of this address; its long AWDL session started after the latch.
User note: Wi-Fi Direct on this card under Windows coexists with the main network, so the
hardware allows concurrency. The P2P Device type stays the fallback.

Change: `be201_awdl_ctx=6` creates only MAC 1 and link 1 (address, wide filter, no station, no queue),
and sends AWDL frames on the AP station's management queue, which reached a phone on 1.1.11. No
removal of a queue with held frames can occur, as there is no such queue. No session protection.
Frame source is MAC 1's address, so firmware may now take ACKs and unicast for it. That is the hope,
not established: the frame still leaves through the AP's link.

Read after reboot: ItlwmAwdlCtxStage=3 (ACTIVE is the end state here), no ItlwmFwErrors,
ItlwmAwdlTxMcastOk rising with Sent, ItlwmAwdlTxUnicastAck, ItlwmAwdlProbeData, phone
`Posted peer presence` with ItlwmAwdlTxAddr. Verification: scripts/test-awdl-ctx.py and all other
suites, 57-unit build. NOT hardware tested.
