# AirportItlwm 1.1.82: DMA pages come back after a refused queue

## 1.1.81 result, boot 2026-11-10 17:44

- **4 GB AirDrop, 17:49–17:52:**
  - It held the Data schedule from 17:49:36 to 17:52:03. There was no Idle and no Low Power, and the average was about 27 MB/s.
  - The Mac was on a channel-149 network for this transfer.
- **Network changes:** from 17:44 to 18:22, en1 changed networks about ten times, between channel 60 (beacon 100) and channel 149 (beacon 300).
- **ROC test at 18:45, on the channel-60 router:**
  - In every phase: AirDrop 0.00 MB/s, no AWDL peers in the family, and RocSetups 0. The ROC was never set up.
  - The user answered "sees Mac, transfer not moving" in every phase.
- **State after the test:**

  | Property | Value | Meaning |
  |---|---|---|
  | ItlwmMldDataQueues | 0 | no data queue for the AP |
  | ItlwmMldTxqErr | 12 (ENOMEM) | AP data queues could not be allocated |
  | ItlwmAwdlOwnErr | 12 | AWDL own queue failed the same way |
  | PeerStations | 0 | |
  | FwErrors | 1 (0x20000A07, command 0x108) | one firmware error |
  | FaultRearms | 1 | |

## Cause

- **How allocation fails:** queue setup (`iwx_tvqm_enable_txq`) returns ENOMEM when `ItlDmaArena::allocate` finds no free run in the 64 MiB pool.
- **Where the pool leaked:**
  - When that setup failed after the command was submitted (`submitted`), the failure path called `deferRecycling()`.
  - That sets `recyclingDeferred` for the whole arena. From then on, every `deallocate` in the driver only marked its pages Retired.
  - `reclaim()` returns them only at the next device stop, with bus mastering off.
- **Why it ran out:** a network change or a station switch does not stop the device. Each later ring free stayed out of use:
  - every AP queue reallocation on reconnect;
  - every own-queue release, retarget and recovery;
  - every peer queue.

  Over ten network changes and twelve AWDL context rebuilds, the pool ran out.
- **What triggered the defer:** queue setups do fail like this, for example a queue the firmware hands back while a live owner still holds it (the 1.1.73 refusal path).
- **Why it was hidden:** the arena counts used pages, the high-water mark and failures, but published none of them.

## Change

- **`ItlDmaArena::beginRetire()` / `endRetire()`:** a depth counter. While it is open, `deallocate` retires pages as before. Outside it, pages go back at once. `deferRecycling()` remains only for the firmware-load failure path, where a dead firmware may still read anything.
- **Failure path in `iwx_tvqm_enable_txq`:**
  - Opens the scope only around freeing the failed ring.
  - Only when the command was submitted and the error is not ENOSPC, EBUSY or EAGAIN. A full command ring returns ENOSPC before anything is queued.
- **Pool properties, once a second with the history sample:** ItlwmDmaUsedKiB, ItlwmDmaHighKiB, ItlwmDmaFailures, ItlwmDmaRetiredKiB and ItlwmDmaDeferred.
- **ItlwmAwdlRocBlocked:** while the ROC switch is on, one bit per readiness condition still missing:

  | Bit | Missing condition |
  |---|---|
  | 0 | context mode is not 6 |
  | 1 | context stage below ACTIVE |
  | 2 | solo AWDL |
  | 3 | AWDL tripped |
  | 4 | not in RUN |
  | 5 | AP port not valid |
  | 6 | WCL teardown pending |
  | 7 | MLD TX queues not active |
  | 8 | shutdown |
  | 9 | hardware error |
  | 10 | TX flush |

  It is published on change. `iwx_awdl_roc_ready` is now `!iwx_awdl_roc_blocked`.
- **ROC tool:** each phase also records RocBlocked, the pool, MldDataQueues and OwnErr.
- **Unchanged:** the 1.1.81 stats report, the 1.1.80 scan hold and history, the ROC switch (off), llw0 off, and the speed-up, UMI and cache answers.

## Tests

- test-awdl-ba:
  - no `deferRecycling` in the queue failure path;
  - the retire scope encloses the ring free and skips transient errors;
  - `deallocate` retires inside a scope or after a defer;
  - `reclaim` keeps the bus-master guard and counts retired pages;
  - the blocked mask covers every former readiness condition, and the properties are published.

All 24 suites pass.
