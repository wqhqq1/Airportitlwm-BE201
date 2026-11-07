# BE201 1.1.24: full request log, optional acceptance of set requests

Follow-up to the 1.1.23 arm test (boot 4044ACBD), which created a real awdl0.

## What 1.1.23 showed

CreateResult 0, stage 6, IOSkywalkNetworkBSDClient attached, pool type 1, flags 0. No panic. So type 0 was the blocker and flag 1 is not needed. wifip2pd created `AWDLInterface` and started advertising. Packets stay 0.

Watch unlock got further. Before: error 103, AWDL information unavailable. Now Bluetooth confirmation, key exchange and the ranging key succeed, then sharingd starts AWDL, wifip2pd sends AWDL_PEER_TRAFFIC_REGISTRATION (type 164) for wifid-assisted-discovery, gets EPERM, and unlock fails with error 192, "AWDL network failed to start". Whether that EPERM comes from our handler is not known: the handler returns unsupported, and only a sample of ids was visible.

AWDL_PEER_SERVICE_REQUEST (type 120) returning 6 is not ours: the native set handler is a stub returning an error.

AirDrop: the user reports the Finder sidebar item unchecks itself. sharingd starts before arming, when capability bit 32 is off. Stale capability is the hypothesis, untested.

## Changes

- Every request is appended to `ItlwmAwdlRequestLog` (u16 ids, first 256), with `ItlwmAwdlRequests` as the total.
- New RAM-only sysctl `debug.be201_awdl_vif_accept`. When set, set requests return success and do nothing, so the system shows what it asks for next. This does not implement them. The companion interface create, getters, and link up stay refused.
- The traffic registration's service name is stored, bounded; the peer address is not.
- The test tool sets acceptance, and restarts sharingd after creation.

No radio or data path yet. Accepted requests have no effect on air, so Watch unlock and AirDrop are still expected to fail, later than before.

## Verification

21 suites pass. Not hardware tested.
