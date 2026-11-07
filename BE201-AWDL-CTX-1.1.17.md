# BE201 1.1.17: session protection for the AWDL link (default off)

1.1.16 result, boot 17:30: stage 6, no firmware fault, Wi-Fi off and on fine, Adds 2. Queue cap held:
16 frames queued (8 per context), 256 limited, Stalls 0, no restart. So the safety fix works.
But 0 completions: marking the MAC associated did not get frames sent. Phone archive has no hit
for this address. Handoff normal per user, phone decrypted 4 adverts, no payload line logged. The one
success on 1.1.15 stays unexplained.

Change: `be201_awdl_ctx=5` keeps the MAC unassociated with the wide filter, as Linux keeps a station
before association, and asks SESSION_PROTECTION on link 1 for 100 TU, at most once a second and only
while peers are heard. Asynchronous, since it runs on the receive path. Notifications for link 1 are
counted (ItlwmAwdlCtxTe*) and kept out of the AP link's state. The session is cancelled first on
removal. Cap and stall guard as in 1.1.16.

Unproven: firmware may pause the AP link during the window, though both share a PHY context; link 1
id in the notification's mac_id field; and whether holding was caused by a missing window at all.

Read after reboot: ItlwmAwdlCtxTeStarted rising with TeRequests, TeFailed 0, ItlwmAwdlTxMcastOk and
UnicastAck rising, phone `Posted peer presence`, no ItlwmFwErrors, and whether the network stutters.
Verification: scripts/test-awdl-ctx.py and all other suites, 57-unit build. NOT hardware tested.
