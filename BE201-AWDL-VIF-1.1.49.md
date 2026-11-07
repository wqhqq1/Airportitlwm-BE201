# AirportItlwm 1.1.49: second channel teardown fix and windows on the peer's schedule

Includes 1.1.48 (llw0 created without waiting in the request), still not hardware tested.

## Second channel test on 1.1.47, 2026-11-06 06:29, Mac on router channel 36, target 149

The corrected sequence works: link 1 moved to PHY 1 on 149 with no fault (Phy2Switches 1, Phy2Err 0). AWDL frames arrived on 149 (RxPhy2 30 in 30 s alone, 28 with one 100 TU window a second, 92 in 20 s with the own queue on) while the AP link on 36 kept 0% gateway loss; gateway RTT rose from 2.5 ms to 26 ms, then 55-59 ms with windows. So the firmware time-shares the two channels. Rate on 149 is low, about one frame a second. No awdl0 neighbor, so own queue TX was never tried.

Turning it off asserted the firmware: 0x2000320F, data1 1, last command 0xC0309 (LINK_CONFIG), Wi-Fi lost for the phase, AWDL latched off for the boot, no panic, Wi-Fi fine later. At that moment one window had started and not ended (TeStarted 49, TeEnded 48), and the own queue (qid 10) was still allocated. The tool turned windows off before the channel, so the driver skipped its window removal (it only removed while the switch was on).

## Change

- Leaving the second channel: remove the window unconditionally, then flush and disable the own queue, then move the link. Which of the two caused the assert is not known; both now go first.
- Windows going off while on the second channel send a remove at once.
- debug.be201_awdl_phy2_te 2: a 64 TU window when the reference peer's schedule has it on the second channel, at most every other slot. 1 keeps the old once-a-second 100 TU window.
- New counters CtxTeRemoved, OwnReleased.
- 开始信道实验.command: finds awdl0 neighbors with a multicast echo, uses mode 2, sends ping6 to a neighbor through the own queue, turns off own queue, then channel, then windows.

Not done: the second channel is not automatic, nothing decides when to use it, and AirDrop or Universal Control over it are untested.
