# AirportItlwm 1.1.54: AirDrop speed-up on by default, second channel on this Mac's own schedule

## 1.1.53 results, 2026-11-07 23:48, phone hotspot 149

AirDrop Mac to phone in 20 s phases:

| Phase | Speed |
|---|---|
| Baseline | 4.62 MB/s |
| Own queue | 4.45 MB/s |
| Plus fix 1 (MAC 1 no power save) | 4.61 MB/s |
| Plus fix 2 (link 1 QoS and beacon timing) | 4.62 MB/s |
| Plus aggregation | 33.06 MB/s |

- **Aggregation phase:** the TID 0 aggregated queue sent 463726 frames and 463693 finished (463572 of them through block ack notifications, 19384 notifications). There were no firmware errors.
- **TID 15 queue:** it stayed held in every phase, with or without the fixes.
- **Fixes:** it is not known whether they are needed. They were on during the aggregation phase, and a later boot cannot tell, because a fix the firmware has taken stays in effect.
- **After the transfer:** OwnHeld was 1. The 33 frames that never finished counted as held, and before this version that state lasted for the rest of the boot.
- **Family's sequence on that hotspot:** the 16 slots of ItlwmAwdlPayload535 were 149 in slots 0, 2 and 10, channel 6 in slot 8, and 0 in the rest (4 AWs a slot).

## Changes

### Speed-up on by default

`startAWDLAuto` (`be201_awdl_auto`, skipped after a panic) now also sets:
- `debug.be201_awdl_own_queue` to 1,
- `debug.be201_awdl_txagg` to 1,
- `debug.be201_awdl_own_fix` to 3.

This is the combination tested above, and writing 0 from RAM still turns each one off. ItlwmAwdlSpeedDefault records that it happened.

### Held own queue is rebuilt

- **When:** 3 s after a queue counts as held.
- **What happens:** the stuck frames are flushed and the queue is rebuilt.
- **Limit:** rebuilding stops after 4 rebuilds in a row that got nothing through. A rebuild that does carry frames resets that count, and so does a settings change.
- **Counters:** OwnRecovers and OwnRecoverFails.

### The own queue changes peer only when the current peer is quiet

- **Rule:** the move waits until the current peer has had no frame for 1 s.
- **Why:** a move flushes the old peer's frames. With an iPad and an iPhone both active, the last destination can alternate from one 64 ms AW tick to the next.
- **Counter:** OwnQuietSkips counts the moves that waited.

### Second channel follows this Mac's own sequence (test switches, off by default)

- **Slot reporting:** the AW timer runs once per slot start, 64 TU. It now reports three things to the HAL (`setAwdlSlot`):
  - this slot's channel from the family's sequence;
  - the run length of that channel when the slot starts a run (0 inside a run);
  - the sequence's 5 GHz channel.

  The radio switches are applied after that report, on the same tick. A sequence with one channel in every slot gets a run start in every fourth slot.
- **`debug.be201_awdl_phy2=1` (automatic):**
  - Chooses the sequence's 5 GHz channel when the AP is on another channel, and none otherwise.
  - A new choice must hold for 2 s before the link moves.
  - Counters: Phy2Auto, Phy2AutoChanges and SeqChan5.
- **`debug.be201_awdl_phy2_te=3`:**
  - Opens a session-protection window at the first slot of each of this Mac's own runs on the second channel: 64 TU a slot, 2 slots at most.
  - It never opens one while an earlier window still runs.
  - It skips a tick handled more than 16 TU late.
  - Counter: CtxTeOwn.
- **Mode 2** (the reference peer's slots, one at most every 250 ms) is unchanged, for comparison.

## Tools

- **开始信道实验.command:** run on a router that is not on channel 149, during a large AirDrop. It records:
  - AirDrop speed, router ping and awdl0 peer ping;
  - the family's 16-slot sequence;
  - four phases: router only, automatic second channel without windows, mode 2, mode 3.

  The second channel is off again at the end.
- **开始隔空投送实验.command:** two AirDrop sends in one boot, which shows the held-queue rebuild. It changes no switch.

## Checks

- **test-awdl-ba:**
  - `iwx_awdl_te_own_due`: run start, run cap, inside a run, other channel, window still running, late tick.
  - `iwx_awdl_phy2_auto`.
  - Source checks for the defaults (not after a panic), quiet retarget, bounded rebuild, slot-then-switch order and mode 3.
- **test-awdl-vif:** the mock gains `setAWDLSlot`.
