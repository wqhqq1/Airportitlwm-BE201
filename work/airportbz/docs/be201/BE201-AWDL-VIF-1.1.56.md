# AirportItlwm 1.1.56: the default own queue is actually built

## 1.1.55 result, boot 2026-11-08, phone hotspot 149

The user reported that AirDrop was not faster. The live counters show the switches were on but the own queue was never built:

- **Switches:** `debug.be201_awdl_own_queue` 1, `debug.be201_awdl_txagg` 1, `debug.be201_awdl_own_fix` 3, and ItlwmAwdlSpeedDefault was Yes.
- **Own queue:** OwnSent 0, OwnFixDone 0, OwnQueue -1, OwnErr 0, OwnHeld 0.
- **Data path:** DataTx 132060, all of it on the AP station's management queue (the 4.6 MB/s path).

Cause:
- `setAwdlOwnQueue` queues the own queue task only when a setting changes. `startAWDLAuto` sets the switches at load, so the first AW tick queues the task once.
- At that point there is no AWDL peer yet (`peer_added` 0), so the task returns. After that nothing changed again, so it never ran.
- In the 1.1.53 test the switches were set by hand during a transfer, when a peer was already there, which is why it worked then.

## Change

- **Retry:**
  - `setAwdlOwnQueue` (every AW tick) queues the task again, once a second at most, while the queue is wanted but not active.
  - It does not retry while the queue is held (held queues have their own rebuild), or after an allocation failure (OwnErr).
  - It needs the context in ASSOC, a peer added and TX not tripped.
  - Counter: OwnRetries.
- **Test:** test-awdl-ba checks the retry conditions and that the retry comes before the no-change return.
- **Unchanged:** everything else is as in 1.1.55, including the OpenCore layout check in the build.
