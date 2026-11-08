# AirportItlwm 1.1.59: a slow awdl0 attach at boot no longer kills AWDL for the boot

## 1.1.57 boot 2026-11-08 06:23, phone hotspot 149

The user reported that AirDrop could not send. The second channel was off and no test was running.

What happened:

| Time | Event |
|---|---|
| 06:24:40 | wifip2pd called `APPLE80211_IOC_VIRTUAL_IF_CREATE`. |
| 06:24:50 | It returned 0xe00002d8 (not ready) after the 10 s BSD attach wait. wifip2pd logged "Failed to create interface AWDL ... not ready" and "Unable to create WiFiInterface". |
| 06:24:56 | `awdl0: attached`. |

The driver had already set `awdlFailed`, so every later create request got NotReady. ItlwmAwdlVifFailedStage was 5 (publish) and ItlwmAwdlVifCreateResult 0xe00002d8. awdl0 stayed `flags=8802` (not UP), CtxMode was 0, and no AWDL counter was ever published. Earlier boots attached within 10 s.

## Change

- **Longer wait:** the BSD attach wait in `createAWDLInterfaceGated` is 300 × 100 ms (30 s), up from 10 s. `commandSleep` gives up the gate, as before.
- **Late attach adopted:**
  - The conditions:
    - `awdlFailed` is set;
    - the kept interface now has a BSD interface named awdl*;
    - the request's address matches;
    - AWDL is not stopping.
  - When they all hold, the next create request takes the interface: `markDown`, stage 6, step "ready-late", `awdlFailed` cleared, the name returned, ItlwmAwdlVifLateAdopted counted.
  - This needs no arm.
  - A different address still gets Busy, and no BSD interface yet still gets NotReady.
- **Test:** test-awdl-vif waits 300 sleeps, then covers a still-unattached request, a wrong address, adoption, and a normal later request.
- **Unchanged:** everything else is as in 1.1.58.
