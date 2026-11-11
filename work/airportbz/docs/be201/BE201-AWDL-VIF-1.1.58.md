# AirportItlwm 1.1.58: the automatic second channel picks the channel the AP is not on

## 1.1.57 channel test, 2026-11-08 00:54, router on 36

The family's own sequence on the router was `36 0 149 0 0 0 0 0 6 0 149 0 0 0 0 0`:
- slot 0 is on the AP's channel;
- slots 2 and 10 are on 149;
- slot 8 is on channel 6.

The AirDrop started at the beginning stayed "waiting" for the whole test, and no awdl0 neighbor ever appeared.

| Phase | Result |
|---|---|
| Baseline | Router 2.4 ms. |
| Automatic, no windows | Router 2.3 ms, no counter change. |
| Automatic, mode 2 | Router average 17.6 ms, maximum 145 ms; Phy2Switches 1, 14 windows started and 14 frames received on 149; OwnSent 19, DataTx 182. |
| Automatic, mode 3 | Router 2.4 ms, no counter change. |

Phy2Auto read 0 throughout.

## Causes

- **Automatic choice:**
  - The interface passed only the first 5 GHz channel of the sequence, which was 36, the AP's own channel, so `iwx_awdl_phy2_auto` chose nothing.
  - The link reached 149 only at moments when the sequence did not hold 36, then went back. That is why mode 3 found no window to open.
- **Stale counters:** they were published only from the receive path. With no peer heard, a whole phase could show no change and stale values.

## Change

- **Two candidates:** the interface passes the sequence's first two different 5 GHz channels (`a | b << 8`). `iwx_awdl_phy2_auto` takes the first one that is not the AP's channel. SeqChan5 holds both.
- **Publishing:** `setAwdlSlot` also calls `iwx_awdl_probe_publish`, which stays rate-limited to once a second, so the counters are live on every AW tick.
- **Tool:** 开始信道实验.command turns on the automatic second channel with mode 3 before asking for the send, then runs mode 2, then no windows. Every phase records the sequence, both candidates, the chosen channel and live counters.
- **Tests:** test-awdl-ba covers the router case (36 then 149), publishing from the tick, and the two-channel hand-off.
