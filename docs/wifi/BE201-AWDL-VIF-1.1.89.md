# AirportItlwm 1.1.89: no ROC while link 1 moves between PHY contexts

The defaults are the same as in 1.1.88. The ROC switch stays off, and the Bluetooth drivers are unchanged (BlueToolFixup 2.7.12, IntelBTPatcher 2.5.10).

## 1.1.88 result, boot 2026-11-12 06:00, test at 07:45

- **Router:** channel 153. The Mac's sequence was `149 149 149 0 … 6 149 149 …` in the baseline.
- **Baseline, ROC off:**
  - The phone saw the Mac, but the transfer did not move.
  - There was no awdl0 neighbour.
  - Router ping: 2.2 ms average.
- **Mode 1 with P2P_TXRX:**
  - 56 ROCs added, 55 started, 56 ended, 20 of them discovery ROCs. No failure and no firmware error.
  - RocRxAny 16, but no AWDL frame (RocRxAwdlAny 0).
  - Router ping: 9.4 ms average, 85 ms maximum.
  - The phone did not see the Mac.
- **Mode 4 with P2P_TXRX and `phy2` 1, both switched on at once:**
  - Two setups, 9 ROCs added, 5 started, 3 failed. 3 frames were sent on the AUX queue and all 3 completed.
  - RxPhy2 0 and RocRxDuring 0. In 1.1.86 the same mode with HOTSPOT received 189 frames on 149.
  - **Three firmware asserts, all alike:**
    - Error `0x200008FE`, data 145.
    - The last host command was PHY_CONTEXT_CMD (`0x08`), sequence numbers `0x54` and `0x55`.
    - The driver re-armed AWDL twice (FaultRearms 2). Each re-arm moved the link again and asserted again, then AWDL latched off (TxTripped 1).
    - Phy2Err 35 (EAGAIN) is from a command that failed during a restart.
  - Router ping: 46.7 % loss, 353 ms maximum. Wi-Fi reconnected again and again.
  - The phone saw the Mac on and off, then not at all. The AirDrop failed.
- **After the test:** the router ping was back to 2.1 ms average.

## Reading

- **The assert comes from the link move, not from ROC transmit:**
  - Every assert followed PHY_CONTEXT_CMD, the command that puts link 1's PHY context on 149.
  - In 1.1.86 the same move worked beside HOTSPOT ROCs.
  - With P2P_TXRX, ROCs on 149 were queued or running when the move was sent: mode 1 had just run, and mode 4 sends a new ROC at every slot start.
  - Both the tool and the driver let the move and the ROCs overlap. Nothing showed whether an ROC was running at the moment of the assert.
- **The re-arm made it worse:** the move was repeated after each restart, so one bad combination cost three router disconnects.

## Change

- **Driver:**
  - **No ROC during a move:**
    - Queuing a move of link 1 sets `phy2_moving`. The task clears it when the move ends, and so does a firmware restart.
    - While `phy2_moving` is set, the ROC tick sends no new ROC. Each tick it waits counts in RocPhyHolds.
    - The move first removes an ROC that is pending or running and waits for the answer. Each removal counts in RocPhyCancels.
  - **Fault snapshot:** at each firmware error the driver records what the ROC test and link 1 were doing.
    - `ItlwmAwdlFaultRoc`:
      - bit 0: pending
      - bit 1: running
      - bit 2: station added
      - bits 4–7: activity
      - bits 8–11: mode
      - bits 16–23: channel
    - `ItlwmAwdlFaultPhy2`:
      - bit 0: move queued or running
      - bits 8–15: wanted channel
      - bits 16–23: current channel, 0 for the AP's
- **ROC tool:**
  - **Phases:**
    1. Baseline.
    2. Mode 1 with P2P_TXRX.
    3. With ROC off, `phy2` 1 moves the link to 149, then 20 s of receive with no ROC.
    4. Only if the link is on 149: mode 4 with P2P_TXRX for 90 s, while the user sends the file again.
  - **On a firmware error:** the tool polls every 2 s. On the first new firmware error it switches ROC and `phy2` off at once, and it skips the later phases.
  - **Each phase line adds:** the link's channel and Phy2Err. After a fault it also gives the error, the command, the data and the two snapshots.
- **Unchanged:**
  - ROC, `phy2` and llw0 stay off unless the tool turns them on.
  - The 1.1.88 defaults, the installer and the boot arguments.

## Tests

- **test-awdl-ba:**
  - Fault snapshot encoding.
  - The task marks the move around it.
  - A running ROC is removed before the link leaves its PHY context, and the removal waits for its answer.
  - Queuing a move holds ROCs before the task runs.
  - No ROC is added during a move.
  - A firmware restart clears the mark.
  - The fault snapshot is taken before the error count rises.
  - The tool moves the link before mode 4 and stops on the first new firmware error.
- **Result:** all 25 suites pass.
