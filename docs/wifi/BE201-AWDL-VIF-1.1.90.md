# AirportItlwm 1.1.90: the second PHY context is 20 MHz

The defaults are the same as in 1.1.88. The ROC switch stays off, and the Bluetooth drivers are unchanged (BlueToolFixup 2.7.12, IntelBTPatcher 2.5.10).

## 1.1.89 result, boot 2026-11-12 08:21, test at 08:25

- **Router:** channel 153 at 80 MHz, encrypted.
- **Before the test:** one firmware error earlier in this boot, `0x20000907` data 2 at PHY_CONTEXT_CMD. Its cause is not known.
- **Baseline:** the phone saw the Mac, but the transfer did not move.
- **Mode 1, P2P_TXRX:**
  - 62 ROCs added, 61 started, 61 ended, 1 failed, 21 of them discovery ROCs. No firmware error.
  - Router ping: 19 ms average.
- **Link moved to 149 with ROC off:**
  - The firmware asserted 2 s in: `0x200008FE` data 145 at PHY_CONTEXT_CMD, the same error as at 07:47.
  - The snapshots rule out an ROC:
    - `ItlwmAwdlFaultRoc` was `0x950120`: nothing pending or running, and the station already removed. The last ROC was mode 1, P2P_TXRX, on 149.
    - `ItlwmAwdlFaultPhy2` was `0x009501`: a move to 149 was running, and the link was still on the AP's PHY.
  - Two faults came before the tool's first 2 s poll. The restart re-armed AWDL and moved the link again.
  - Router ping: 62.5 % loss.

## Reading

- **What the driver sends:** `iwx_get_channel_width` and `iwx_get_ctrl_pos` build the PHY context command from the AP's width (`ni_chw`) and the AP's control position (`ni_chan` against `ic_center_freq1`), whatever channel the context is for.
- **What it sent this time:** link 1's context on 149, beside an 80 MHz AP on 153 (centre 155), went out as 80 MHz with the control channel 1 below the centre.
- **The fault:** that describes an 80 MHz block centred on 151, which does not exist. Its lowest channel would be 145, which is the error's data value.
- **Why other setups worked:**
  - **Solo:** with no AP the context is 20 MHz, and the link worked on 149 (RxPhy2 301).
  - **1.1.86, router on 157:** if that router used 40 MHz (157/161), the same rule gives 149/153 at 40 MHz, a valid block. That router's width was not recorded, so this is consistent but not proven.

## Change

- **Second PHY width:**
  - `iwx_get_channel_width` uses the AP's width only for a context on the AP's own channel (`iwx_phy_takes_ap_width`). Any other channel gets 20 MHz.
  - The control position follows, because it already returns the default for 20 MHz.
  - The AP's own context is unchanged.
  - AWDL action frames are 20 MHz, so receive on 149 does not need more for this test.
- **Fault hold:**
  - A firmware fault while a move of link 1 is queued or running sets `phy2_fault_hold`. Each one counts in `ItlwmAwdlPhy2FaultHolds`.
  - While the hold is set, the tick treats the second-channel switch as 0. The hold clears when the switch reads 0.
  - A restart keeps the hold, so a re-armed AWDL does not repeat the move.
- **ROC tool:** each phase also records the channel, width and control position of the last PHY command, and the fault-hold count.

## Tests

- **test-awdl-ba:**
  - The width rule, and that both PHY command builders use it.
  - The control position follows the width.
  - The fault-hold helper: off, held, released.
  - The hold applies before any move, is set in the fault handler before the error count rises, and is not cleared by a restart.
- **Result:** all 25 suites pass.
