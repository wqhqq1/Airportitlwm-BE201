/* SPDX-License-Identifier: ISC
 * BE201 AWDL radio feasibility work. be201_awdl_probe counts received frames and
 * follows the timing of nearby peers; be201_awdl_tx also transmits. Both are off
 * by default. Published values are numeric, except the random per-boot AWDL
 * address; peer addresses stay in RAM. Wire format: public OWL protocol analysis.
 */
#ifndef IWX_AWDL_PROBE_H
#define IWX_AWDL_PROBE_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define IWX_AWDL_PROBE_MAX_SENDERS 32
#define IWX_AWDL_TIMING_PEERS 8
#define IWX_AWDL_TIMING_MAX_GAP_US 10000000u
#define IWX_AWDL_TU_US 1024u
#define IWX_AWDL_FRAME_MAX 384u
/* TLVs the system's AWDL manager builds; firmware adds the action header, sync and channel TLVs. */
#define IWX_AWDL_NATIVE_TLV_MAX 1024u
#define IWX_AWDL_NATIVE_FRAME_MAX 1400u
#define IWX_AWDL_NATIVE_MIF_INTERVAL_US 224000u
#define IWX_AWDL_HDR_LEN 24u
#define IWX_AWDL_ACTION_LEN 16u
#define IWX_AWDL_PSF_INTERVAL_US (110u * IWX_AWDL_TU_US)
#define IWX_AWDL_SLOW_INTERVAL_US 1000000u
/* Transmit only right after hearing a peer, while it is listening on this channel. */
#define IWX_AWDL_TX_WINDOW_US 20000u
#define IWX_AWDL_PEER_STA_MAX 4u
#define IWX_AWDL_PEER_MIN_RSSI (-65)
/* A station not heard from for this long may give its place to a new nearby peer (1.1.77). */
#define IWX_AWDL_PEER_IDLE_US 3000000u
#define IWX_AWDL_SELF_METRIC 60u
/* Far below the ring's high mark, so held frames can never stop the AP's traffic. */
#define IWX_AWDL_TX_MAX_QUEUED 8
/* Data may drop: TCP recovers. Still well below the mark that would stop the AP's traffic. */
#define IWX_AWDL_DATA_MAX_QUEUED 32
/* Block ack the peers ask for. No more than the firmware's usual window for a legacy session. */
/* The family's peer cache: the request's operation at +4, the answer in event 51, read from 24G824. */
#define IWX_AWDL_CACHE_REQ_DELETE 2u
#define IWX_AWDL_CACHE_EVENT 51u
#define IWX_AWDL_CACHE_EVENT_ADDED 1u
#define IWX_AWDL_CACHE_EVENT_DELETED 3u
#define IWX_AWDL_CACHE_EVENT_LEN 0x1d0u
/* reportDataPathEvents on 24G824: case 69 is processUnicastAfStatus. Address at +0, status at +6, 0 is acked. */
#define IWX_AWDL_UMI_EVENT 69u
#define IWX_AWDL_UMI_EVENT_LEN 64u
#define IWX_AWDL_UMI_DONE_MAX 8u
#define IWX_AWDL_BA_MAX 4u
/* Well under the 11454 byte MPDU this phone's VHT capability allows, and the 7991 of a smaller one. */
#define IWX_AWDL_AMSDU_MAX_BYTES 7900u
#define IWX_AWDL_AMSDU_MAX_FRAMES 5u
/* Failures with no success at all: the peer or the firmware will not take these. */
#define IWX_AWDL_AMSDU_GIVE_UP 16u
#define IWX_AWDL_BA_WINDOW 64u
#define IWX_AWDL_BA_STATUS_OK 0
#define IWX_AWDL_BA_STATUS_REFUSED 37
/* A tenth of the time at most, and only while peers are heard. */
#define IWX_AWDL_TE_DURATION_TU 100
#define IWX_AWDL_TE_INTERVAL_US 1000000u
/* Windows that follow the peer: one 64 TU slot at most every 250 ms. Every other slot (1.1.49) took the AP RTT to 139 ms. */
#define IWX_AWDL_TE_SLOT_TU 64u
#define IWX_AWDL_TE_SLOT_GAP_US 250000u
/* Mode 3: windows in this Mac's own advertised slots on the second channel, from the AW timer at each slot start.
 * A run of that channel's slots gets one window, two slots (128 TU) at most so the AP never loses more in a row. */
#define IWX_AWDL_OWN_SLOT_TU 64u
#define IWX_AWDL_OWN_SLOT_RUN_MAX 2u
/* Automatic second channel: a new choice must hold this long before the link moves. */
#define IWX_AWDL_PHY2_AUTO_STABLE_US 2000000u
/* The own queue moves to another peer only after its current peer had no frame for this long. */
#define IWX_AWDL_OWN_QUIET_US 1000000u
/*
 * The own queue serves one peer. With Universal Control or other light traffic to an iPad, the quiet rule kept it there
 * and an AirDrop to the iPhone went out on the AP queue without aggregation, about 4 MB/s (2026-11-10, 4 peers, 11
 * retargets). Bytes decide too: over a 500 ms window, a peer taking at least 512 KB and four times the current peer's
 * bytes gets the queue (1.1.77).
 */
#define IWX_AWDL_OWN_BULK_WINDOW_US 500000u
#define IWX_AWDL_OWN_BULK_BYTES (512u * 1024u)
/*
 * AWDL bulk data for the scan gate (1.1.79): at least this many unicast bytes to peer stations over the last closed
 * window and the one being counted, with the last window closed no more than 1.5 s ago.
 */
#define IWX_AWDL_SCAN_DEFER_BYTES (256u * 1024u)
#define IWX_AWDL_SCAN_DEFER_STALE_US 1500000u
/*
 * 1.1.80: the gate also holds for this long after the last bulk data. Once a transfer slowed for any reason, its byte
 * count fell, the scans came back to back and the stall went on (2026-11-10 16:12 boot: 54 real scans, 7 deferred).
 */
#define IWX_AWDL_SCAN_HOLD_US 10000000u
/* Per-second history for stalls (1.1.80): 90 one-second samples, newest last when read from the property. */
#define IWX_AWDL_HIST_LEN 90u
enum { IWX_AWDL_HIST_OWN_ACTIVE = 1, IWX_AWDL_HIST_OWN_HELD = 2, IWX_AWDL_HIST_BGSCAN = 4, IWX_AWDL_HIST_TX_TIMER = 8,
       IWX_AWDL_HIST_SOLO = 16, IWX_AWDL_HIST_DATA_STALLED = 32, IWX_AWDL_HIST_BULK = 64, IWX_AWDL_HIST_SCAN_HELD = 128 };
struct iwx_awdl_hist {
    uint32_t t_s, own_sent, own_ok, own_agg_fail, own_ba_notifs, tx_busy, data_stalls, own_recovers, mcast_sent;
    uint16_t own_queued, ap_queued;
    uint32_t flags;
};
static inline bool iwx_awdl_bulk_active(const struct iwx_awdl_probe *p, uint64_t now_us);
/* A held own queue (frames that never finish, often the tail left when a peer goes) is freed and rebuilt after this
 * long, again and again while rebuilds still carry frames; after this many rebuilds in a row with nothing done, never. */
#define IWX_AWDL_OWN_RECOVER_US 3000000u
#define IWX_AWDL_OWN_RECOVER_MAX 4u
/* A wanted queue that was never made (no peer yet when the switch came on) is tried again this often. */
#define IWX_AWDL_OWN_RETRY_US 1000000u
/* With no infrastructure network: how long the driver must sit idle before AWDL runs on its own, and its channel. */
#define IWX_AWDL_SOLO_IDLE_US 5000000u
#define IWX_AWDL_SOLO_CHAN 149u
/* Firmware faults that the restart may recover from; the next one keeps AWDL off for the boot (1.1.73). */
#define IWX_AWDL_FAULT_REARM_MAX 2u
#include <sys/errno.h>
/*
 * Errors that only say the host command ring was busy at that moment (iwx_send_cmd: ring full or the slot still
 * owned by a waiting caller). The own queue tries again a second later instead of giving up for the boot (1.1.76).
 */
static inline bool iwx_awdl_err_transient(int err) {
    const int e = err < 0 ? -err : err;
    return e == ENOSPC || e == EBUSY || e == EAGAIN;
}
/*
 * Remain on channel for the AWDL sequence's other 5 GHz channel (1.1.75 test, debug.be201_awdl_roc, off by default):
 * an AUX station and its queue carry the frames, node_addr is the AWDL address. Mode in the low nibble, activity in
 * the next: 1 ROC only, 2 also AWDL management and multicast frames on the AUX queue, 3 also unicast data.
 */
#define IWX_AWDL_ROC_STA_ID 12u
#define IWX_AWDL_ROC_TID 8u
/*
 * 1.1.96: a sequence slot is one extended AW, 64 TU (the AW timer runs at 65536 us). 1.1.75-1.1.95 took 16 TU, so a
 * run of six 149 slots (384 TU) asked for 96 TU; with one ROC per run that left this Mac on 149 for 7.9 % of the
 * 1.1.95 mode 4 test (173 ROCs x 41.3 ms in 90 s). ROCs now cover at most IWX_AWDL_ROC_RUN_MAX_SLOTS slots of each run
 * (about 262 ms, so the AP keeps its beacons), chained: each end notification adds the next while covered time is left.
 */
#define IWX_AWDL_ROC_SLOT_TU 64u
#define IWX_AWDL_ROC_SLOT_US 65536u
#define IWX_AWDL_ROC_MAX_TU 256u
/*
 * 1.1.99 tried 6 slots (about 393 ms). 2026-11-12 23:17, router on 2.4 GHz channel 6: router ping 553 ms average and
 * 6.8 s at most, then 58 % loss and the AP link dropped in the next phase. 1.2.0: back to 4 (262 ms), which kept the
 * router at 0 % loss and 57 ms at 22:49.
 */
/*
 * 1.2.2: 5 slots (about 328 ms). 2026-11-13 17:23 (1.2.1, router on 44, family timing): 1.56 MB/s with the family's
 * sequence at 12-14 of 16 slots on 149 and this Mac there 45 % of the time; router 0 % loss, 51 ms average.
 */
/*
 * 1.2.11: 6 slots (about 393 ms), then 2 left to the AP. 2026-11-13 22:50 (1.2.10, router on 36): 1.56 and 1.63 MB/s
 * at 5 slots, 1.80 MB/s at 6 (149 share 62-64 % against 65 %, 1.70 against 1.85 frames per ms of dwell), router 0 %
 * loss in both, 182-191 ms against 294 ms at most.
 */
/*
 * 1.2.12: 7 slots (about 459 ms). 2026-11-14 08:02 (1.2.11, router on 36): 1.88 MB/s at 6 slots (149 share 63 %),
 * 2.07 MB/s at 7 (71 %), router 0 % loss in both, 176 against 206 ms at most.
 */
#define IWX_AWDL_ROC_RUN_MAX_SLOTS 7u
#define IWX_AWDL_ROC_CHAIN_MIN_US 15000u
/*
 * 1.1.97: no ADD sooner than this after the last ROC ended, failed or was removed. 2026-11-12 21:21 (1.1.96, R1 mode 1,
 * P2P_TXRX): the firmware asserted 0x20103620 on ROC_CMD (data 2, the activity) 18 s in, with an ADD just sent and none
 * running. 1.1.96 was the first version to add from the end notification itself, within a millisecond of it; the
 * firmware had run 65 ROCs of up to 80 TU there in full, so the length was not the cause. Linux never re-adds an
 * activity that fast: its roc_done work flushes and removes the AUX station first.
 */
#define IWX_AWDL_ROC_READD_US 10000u
static inline uint32_t iwx_awdl_roc_readd_wait(uint64_t now_us, uint64_t last_end_us, uint32_t guard_us)
{
    if (!last_end_us || now_us >= last_end_us + guard_us)
        return 0;
    return now_us <= last_end_us ? guard_us : uint32_t(last_end_us + guard_us - now_us);
}
/* Linux keeps an ROC beside an association under the DTIM interval less 20 TU (iwl_mvm_roc_duration_and_delay). */
#define IWX_AWDL_ROC_DTIM_GUARD_TU 20u
#define IWX_AWDL_ROC_DELAY_TU 16u
/* Switch flags above the mode and activity (1.1.96 probes): an 80 MHz ROC, and no DTIM clamp. */
#define IWX_AWDL_ROC_F_80MHZ 0x100u
#define IWX_AWDL_ROC_F_NO_DTIM 0x200u
/*
 * 1.1.99 ran mode 4 unclamped by default (0x400 asked for the clamp). 23:17 showed the clamp is the faster one: 0.97
 * frames per ms of dwell (15261 frames in 15.8 s, 72 ms ROCs) against 0.15 unclamped (4205 in 27.2 s, 148 ms ROCs),
 * with frames waiting in both. An ROC longer than the beacon interval seems to be broken up by the firmware for the
 * AP's beacons. 1.2.0: the clamp everywhere unless 0x200; 0x400 is still accepted and changes nothing.
 */
#define IWX_AWDL_ROC_F_DTIM 0x400u
/*
 * 1.2.1 timed mode 4 by the phone's own schedule by default. 17:23 showed both clocks agree (slot index difference 0,
 * boundary 2.6 ms apart on average) and the family-timed phase moved 1.56 MB/s. 1.2.2: the family's timing again by
 * default; this flag asks for the phone's.
 */
#define IWX_AWDL_ROC_F_PHONE 0x800u
/*
 * 1.2.3: the ROC's millisecond timer. 2026-11-13 17:39 (1.2.2, router on 60, idle sequence) repeated 17:03: AUX unicast
 * 0 of 41, 39 failed after their ROC with few retries; the phone's sequence had 149 in runs of 3 and 4. In both runs few
 * frames were waiting and all went into the ring at the start notification; in every run with a transfer under way,
 * new frames kept arriving and the same path delivered 99.9 %. Taken (not proven): one doorbell at the notification
 * itself can be missed. Now held frames go IWX_AWDL_ROC_START_DELAY_US after the start, and while an ROC runs the timer
 * rewrites the AUX write pointer when frames are queued and none completed for IWX_AWDL_ROC_KICK_MS.
 */
#define IWX_AWDL_ROC_START_DELAY_US 2000u
#define IWX_AWDL_ROC_KICK_MS 6
/*
 * 1.2.3: no new ROC for IWX_AWDL_ROC_BMISS_PAUSE_US after the firmware reports this many beacons missed in a row from
 * the AP. 17:39: 70 % router ping loss in the 80 MHz phase, then the firmware asserted on ROC_CMD (0x20103620, data 2)
 * 42 ms after the last ROC ended, and the router link was gone. An ROC covers at most about 3 beacons.
 */
/*
 * 1.2.4: be on 149 when the phone's slot begins. 2026-11-13 19:20 (1.2.3, router on 2.4 GHz channel 5, idle sequence):
 * AUX unicast data 0 of 145, 104 and 278, almost all failed after their ROC; the ring never sat stuck (0 kicks in 2412
 * timer checks), and for most failures the phone's timing was stale (no sync frame from it for 2 s): the phone was not
 * there when we were. Idle, an AWDL node is only sure to be on a channel in the AW at the start of its slot (16 TU),
 * while our ROC began about 5.5 ms after our slot tick and held frames went 2 ms after that. Now, when the next slot
 * starts a 149 run and this one is not on 149, the ROC is asked for IWX_AWDL_ROC_PRE_LEAD_US before the boundary, and
 * held frames go IWX_AWDL_ROC_AW_RELEASE_US after the boundary. Switch flag 0x1000 turns this off (comparison).
 */
#define IWX_AWDL_ROC_PRE_LEAD_US 12000u
#define IWX_AWDL_ROC_AW_RELEASE_US 500u
#define IWX_AWDL_ROC_F_NO_PRE 0x1000u
/* 1.2.4: when the held frames of an ROC that just started may go: 2 ms after its start, or just after the slot boundary
 * it was asked to be early for, whichever is later. */
static inline uint64_t iwx_awdl_roc_release_at(uint64_t start_us, uint64_t aw_start_us)
{
    if (!aw_start_us)
        return start_us + IWX_AWDL_ROC_START_DELAY_US;
    /* Early: just after the boundary. Late for it: the AW is running already, so at once. */
    return start_us < aw_start_us ? aw_start_us + IWX_AWDL_ROC_AW_RELEASE_US : start_us + IWX_AWDL_ROC_AW_RELEASE_US;
}
/*
 * 1.2.5: the cause of the idle failures (found by the Fable 5.2 review of all runs, 2026-11-13). sendAwdlData built QoS
 * TID 0 frames for the own-queue peer whenever that queue was active and aggregated. In mode 4 such a frame was routed
 * to the AUX queue and then moved by iwx_tx's QoS-to-TID mapping onto the router's TID 0 queue: it went out on the
 * router's channel after the ROC, to a phone on 149 (status 0x83, after the ROC, no frame ever seen sitting in the AUX
 * ring by the 1.2.3 watchdog, while non-QoS unicast management frames in the same phases were acknowledged). Runs
 * worked when the own queue happened to be held (non-QoS frames). Mode 4 now sends non-QoS data, and the mapping leaves
 * AUX frames alone. A QoS TID 0 frame on AUX would also meet the phone's block-ack window for the own queue.
 */
static inline bool iwx_awdl_data_qos(bool own_active, bool own_agg, bool own_peer, bool roc_aux)
{
    return own_active && own_agg && own_peer && !roc_aux;
}
/* 1.2.5: no new ROC for this long after the firmware reports one it could not start (the asserts followed those). */
#define IWX_AWDL_ROC_FAIL_PAUSE_US 500000u
/*
 * 1.2.6: speed. 2026-11-13 21:39 (1.2.5, router on 36, from idle): the transfer ran at 0.98-1.43 MB/s, AUX unicast
 * 38709/3 and 42848/1, but the radio sent only 23-29 % of the ROC time (171 us per frame) at 1.35-1.71 frames per ms,
 * and flushes stopped on the full ring 10 times as often as on the ROC rule: per-frame overhead in the firmware. An
 * A-MSDU carries up to IWX_AWDL_AMSDU_MAX_FRAMES packets in one frame. Through AUX it uses IWX_AWDL_ROC_AMSDU_TID, a TID
 * with no block-ack agreement, so the phone's TID 0 window for the own queue does not see it.
 */
#define IWX_AWDL_ROC_AMSDU_TID 3u
static inline uint32_t iwx_awdl_roc_run_max(uint32_t want)
{
    (void)want;
    return IWX_AWDL_ROC_RUN_MAX_SLOTS;
}
/*
 * 1.2.12: a flag for 1 slot to the AP between pieces. 1.2.14: 1 slot by default, the flag gives 2 back. 2026-11-14 08:34
 * (1.2.13, router on 36, to the iPhone): 2.22 MB/s at 1 slot (149 share 77 %) against 1.31 MB/s at 2 (60 %), router
 * 0 % loss in both, 85 against 64 ms average, 340 against 305 ms at most.
 */
#define IWX_AWDL_ROC_F_GAP1 0x2000u
/*
 * 1.2.15: 2 slots to the AP by default again, for every day (on at boot): 08:55 (1.2.14, to the iPhone) 2.28 MB/s at 2
 * slots (70 %) with the router at 71 ms average, against 2.22 MB/s at 1 slot (77 %) and 85 ms at 08:34.
 */
/*
 * 1.2.15: the value cross-channel AirDrop takes at boot (be201_awdl_xchan): mode 4, P2P_TXRX, and this flag, which
 * keeps it off while the AP is on 2.4 GHz (1.1.99, router on channel 6: 553 ms ping, then the AP link dropped).
 */
#define IWX_AWDL_ROC_F_AUTO 0x10000u
#define IWX_AWDL_ROC_DEFAULT (0x24u | IWX_AWDL_ROC_F_AUTO)
/*
 * 1.2.11: the AUX queue on IWX_AWDL_ROC_AMSDU_TID instead of IWX_AWDL_ROC_TID, so a QoS A-MSDU leaves on a queue of its
 * own TID. 22:50 (1.2.10): air (data + ACK) was 171 us of each 588 us per frame, with no retries (RocTxOkTries 0) and
 * the ring full: most of the time per frame is outside the air, so packets per frame is the lever. The AUX station has
 * no peer address, so no block ack and no A-MPDU; an A-MSDU is the one way to put more than one packet in a frame.
 * 22:38 (1.2.9) sent its A-MSDUs, QoS TID 3, on the TID 8 queue: 1 of 6 completed and the firmware asserted.
 */
#define IWX_AWDL_ROC_F_TID3 0x8000u
static inline uint8_t iwx_awdl_roc_tid(uint32_t want)
{
    return (want & IWX_AWDL_ROC_F_TID3) ? uint8_t(IWX_AWDL_ROC_AMSDU_TID) : uint8_t(IWX_AWDL_ROC_TID);
}
/* 1.2.11: A-MSDUs sent since the last ROC end with none completing: the queue is stuck, A-MSDU stops for the boot. */
#define IWX_AWDL_ROC_AMSDU_STUCK 4u
static inline bool iwx_awdl_amsdu_stuck(uint32_t sent, uint32_t done, uint32_t sent_mark, uint32_t done_mark)
{
    return done == done_mark && sent - sent_mark >= IWX_AWDL_ROC_AMSDU_STUCK;
}
#define IWX_AWDL_ROC_BMISS_MAX 6u
#define IWX_AWDL_ROC_BMISS_PAUSE_US 2000000u
static inline bool iwx_awdl_roc_bmiss_paused(uint64_t now_us, uint64_t until_us)
{
    return until_us && now_us < until_us;
}
/* 1.2.3: the timer's verdict on the AUX ring: kick when frames sit queued with the tail where it was last time. */
static inline bool iwx_awdl_roc_kick_due(uint32_t queued, uint32_t tail, uint32_t last_tail, bool active)
{
    return active && queued && tail == last_tail;
}
/* 1.2.2: multicast (sync frames) may queue this far past the ring cap: 232 were dropped on a full ring at 17:23. */
#define IWX_AWDL_ROC_MCAST_EXTRA 16u
/* 1.2.1: the longest wait for the phone's run to start once an ROC is on 149. */
#define IWX_AWDL_ROC_PEER_WAIT_MAX_US 80000u
static inline bool iwx_awdl_roc_no_clamp(uint32_t want)
{
    return (want & IWX_AWDL_ROC_F_NO_DTIM) != 0;
}
/*
 * 1.1.92 host hold for mode 4: frames, how long one may wait, and how much of an ROC must be left to send. 1.1.96:
 * 101 held, 28 sent and 73 expired at 16 frames and 300 ms in the 1.1.95 test; now 128 frames and 1 s, and the AUX
 * ring takes up to IWX_AWDL_ROC_TX_MAX_QUEUED while an ROC runs (8 outside one, as before).
 */
/*
 * 1.1.99: 256 frames, and the family's queue waits from IWX_AWDL_ROC_HOLD_HIGH until the hold is down to
 * IWX_AWDL_ROC_HOLD_LOW (iwx_awdl_data_gate). 2026-11-12 22:49 (1.1.98, mode 4, 60 s): 0.15 MB/s; 5707 of 5708 AUX
 * unicast data acknowledged, but 432 frames dropped because the AUX ring was full while an ROC ran, and about 18
 * frames per ROC: TCP lost about 7 % and never opened its window. A full ring and a non-empty hold now keep the frame.
 */
#define IWX_AWDL_ROC_HOLD_MAX 256u
#define IWX_AWDL_ROC_HOLD_HIGH 192u
#define IWX_AWDL_ROC_HOLD_LOW 64u
#define IWX_AWDL_ROC_HOLD_US 1000000u
#define IWX_AWDL_ROC_TX_MARGIN_US 6000u
/*
 * 1.2.0: 64 frames while an ROC runs (32 in 1.1.99), refilled straight from each completion. A frame still queued at
 * the ROC's end comes back to the front of the hold (1.1.98), so a deeper ring costs order nothing.
 */
#define IWX_AWDL_ROC_TX_MAX_QUEUED 64u
/*
 * 1.1.98: a unicast frame the firmware dropped at an ROC's end goes back into the hold for the next ROC, at most
 * IWX_AWDL_ROC_REQUEUE_MAX times. 2026-11-12 21:40 (1.1.97, mode 4, 60 s): 42 AUX unicast, 8 acknowledged; 32 of the
 * 34 failures completed after their ROC had ended (RocTxFailOut), all long-limit 0x83, with 45 retries over 34 frames:
 * the firmware failed the frames still queued when the ROC ended, not frames the phone did not acknowledge.
 */
#define IWX_AWDL_ROC_REQUEUE_MAX 3u
#define IWX_AWDL_ROC_REQUEUE_TRIES 2u
/*
 * 1.2.17: a unicast frame the peer did not acknowledge while the ROC ran gets one more turn, in front of newer frames.
 * 2026-11-14 12:04 (iPad, 1.2.16): 4-9 such failures a minute whatever the traffic (RocTxFailIn), 2.7 % of 338 frames
 * in the first minute against 0.01 % of 69 400 with the iPhone. At that loss QUIC stays near 0.01 MB/s; a retry in
 * the same or the next ROC turns most of them into delay.
 */
#define IWX_AWDL_ROC_REQUEUE_IN_MAX 2u
static inline bool iwx_awdl_roc_requeue_ok(uint32_t mode, bool active, bool ok, uint32_t retries, uint32_t requeues)
{
    if (mode < 4 || ok)
        return false;
    if (active)
        return requeues < IWX_AWDL_ROC_REQUEUE_IN_MAX;
    return retries <= IWX_AWDL_ROC_REQUEUE_TRIES && requeues < IWX_AWDL_ROC_REQUEUE_MAX;
}
#define IWX_AWDL_ROC_STALE_US 1000000u
#define IWX_AWDL_ROC_SETUP_US 1000000u
/*
 * Discovery ROC (1.1.85): with no AWDL frame heard for IWX_AWDL_ROC_HEARD_US, one ROC of IWX_AWDL_ROC_DISC_TU on the
 * sequence's other 5 GHz channel every IWX_AWDL_ROC_DISC_GAP_US. 2026-11-11 15:39: 36 slot ROCs of 16 TU on 149
 * started and ended and heard nothing (RocRxDuring 0): without a heard peer the AW timing is free-running, and a
 * one-slot ROC rarely meets the phone. 120 TU covers more than one PSF period (110 TU in the family log).
 */
#define IWX_AWDL_ROC_HEARD_US 2000000u
#define IWX_AWDL_ROC_DISC_TU 120u
#define IWX_AWDL_ROC_DISC_DELAY_TU 64u
#define IWX_AWDL_ROC_DISC_GAP_US 1000000u
/*
 * Mode 4 (1.1.86): as 3, but AWDL frames wait on the AUX queue between ROCs too. 2026-11-11 15:53: with the AWDL link
 * on the AP's PHY, 139 discovery ROCs of 120 TU on 149 heard no AWDL frame (RocRxAwdlAny 0, RocRxAnyChan 31 of 3729),
 * while the link on a 149 PHY received AWDL there (RxPhy2 301 at boot, solo). The tool pairs mode 4 with phy2 1: the
 * link on 149 passes the phone's frames, ROC takes the radio there, and the own queue on that link never sends.
 */
static inline uint32_t iwx_awdl_roc_mode(uint32_t v) { return (v & 15u) <= 4u ? (v & 15u) : 0u; }
/* Frames take the AUX queue only while an ROC runs, or always in mode 4. */
static inline bool iwx_awdl_roc_routes(uint32_t mode, bool active) { return active || mode >= 4; }
/*
 * Modes that send (2 and up) always use P2P_TXRX (1.1.87). 2026-11-11 16:08: the tool picked HOTSPOT (0) for modes 2-4
 * and the firmware asserted three times (0x20103620, last host command ROC_CMD 0x23030e), AWDL latched off and the
 * router link dropped. With P2P_TXRX the same modes ran 160+ ROCs with AUX transmit and no error (15:53), and mode 1
 * with HOTSPOT, which sends nothing, had none either.
 */
static inline uint32_t iwx_awdl_roc_activity(uint32_t v) {
    return iwx_awdl_roc_mode(v) >= 2 ? 2u : (v >> 4) & 3u;
}
/* Whether a frame of this AWDL kind (1 multicast, 2 unicast) leaves on the AUX queue while an ROC runs. */
static inline bool iwx_awdl_roc_takes(uint32_t mode, uint8_t awdl_kind, bool mgmt) {
    return mode >= 3 ? awdl_kind != 0 : (mode == 2 && (awdl_kind == 1 || (awdl_kind && mgmt)));
}
/* Duration of an ROC for a run of this many 16 TU slots; 0 for no ROC. */
static inline uint32_t iwx_awdl_roc_duration(uint32_t run) {
    const uint32_t tu = run * IWX_AWDL_ROC_SLOT_TU;
    return tu > IWX_AWDL_ROC_MAX_TU ? IWX_AWDL_ROC_MAX_TU : tu;
}

static const uint8_t iwx_awdl_bssid[6] = {0x00, 0x25, 0x00, 0xff, 0x94, 0x73};

struct iwx_awdl_timing_peer {
    uint16_t hash;
    uint8_t valid;
    uint32_t gp2;
    uint32_t boundary;
};

struct iwx_awdl_sync {
    uint8_t valid, action_version, version, presence, master_channel, height;
    uint8_t encoding, chan_aux;
    uint8_t reference[6], master[6];
    uint16_t aw_period, af_period, ttn, aw_seq;
    uint32_t master_metric, master_counter, gp2;
    uint64_t host_us;
    /* The reference's channel for each slot of its sequence; 0 is a slot it sleeps through. */
    uint8_t seq[16], seq_valid;
    /*
     * 1.2.13: the sequence of the peer unicast data goes to (iwx_awdl_note_dest), kept apart from the reference, which
     * any sender of the cluster overwrites. 2026-11-14 07:55 and 08:14 (router on 36): AirDrop to an iPad stalled after
     * 2.6 and 3.2 MB at 0.01-0.03 MB/s and failed with "No route to host", while an idle iPhone nearby kept writing its
     * sequence (149 149 149 0 0 0 0 0 6 149 149 0 ...) over the iPad's. Every run that worked sent to that iPhone.
     */
    uint8_t dest[6], dest_seq[16], dest_seq_valid;
    uint64_t dest_host_us;
    uint32_t dest_updates;
    /*
     * 1.2.15: the peers data went to in the last IWX_AWDL_DPEER_TX_US, or whose own sequence is widened, each with its
     * sequence. 2026-11-14 08:55 (1.2.14): AirDrop to the iPad alone, yet the receiving device read as the iPhone in
     * every phase: background unicast to the iPhone (Continuity) took tx.last_dest, so the union followed the
     * iPhone's idle sequence and the iPad's transfer failed. The union takes every active peer's 149 slots instead.
     */
    struct iwx_awdl_dpeer {
        uint8_t mac[6], seq[16], seq_valid;
        uint64_t seq_us, tx_us;
    } dpeer[4];
    /* 1.2.16: when this Mac last meant to use AWDL: its family's sequence widened, or unicast data went out. */
    uint64_t intent_us;
};

/* An ADDBA request or DELBA heard from a peer, waiting for the task that may send commands. */
struct iwx_awdl_ba_req {
    uint8_t peer[6], dialog, tid, del;
    uint16_t param, timeout, ssn, win;
};

struct iwx_awdl_ba {
    uint8_t active, sta_id, tid, dialog;
    uint8_t peer[6];
};

enum iwx_awdl_tx_kind { IWX_AWDL_TX_NONE, IWX_AWDL_TX_PSF, IWX_AWDL_TX_MIF, IWX_AWDL_TX_UNICAST };

struct iwx_awdl_tx {
    /* Destination of the last unicast data frame, which the own queue follows. */
    uint8_t last_dest[6];
    uint8_t last_dest_valid;
    /* Unicast data bytes per peer station: the window being counted and the last whole one (1.1.77). */
    uint32_t dest_bytes[IWX_AWDL_PEER_STA_MAX], dest_bytes_last[IWX_AWDL_PEER_STA_MAX];
    uint64_t dest_window_us;
    uint64_t bulk_last_us;       /* Last tick with bulk data (1.1.80): the scan gate holds 10 s past it. */
    uint32_t mode, tripped, firmware_faults;
    /* Set when a firmware fault tripped AWDL: the firmware restart may re-arm it (1.1.73). */
    uint32_t fault_tripped, fault_rearms;
    /* What the ROC test and link 1 were doing at the last firmware fault (1.1.89): iwx_awdl_fault_roc, _phy2. */
    uint32_t fault_roc, fault_phy2, fault_link;
    uint8_t self[6], peer[6], peer_valid;
    uint16_t seq;
    uint64_t last_psf_us, last_mif_us, last_unicast_us;
    uint32_t mcast_sent, mcast_ok, mcast_fail;
    uint32_t unicast_sent, unicast_ack, unicast_noack, unicast_retries;
    uint32_t last_fail_status, busy, alloc_fail, queue_limited, stalls, csum_fixed, psf_sent;
    /* Unicast rate, offset from the starting step in iwx_awdl_data_rate. No TLC serves these peers. */
    int32_t rate_step;
    uint32_t rate_ok, rate_fail, rate_up_after, rate_ups, rate_downs;
    /* The system's queue waits while this is set; a completion or the AW timer wakes it. */
    uint8_t data_stalled;
    uint32_t data_stalls, data_kicks;
    /* Test: keep data while the peer's schedule has it elsewhere. Results by presence prove the schedule. */
    uint8_t hold, peer_away;
    uint32_t away_holds, ok_here, fail_here, ok_away, fail_away;
    /* Test: several packets to one peer in one MPDU, on the AP queue. */
    uint8_t amsdu;
    uint32_t amsdu_sent, amsdu_frames, amsdu_ok, amsdu_fail, amsdu_gave_up;
    uint8_t amsdu_buf[IWX_AWDL_AMSDU_MAX_BYTES];
    /* Send the system's own TLVs. Set under the work loop gate, like everything here. */
    uint8_t native;
    uint16_t native_psf_len, native_mif_len;
    uint32_t native_updates, native_rejected;
    uint8_t native_psf[IWX_AWDL_NATIVE_TLV_MAX], native_mif[IWX_AWDL_NATIVE_TLV_MAX];
    uint8_t frame[IWX_AWDL_NATIVE_FRAME_MAX];
};

/* Firmware objects of the AWDL context, in creation order. */
enum iwx_awdl_ctx_stage { IWX_AWDL_CTX_NONE, IWX_AWDL_CTX_MAC, IWX_AWDL_CTX_LINK, IWX_AWDL_CTX_ACTIVE,
                          IWX_AWDL_CTX_STA, IWX_AWDL_CTX_QUEUE, IWX_AWDL_CTX_ASSOC };

struct iwx_awdl_ctx {
    uint32_t mode, stage, last_err, failed_stage, adds, removes;
    int32_t qid;
    uint32_t te_requests, te_started, te_ended, te_failed;
    uint64_t last_te_us;
    /* Test: data to the first peer on that peer's own queue. Falls back to the AP queue if held. */
    int32_t own_qid;
    uint8_t own_want, own_active, own_sta, own_peer[6];
    uint32_t own_sent, own_ok, own_fail, own_err, own_held, own_seen_done, own_idle;
    /* Test: link 1 on its own PHY context, another channel than the AP's. 0 is the AP's. */
    uint32_t phy2_want, phy2_chan, phy2_err, phy2_switches, rx_phy2, rx_home;
    uint8_t te_want, link_no_phy;
    /* A move of link 1 between PHY contexts is queued or running: no ROC starts meanwhile (1.1.89). */
    uint8_t phy2_moving;
    /* 1.1.90: a firmware fault came during a move; the second channel stays off until the switch reads 0. */
    uint8_t phy2_fault_hold;
    uint32_t phy2_fault_holds;
    uint32_t te_removed, own_released;
    /* The own queue follows where data goes; with aggregation it is a TID 0 queue the firmware aggregates. */
    uint8_t own_tid, own_agg_want, own_agg;
    /* Fixes for the held own queue, by bit: 1 MAC 1 without power save, 2 link 1 QoS (EDCA, FIFOs) and beacon timing. */
    uint8_t own_fix_want, own_fix_done, own_redo;
    uint32_t own_fix_err;
    uint32_t own_retargets, own_agg_err, own_tlc_err, own_txen_err, own_agg_ok, own_agg_fail, own_ba_notifs;
    /* Default from 1.1.54: retarget only after the current peer went quiet; held queues rebuilt, a bounded number of times. */
    uint32_t own_sent_mark, own_recovers, own_recover_fails, own_recover_ok_mark, own_quiet_skips;
    uint64_t own_busy_us, own_held_us, own_try_us;
    int32_t own_target;          /* Peer index the next build must use: the bulk peer (1.1.77); -1 none. */
    uint32_t own_bulk_moves;
    uint32_t own_retries;
    uint32_t own_transient, own_transient_last; /* Busy command ring: retried, not latched (1.1.76). */
    /* This Mac's own schedule, from the AW timer: the slot starting now, how many slots of that channel follow, the
     * 5 GHz channel the sequence uses. Second channel automatic choice and mode 3 windows. */
    uint8_t slot_chan, slot_run, auto_cand;
    /* Mode 4: the 5 GHz channel of the next slot that has one, from this slot on (the link moves a slot ahead). */
    uint8_t slot_next5;
    uint32_t phy2_slot_moves;
    /* Mode 5: moves that kept the own queue (flushed only) instead of releasing it. */
    uint32_t own_kept_moves;
    /* Second channel windows: the session protection kind, latched only between windows; peer refreshes after moves. */
    uint8_t te_conf;
    uint32_t own_refreshes, own_refresh_err;
    /* Own queue completions while link 1 sits on the second channel, and the frames sent there. */
    uint32_t own_sent_phy2, own_done_phy2;
    /* On the second channel: failed TX responses, the last failure status, block ack notifications. */
    uint32_t own_fail_phy2, own_last_status_phy2, own_ba_phy2;
    /*
     * Mode 6: a queue on the AWDL station (link 1), so action, multicast and fallback unicast frames go where link 1
     * is. In context mode 6 they all used the AP station's queue, on the AP's channel only. 0 or less: none.
     */
    int32_t phy2_qid;
    uint32_t phy2_q_sent, phy2_q_done, phy2_q_fail, phy2_q_drop, phy2_q_err;
    /*
     * No infrastructure network (1.1.66): the context on its own, link 1 on the second PHY context at the AWDL
     * channel, all AWDL frames on the AWDL station's queue. Removed before any join; a failure stops it for the boot.
     */
    uint8_t solo, solo_failed;
    uint32_t solo_adds, solo_removes, solo_err, solo_err_stage;
    uint64_t solo_try_us;
    /* The sequence's first two different 5 GHz channels, low byte first. */
    uint16_t seq_chan5;
    uint64_t slot_us, auto_since_us, te_end_us;
    uint32_t te_own, phy2_auto_changes;
    /*
     * 1.1.94: the step of a move of link 1 that is running (iwx_awdl_move_step, 0 none), for the fault snapshot.
     * Peer TLC re-sent for a new width, and own queues released or flushed on the way onto the second channel.
     */
    uint8_t phy2_step;
    uint32_t phy2_tlc_refreshes, phy2_tlc_err, phy2_own_quiesces;
};

struct iwx_awdl_roc {
    uint32_t want, mode, activity;   /* want: from the switch each tick; mode/activity: latched at setup */
    int32_t qid;
    uint8_t sta_added, pending, active, chan, setup_failed;
    uint64_t sent_us, setup_us;
    uint32_t adds, add_err, started, ended, failed, stale, removes;
    uint32_t setups, setup_err, setup_stage, teardowns;
    uint32_t tx_sent, tx_ok, tx_fail, tx_drop, rx_during;
    uint32_t blocked, blocked_pub;   /* Readiness bits missing while wanted (1.1.82); published on change. */
    /* 1.1.85: last AWDL frame heard on any channel, discovery ROCs, and every frame received while an ROC runs. */
    uint64_t heard_us, disc_us;
    uint32_t disc, rx_any, rx_any_chan, rx_awdl_any;
    uint8_t disc_pending;
    /* 1.1.89: ticks an ROC waited for a move of link 1, and ROCs the move removed first. */
    uint32_t phy_holds, phy_cancels;
    /*
     * 1.1.91, why AUX frames fail. 2026-11-12 08:48, mode 4 with the link on 149: 634 sent, 311 ok, 321 failed, all
     * multicast fine, unicast without ACK (last status 0x83), 144 retries over 427 boot-wide failures; AirDrop failed.
     * See iwx_awdl_roc_note_tx and the start/end timing in the ROC notification.
     */
    struct iwx_awdl_roc_tx_stats {
        uint32_t status[8];                 /* failures by iwx_awdl_roc_status_bucket */
        uint32_t ok_ucast, fail_ucast, ok_mcast, fail_mcast;
        /* 1.1.95: unicast data among them (the rest is management, mostly AWDL action frames). */
        uint32_t ok_ucast_data, fail_ucast_data;
        uint32_t fail_in, fail_out;         /* the ROC still running at completion, or not */
        uint32_t ok_here, ok_away, fail_here, fail_away, fail_unknown; /* phone's schedule: the ROC's channel, another, unknown */
        uint32_t fail_tries, ok_tries;      /* failure_frame summed */
    } txs;
    uint64_t started_us;
    uint32_t late_n, late_sum_ms, late_max_us; /* ADD sent to started */
    uint32_t on_n, on_sum_ms;                  /* started to ended */
    /*
     * 1.1.92, mode 4: unicast AWDL frames wait here, in the host, until an ROC runs with time left. 2026-11-12 09:02:
     * 24 unicast AUX frames failed, 23 of them completing after their ROC, 3 retries in all (0x83), none acknowledged;
     * frames queued to the firmware between ROCs were never really sent. mbufs and node references, oldest first.
     */
    uint32_t dur_tu;                       /* the running ROC's requested duration */
    /*
     * 1.1.96: the family's 16-slot sequence and the slot running now (setAwdlSequence), the slots ROCs cover
     * (iwx_awdl_roc_cover), covered slots left from this one and when they end, and what was announced on the air.
     */
    uint8_t fam[16], cover[16], fam_valid, slot_idx, cov_left, announce_on;
    uint64_t cov_end_us, last_end_us;
    uint32_t cap_tu, cov_sum_ms, req_sum_ms, chain_adds, chain_skips, chain_gap_n, chain_gap_sum_ms, wide_adds;
    uint32_t dwell_hist[4];                /* dwell against request: under 25 %, 50 %, 75 %, and more */
    /* 1.1.97: ADDs held back by IWX_AWDL_ROC_READD_US, the shortest end-to-ADD time seen, and the last ADD's. */
    uint32_t readd_waits, readd_min_us, last_add_after_us;
    uint8_t last_add_src;                  /* 1 slot tick, 2 chain, 3 discovery */
    void *hold_m[IWX_AWDL_ROC_HOLD_MAX], *hold_ni[IWX_AWDL_ROC_HOLD_MAX];
    uint8_t hold_rq[IWX_AWDL_ROC_HOLD_MAX]; /* 1.1.98: times each held frame came back from an ROC's end */
    uint8_t flush_rq;                       /* the count for the frame the flush is sending */
    uint32_t requeued, requeue_drop;
    uint32_t requeued_in;                   /* 1.2.17: of those, frames the peer missed while the ROC ran */
    /* 1.1.99: requeues since the last ROC start (they go in front, in order), why frames waited, the family's waits. */
    uint32_t rq_batch, hold_order, hold_ring, hold_stalls, hold_kicks, hold_peak;
    uint8_t hold_stall_wait;
    /*
     * 1.2.1: the window follows the phone's own sequence and AW timing (iwx_awdl_peer_run): whether it does this slot,
     * when the phone's run starts, ticks timed so, ticks with no phone run, the phone's slot index less ours, how far
     * its boundary was from our tick (signed, last, and summed as absolute ms), and releases waiting for its start.
     */
    uint8_t peer_timed, peer_k;
    uint64_t peer_start_us;
    uint32_t peer_ticks, peer_idle_ticks, peer_lag_n, peer_lag_abs_ms, peer_waits;
    int32_t peer_lag_us;
    /* 1.2.2: why a flush stopped with frames still held: the ring cap, the ROC rule (no ROC, end near, phone not yet). */
    uint32_t flush_stop_ring, flush_stop_rule;
    /* 1.2.3: the ROC timer: armed, the ring tail it saw, kicks, the delayed release time, missed-beacon pauses. */
    uint8_t kick_armed;
    uint32_t kick_tail, kicks, kick_ticks, kick_releases, bmiss_pauses, bmiss_skips, bmiss_last;
    uint64_t release_at_us, bmiss_until_us;
    /* 1.2.4: the early ROC for the next slot: armed, the boundary, the run, and how it went. */
    uint8_t pre_armed, pre_chan, pre_slots;
    uint64_t pre_boundary_us, aw_start_us;
    uint32_t pre_arms, pre_adds, pre_skips, pre_on_time, pre_late;
    /* 1.2.5: AUX frames that still left on another queue (should stay 0), and pauses after a failed ROC. */
    uint32_t off_aux, fail_pauses;
    /* 1.2.11: the AUX queue's TID, and the A-MSDU counts at the last ROC end (iwx_awdl_amsdu_stuck). */
    uint8_t tid;
    uint32_t amsdu_sent_mark, amsdu_done_mark, amsdu_stuck;
    /* 1.2.13: ticks where the union followed the data peer's own sequence. */
    uint32_t dest_ticks;
    /* 1.2.9: ticks where the slot now is covered only because the phone's sequence has it, and slots added so. */
    uint32_t union_ticks, union_slots;
    /* 1.2.19: the sparse-peer gate: the peers' slot offset and this Mac's slot when set, frames held, flush stops. */
    uint8_t gate_k, gate_chan;
    uint64_t gate_us;
    uint32_t gate_ticks, gate_waits;
    /* 1.2.8: the AUX path's own rate step (iwx_awdl_roc_rate_note), apart from the link-wide one. */
    int32_t rate_step;
    uint32_t rate_ok, rate_fail, rate_ups, rate_downs;
    /* 1.2.0: refills from a completion or an ROC start in the gate; air time and the last rate of AUX unicast data. */
    uint32_t flush_direct, air_n, air_us_hi, air_us_lo, last_rate, sent_per_roc_max, sent_this_roc;
    uint64_t hold_us[IWX_AWDL_ROC_HOLD_MAX];
    uint32_t hold_head, hold_n;
    uint8_t flushing;                      /* the flush task is sending: no new hold */
    uint32_t held, released, hold_full, hold_expired, hold_freed;
};

/*
 * 1.1.96: the slots ROCs cover. A slot of the ROC channel counts while it is within the first run_max slots of its
 * run; a sequence that is that channel in every slot counts from slot 0. Everything else is 0.
 */
/*
 * 1.2.10: a long run is covered in pieces of run_max slots with IWX_AWDL_ROC_AP_GAP_SLOTS left to the AP between them.
 * 2026-11-13 22:38 (1.2.9, router on 36): the phone's sequence was one run of 15 slots on 149, the union took it, and
 * covering only the first run_max slots of a run left this Mac on 149 30 % of the time (5 of 16 slots), against
 * 48-56 % at 21:39 when the family's two runs of 6 gave 10 of 16. Runs up to run_max are covered as before.
 */
#define IWX_AWDL_ROC_AP_GAP_SLOTS 2u
static inline uint32_t iwx_awdl_roc_gap(uint32_t want)
{
    return (want & IWX_AWDL_ROC_F_GAP1) ? 1u : IWX_AWDL_ROC_AP_GAP_SLOTS;
}
static inline void iwx_awdl_roc_cover(const uint8_t fam[16], uint8_t chan, uint32_t run_max, uint8_t out[16],
                                      uint32_t gap = IWX_AWDL_ROC_AP_GAP_SLOTS)
{
    bool all = chan != 0;
    for (unsigned i = 0; i < 16; ++i)
        all = all && fam[i] == chan;
    for (unsigned i = 0; i < 16; ++i) {
        out[i] = 0;
        if (!chan || fam[i] != chan)
            continue;
        unsigned pos = 0;
        if (all)
            pos = i;
        else
            while (pos < 16 && fam[(i + 16 - pos - 1) % 16] == chan)
                ++pos;
        if (run_max && pos % (run_max + gap) < run_max)
            out[i] = chan;
    }
}
/* Whether any slot is covered. */
static inline bool iwx_awdl_roc_covers(const uint8_t cover[16])
{
    for (unsigned i = 0; i < 16; ++i)
        if (cover[i])
            return true;
    return false;
}
/* Covered slots from this one on, this one included. */
static inline uint32_t iwx_awdl_roc_cover_left(const uint8_t cover[16], uint32_t slot)
{
    uint32_t n = 0;
    while (n < 16 && cover[(slot + n) % 16])
        ++n;
    return n;
}
/* The longest ROC beside the AP: IWX_AWDL_ROC_MAX_TU, under the DTIM interval less the guard unless switched off. */
static inline uint32_t iwx_awdl_roc_cap(uint32_t beacon_tu, uint32_t dtim, bool no_clamp)
{
    uint32_t cap = IWX_AWDL_ROC_MAX_TU;
    const uint32_t d = beacon_tu * (dtim ? dtim : 1);
    if (!no_clamp && beacon_tu && d > IWX_AWDL_ROC_DTIM_GUARD_TU + IWX_AWDL_ROC_SLOT_TU / 4 && d - IWX_AWDL_ROC_DTIM_GUARD_TU < cap)
        cap = d - IWX_AWDL_ROC_DTIM_GUARD_TU;
    return cap;
}
/* Another ROC is worth chaining while more than min_us of covered time is left. */
static inline bool iwx_awdl_roc_chain_due(uint64_t now_us, uint64_t cov_end_us, uint32_t min_us)
{
    return cov_end_us > now_us && cov_end_us - now_us > min_us;
}
/* How much of the requested time an ROC really ran. */
static inline void iwx_awdl_roc_note_dwell(struct iwx_awdl_roc *r, uint64_t on_us, uint32_t req_tu)
{
    const uint64_t req = uint64_t(req_tu) * IWX_AWDL_TU_US;
    const uint32_t b = !req ? 3u : on_us * 4 < req ? 0u : on_us * 2 < req ? 1u : on_us * 4 < req * 3 ? 2u : 3u;
    ++r->dwell_hist[b];
}
/*
 * The control position of a 20 MHz primary inside its 80 MHz block (36-48, 52-64, 100-112, 116-128, 132-144,
 * 149-161, 165-177), as Linux iwl_mvm_get_ctrl_pos: 0x1 2 below, 0x0 1 below, 0x4 1 above, 0x5 2 above the centre.
 */
static inline uint8_t iwx_awdl_ctrl_pos80(uint32_t chan)
{
    static const uint8_t pos[4] = {0x1, 0x0, 0x4, 0x5};
    const uint32_t start = chan >= 149 ? 149 + (chan - 149) / 16 * 16 : chan >= 100 ? 100 + (chan - 100) / 16 * 16 :
        36 + (chan - 36) / 16 * 16;
    return pos[((chan - start) / 4) & 3];
}

/* AUX ring room: IWX_AWDL_ROC_TX_MAX_QUEUED while an ROC runs (1.1.96), IWX_AWDL_TX_MAX_QUEUED otherwise. */
static inline uint32_t iwx_awdl_roc_ring_cap(bool active)
{
    return active ? IWX_AWDL_ROC_TX_MAX_QUEUED : IWX_AWDL_TX_MAX_QUEUED;
}

/* Whether a unicast AWDL frame for the AUX queue waits in the host (1.1.92): mode 4, no ROC with margin left. */
static inline bool iwx_awdl_roc_hold(uint32_t mode, bool active, uint64_t started_us, uint32_t dur_tu, uint64_t now_us)
{
    if (mode < 4)
        return false;
    if (!active || !started_us)
        return true;
    const uint64_t end = started_us + uint64_t(dur_tu) * IWX_AWDL_TU_US;
    return now_us + IWX_AWDL_ROC_TX_MARGIN_US >= end;
}
/* Ring positions for the hold queue: the slot a new frame takes, and whether the oldest has waited too long. */
static inline uint32_t iwx_awdl_roc_hold_tail(const struct iwx_awdl_roc *r)
{
    return (r->hold_head + r->hold_n) % IWX_AWDL_ROC_HOLD_MAX;
}
/*
 * 1.1.99: in mode 4 a unicast frame also waits when frames are already held (order) or the AUX ring is full (no
 * drop). 0 send now, 1 the ROC rule, 2 behind held frames, 3 ring full.
 */
static inline uint32_t iwx_awdl_roc_hold_why(bool rule, uint32_t mode, uint32_t hold_n, bool ring_full)
{
    if (rule)
        return 1;
    if (mode < 4)
        return 0;
    return hold_n ? 2 : ring_full ? 3 : 0;
}
/* 1.1.99: the family waits while the hold is high, and is woken when it is low again. */
static inline bool iwx_awdl_roc_hold_busy(uint32_t mode, bool up, uint32_t hold_n)
{
    return up && mode >= 4 && hold_n >= IWX_AWDL_ROC_HOLD_HIGH;
}
/* 1.1.99: insert at position pos from the oldest (0 = next out), moving the later ones back by one. */
static inline void iwx_awdl_roc_hold_insert(struct iwx_awdl_roc *r, uint32_t pos, void *m, void *ni, uint64_t us,
                                            uint8_t rq)
{
    if (pos > r->hold_n)
        pos = r->hold_n;
    for (uint32_t k = r->hold_n; k > pos; --k) {
        const uint32_t d = (r->hold_head + k) % IWX_AWDL_ROC_HOLD_MAX, s = (r->hold_head + k - 1) % IWX_AWDL_ROC_HOLD_MAX;
        r->hold_m[d] = r->hold_m[s];
        r->hold_ni[d] = r->hold_ni[s];
        r->hold_us[d] = r->hold_us[s];
        r->hold_rq[d] = r->hold_rq[s];
    }
    const uint32_t i = (r->hold_head + pos) % IWX_AWDL_ROC_HOLD_MAX;
    r->hold_m[i] = m;
    r->hold_ni[i] = ni;
    r->hold_us[i] = us;
    r->hold_rq[i] = rq;
    ++r->hold_n;
}
static inline bool iwx_awdl_roc_hold_stale(const struct iwx_awdl_roc *r, uint64_t now_us)
{
    return r->hold_n && now_us - r->hold_us[r->hold_head] >= IWX_AWDL_ROC_HOLD_US;
}

/* Failure status buckets: 0 short limit, 1 long limit, 2 drain, 3 lifetime, 4 dest PS, 5 FIFO flushed, 6 aborted, 7 other. */
static inline uint32_t iwx_awdl_roc_status_bucket(uint32_t s)
{
    switch (s) {
    case 0x82: return 0;
    case 0x83: return 1;
    case 0x85: return 2;
    case 0x87: return 3;
    case 0x88: return 4;
    case 0x8e: return 5;
    case 0x89: case 0x92: return 6;
    default: return 7;
    }
}

/* One AUX frame's result. peer_chan: the reference peer's slot channel then (0 unknown); chan: the ROC's. */
static inline void iwx_awdl_roc_note_tx(struct iwx_awdl_roc *r, bool unicast, bool ok, uint32_t status, uint32_t tries,
                                        bool active, uint8_t peer_chan)
{
    auto t = &r->txs;
    if (!unicast) {
        ++*(ok ? &t->ok_mcast : &t->fail_mcast);
        if (!ok)
            ++t->status[iwx_awdl_roc_status_bucket(status)];
        return;
    }
    const bool here = peer_chan && peer_chan == r->chan;
    if (ok) {
        ++t->ok_ucast;
        t->ok_tries += tries;
        if (peer_chan)
            ++*(here ? &t->ok_here : &t->ok_away);
        return;
    }
    ++t->fail_ucast;
    t->fail_tries += tries;
    ++t->status[iwx_awdl_roc_status_bucket(status)];
    ++*(active ? &t->fail_in : &t->fail_out);
    ++*(!peer_chan ? &t->fail_unknown : here ? &t->fail_here : &t->fail_away);
}

/* ROC timing from its notifications (1.1.91): how late after the ADD it started, and how long it ran. */
static inline void iwx_awdl_roc_note_start(struct iwx_awdl_roc *r, uint64_t now_us)
{
    r->started_us = now_us;
    const uint64_t late = now_us > r->sent_us ? now_us - r->sent_us : 0;
    ++r->late_n;
    r->late_sum_ms += uint32_t(late / 1000);
    if (late > r->late_max_us)
        r->late_max_us = late > 0xffffffffull ? 0xffffffffu : uint32_t(late);
}
static inline void iwx_awdl_roc_note_end(struct iwx_awdl_roc *r, uint64_t now_us)
{
    if (r->started_us && now_us > r->started_us) {
        ++r->on_n;
        r->on_sum_ms += uint32_t((now_us - r->started_us) / 1000);
    }
    r->started_us = 0;
}

/*
 * Snapshots for a firmware fault (1.1.89). 2026-11-12 07:47, mode 4 with P2P_TXRX and phy2 1: three asserts, all
 * 0x200008FE with data 145 and last host command PHY_CONTEXT_CMD (0x08), while 1.1.86 moved the same link beside
 * HOTSPOT ROCs without one. Whether an ROC was running at the move is what these record.
 * ROC: bit 0 pending, 1 active, 2 station added, bits 4-7 activity, 8-11 mode, 16-23 channel.
 */
static inline uint32_t iwx_awdl_fault_roc(const struct iwx_awdl_roc *r)
{
    return (r->pending ? 1u : 0u) | (r->active ? 2u : 0u) | (r->sta_added ? 4u : 0u) |
           (r->activity & 15u) << 4 | (r->mode & 15u) << 8 | uint32_t(r->chan) << 16;
}
/* 1.1.90: the switch as the tick uses it. A hold set by a fault during a move gives 0 until the switch reads 0. */
static inline uint32_t iwx_awdl_phy2_after_fault(uint8_t *hold, uint32_t phy2)
{
    if (!phy2)
        *hold = 0;
    return *hold ? 0u : phy2;
}
/* Link 1: bit 0 a move queued or running, bits 8-15 the wanted channel, 16-23 the channel it is on (0 the AP's). */
static inline uint32_t iwx_awdl_fault_phy2(uint8_t moving, uint32_t want, uint32_t chan)
{
    return (moving ? 1u : 0u) | (want & 0xffu) << 8 | (chan & 0xffu) << 16;
}

/*
 * 1.1.94. 2026-11-12 12:20 (1.1.93, router 153/80 MHz): link 1 moved to 149 with ROC off and the firmware asserted,
 * 0x20101A28 data 0x20004 at LINK_CONFIG, after the PHY context had reached 149 (FaultPhy2 0x959501). That boot had
 * carried an AirDrop: an aggregated own queue, and its peer's TLC built for 80 MHz, on a link now on a 20 MHz context.
 * The 09:01 move that worked had almost no own queue traffic. Linux updates TLC for a link's stations when the link
 * gets a channel context, before activating it. Here the config stays valid at every step: narrowed to 20 MHz before
 * the link leaves the AP's PHY (20 MHz is valid there too), widened only after it is back on it.
 */
enum iwx_awdl_move_step { IWX_AWDL_MOVE_NONE, IWX_AWDL_MOVE_TE, IWX_AWDL_MOVE_OWN, IWX_AWDL_MOVE_ROC, IWX_AWDL_MOVE_TLC_NARROW,
                          IWX_AWDL_MOVE_INACTIVE, IWX_AWDL_MOVE_NO_PHY, IWX_AWDL_MOVE_PHY, IWX_AWDL_MOVE_WITH_PHY,
                          IWX_AWDL_MOVE_TLC_WIDEN, IWX_AWDL_MOVE_ACTIVE };
/* TLC goes to 20 MHz before a move onto the second channel, back to the AP's width after a move home. */
static inline bool iwx_awdl_move_tlc_narrow(uint32_t want, uint32_t chan)
{
    return want && !chan;
}
static inline bool iwx_awdl_move_tlc_widen(uint32_t want, uint32_t chan)
{
    return !want && !chan;
}
/* Link 1 at a fault: bits 0-3 the move step, 4 own queue, 5 own queue aggregated, 8-15 peer stations, 16-23 peer TLC. */
static inline uint32_t iwx_awdl_fault_link(uint8_t step, bool own_q, bool own_agg, uint32_t peers, uint8_t tlc)
{
    return (step & 15u) | (own_q ? 0x10u : 0u) | (own_agg ? 0x20u : 0u) | (peers & 0xffu) << 8 | uint32_t(tlc) << 16;
}

/* A discovery ROC is due: nothing AWDL heard lately and the last one long enough ago (1.1.85). */
static inline bool iwx_awdl_roc_disc_due(const struct iwx_awdl_roc *r, uint64_t now_us)
{
    const bool heard = r->heard_us && now_us - r->heard_us < IWX_AWDL_ROC_HEARD_US;
    return !heard && (!r->disc_us || now_us - r->disc_us >= IWX_AWDL_ROC_DISC_GAP_US);
}

/* The sequence's 5 GHz channel that is not the AP's: seq5 holds two channels, low byte first (0 when none). */
static inline uint32_t iwx_awdl_roc_other5(uint32_t seq5, uint32_t ap)
{
    const uint32_t a = seq5 & 0xff, b = (seq5 >> 8) & 0xff;
    if (a >= 36 && a != ap)
        return a;
    if (b >= 36 && b != ap)
        return b;
    return 0;
}

/*
 * Pause mode (1.2.24, docs/wifi/BE201-AWDL-PAUSE-DESIGN.md). Discovery and the ask stay on ROC, with the router; once
 * file data flows, the router's PHY context moves to the AWDL channel and link 1 joins it there, the layout that did
 * 13-16 MB/s when the router itself was on 149, while frames for the router wait (dropped, internet paused).
 */
#define IWX_AWDL_PAUSE_START_PKTS 32u     /* unicast packets, both ways, in one window: data is flowing */
#define IWX_AWDL_PAUSE_KEEP_PKTS 8u       /* in a window, still flowing */
#define IWX_AWDL_PAUSE_WIN_US 1000000u
#define IWX_AWDL_PAUSE_IDLE_US 4000000u   /* this long below KEEP: back to the router */
#define IWX_AWDL_PAUSE_MAX_US 120000000u  /* at most this long at a time, so the router never times this Mac out */
#define IWX_AWDL_PAUSE_COOL_US 2000000u   /* after a return, no new pause for this long */
#define IWX_AWDL_PAUSE_STEP_US 3000000u   /* a move that does not finish in this long is given up */
struct iwx_awdl_pause_trig {
    uint64_t win_us, since_us, last_us, cool_until_us;
    uint32_t win_n, starts, max_cuts;
    uint8_t want;
};
/* Unicast packets since the last call; whether the transfer wants the pause now. */
static inline bool iwx_awdl_pause_trig_step(struct iwx_awdl_pause_trig *t, uint64_t now_us, uint32_t pkts)
{
    if (!t->win_us || now_us - t->win_us >= IWX_AWDL_PAUSE_WIN_US) {
        t->win_us = now_us ? now_us : 1;
        t->win_n = 0;
    }
    t->win_n += pkts;
    if (!t->want) {
        if (t->win_n >= IWX_AWDL_PAUSE_START_PKTS && now_us >= t->cool_until_us) {
            t->want = 1;
            t->since_us = t->last_us = now_us;
            ++t->starts;
        }
        return t->want;
    }
    if (pkts && t->win_n >= IWX_AWDL_PAUSE_KEEP_PKTS)
        t->last_us = now_us;
    const bool maxed = now_us - t->since_us >= IWX_AWDL_PAUSE_MAX_US;
    if (maxed || now_us - t->last_us >= IWX_AWDL_PAUSE_IDLE_US) {
        if (maxed)
            ++t->max_cuts;
        t->want = 0;
        t->cool_until_us = now_us + IWX_AWDL_PAUSE_COOL_US;
        t->win_n = 0;
    }
    return t->want;
}
enum {
    IWX_AWDL_PAUSE_OFF = 0,
    IWX_AWDL_PAUSE_MOVING,    /* link 1 going back to the router's PHY, ROC coming down */
    IWX_AWDL_PAUSE_TUNING,    /* the task moves the router's PHY to the AWDL channel */
    IWX_AWDL_PAUSE_ON,
    IWX_AWDL_PAUSE_LEAVING,   /* the task moves it back */
    IWX_AWDL_PAUSE_RETURNING, /* link 1 going back to its second PHY */
};
struct iwx_awdl_pause {
    uint8_t want, state, phy2_hold, tuned, chan;
    uint64_t state_us, on_us;
    uint32_t enters, exits, aborts, drops, nulls, null_err, err, last_ms, max_ms, ignored_bmiss;
    uint32_t skips; /* 1.2.25: router wider than 80 MHz, no pause */
};
/*
 * 1.2.25: during a pause the router's PHY context takes the router's own width on the AWDL channel, so neither the
 * router's nor the peers' rate control changes. 15:3x (1.2.24): narrowing the router station's rate control to
 * 20 MHz while associated (TLC_MNG_CONFIG) asserted the firmware (0x20101A27, last command 0x50F) on both pauses.
 * Widths the AWDL channel can take for a router of width w (net80211 widths): up to 80 MHz.
 */
static inline bool iwx_awdl_pause_width_ok(uint8_t chw)
{
    return chw <= 3; /* IEEE80211_CHAN_WIDTH_20_NOHT 0, _20 1, _40 2, _80 3 */
}
/* The 40 MHz pair: whether chan is the lower channel (control 1 below the centre). */
static inline bool iwx_awdl_lower40(uint32_t chan)
{
    const uint32_t start = chan >= 149 ? 149 : chan >= 100 ? 100 : 36;
    return ((chan - start) / 4) % 2 == 0;
}
/* Whether a router-bound frame is dropped: data while the router's PHY is on the AWDL channel. */
static inline bool iwx_awdl_pause_drops(const struct iwx_awdl_pause *s, bool awdl, bool data)
{
    return s->tuned && !awdl && data;
}

struct iwx_awdl_probe {
    uint32_t mode;            /* 0 off, 1 mgmt filter, 2 mgmt filter + promiscuous, 3 own context */
    uint32_t assoc_rx;        /* Mode 6 also holds a station and association, for data receive. */
    /* Nearby AWDL senders that get a firmware station. Staged here, sent by the peer task. */
    uint8_t peer_addr[IWX_AWDL_PEER_STA_MAX][6];
    uint32_t peer_count, peer_added, peer_failed, peer_errors;
    /* 1.1.94: peer stations, by index bit, that have a firmware rate control (TLC) config: a move re-sends it. */
    uint8_t peer_tlc;
    /*
     * Replacing stations (1.1.77): when last heard, and an address staged to take an index's place. The table has 4
     * places and nothing ever left it: with 8 devices around, the AirDrop target often had no station (no own queue,
     * about 4 MB/s), and after Wi-Fi and Bluetooth were turned off and on the peers' new addresses never got one.
     */
    uint64_t peer_seen_us[IWX_AWDL_PEER_STA_MAX];
    uint8_t peer_new[IWX_AWDL_PEER_STA_MAX][6];
    uint8_t peer_replace;
    uint32_t peer_replaced, peer_replace_err;
    uint32_t foreign_data;    /* Data in another BSS: the filter is wider than this address. */
    uint32_t awdl_data_self;  /* AWDL data sent to this interface's address. */
    uint32_t rx_data_rate, rx_data_rate_peak, rx_data_ampdu; /* Of those: what the peer really sends. */
    /* Peers the family asked to cache, by slot of peer_addr, until the task answers. */
    uint8_t cache_add_wait, cache_del_wait;
    uint32_t cache_adds, cache_dels, cache_full;
    /* Unicast master indications the family asked for, and the ACK results it waits for. */
    uint32_t umi_sent, umi_ok, umi_fail, umi_rejected, umi_dropped;
    uint16_t umi_seq;
    uint8_t umi_seq_valid;
    uint8_t umi_seq_peer[6];
    uint8_t umi_done_count;
    struct { uint8_t mac[6]; uint8_t status; } umi_done[IWX_AWDL_UMI_DONE_MAX];
    struct iwx_awdl_ba_req ba_pending;
    uint8_t ba_pending_valid, ba_sample[9];
    struct iwx_awdl_ba ba[IWX_AWDL_BA_MAX];
    uint32_t ba_heard, ba_started, ba_repeated, ba_refused, ba_no_peer, ba_removed, ba_errors, ba_last_err;
    uint32_t rx_old_sn;
    uint32_t foreign_mgmt;    /* Proves the wider filter admits other BSS frames. */
    uint32_t foreign_action;
    uint32_t apple_action;    /* Category 127, OUI 00:17:f2, any type. */
    uint32_t awdl_action;     /* Type 8. */
    uint32_t awdl_psf;        /* Subtype 0. */
    uint32_t awdl_mif;        /* Subtype 3. */
    uint32_t awdl_bssid;      /* Any frame in the fixed AWDL BSSID. */
    uint32_t awdl_data;
    uint32_t dropped;
    uint32_t sender_count;
    uint16_t senders[IWX_AWDL_PROBE_MAX_SENDERS];
    uint64_t published_ns;
    /* Set by the driver for the frame being handed to iwx_awdl_probe_rx. */
    uint32_t rx_gp2;
    uint64_t rx_host_us;
    uint8_t rx_chan;
    /* Timing: can the host follow the windows of the peers it hears? */
    uint32_t parse_bad, sync_frames, sync_updates;
    uint32_t jitter[4];       /* <=256us, <=1 TU, <=3 TU (OWL's limit), more */
    uint32_t host_jitter[5];  /* Host latency above the 10 s minimum: <=256us, 1, 4, 16 TU, more */
    uint32_t slots_6, slots_44, slots_149, slots_other, slots_idle, slots_current;
    uint32_t next_peer;
    uint32_t host_min;
    uint64_t host_window_us;
    struct iwx_awdl_timing_peer peers[IWX_AWDL_TIMING_PEERS];
    struct iwx_awdl_sync sync;
    struct iwx_awdl_tx tx;
    struct iwx_awdl_ctx ctx;
    struct iwx_awdl_roc roc;
    struct iwx_awdl_pause pause; /* 1.2.24 */
    struct iwx_awdl_hist hist[IWX_AWDL_HIST_LEN];
    uint32_t hist_next;
    uint64_t hist_us;
};

struct iwx_awdl_tlvs {
    const uint8_t *sync, *election, *election2, *chanseq, *version;
    uint16_t sync_len, election_len, election2_len, chanseq_len, version_len;
};

enum iwx_awdl_probe_action { IWX_AWDL_PROBE_KEEP, IWX_AWDL_PROBE_DROP };

static inline uint16_t iwx_awdl_le16(const uint8_t *p) { return uint16_t(p[0] | (p[1] << 8)); }
static inline uint32_t iwx_awdl_le32(const uint8_t *p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
static inline uint8_t *iwx_awdl_put16(uint8_t *w, uint16_t v) { w[0] = uint8_t(v); w[1] = uint8_t(v >> 8); return w + 2; }
static inline uint8_t *iwx_awdl_put32(uint8_t *w, uint32_t v) {
    w = iwx_awdl_put16(w, uint16_t(v));
    return iwx_awdl_put16(w, uint16_t(v >> 16));
}
static inline uint8_t *iwx_awdl_putmem(uint8_t *w, const uint8_t *v, size_t n) { memcpy(w, v, n); return w + n; }

static inline uint16_t iwx_awdl_sender_hash(const uint8_t *sender) {
    uint16_t hash = 0x811c;
    for (unsigned i = 0; i < 6; ++i)
        hash = uint16_t((hash ^ sender[i]) * 0x0193);
    return hash;
}

/* body starts at the action category. Fields found before a bad TLV stay usable. */
static inline bool iwx_awdl_parse(const uint8_t *body, size_t n, struct iwx_awdl_tlvs *t) {
    memset(t, 0, sizeof(*t));
    if (n < IWX_AWDL_ACTION_LEN) return false;
    for (size_t off = IWX_AWDL_ACTION_LEN; off < n;) {
        if (n - off < 3) return false;
        const uint16_t l = iwx_awdl_le16(body + off + 1);
        if (l > n - off - 3) return false;
        const uint8_t *v = body + off + 3;
        switch (body[off]) {
            case 4: t->sync = v; t->sync_len = l; break;
            case 5: t->election = v; t->election_len = l; break;
            case 18: t->chanseq = v; t->chanseq_len = l; break;
            case 21: t->version = v; t->version_len = l; break;
            case 24: t->election2 = v; t->election2_len = l; break;
            default: break;
        }
        off += 3 + size_t(l);
    }
    return true;
}

static inline size_t iwx_awdl_chan_entry_size(uint8_t encoding) {
    return encoding == 0 ? 1 : ((encoding == 1 || encoding == 3) ? 2 : 0);
}

/* Slots of a heard channel sequence, and the second byte our channel uses in it. */
static inline void iwx_awdl_note_chanseq(struct iwx_awdl_probe *p, const struct iwx_awdl_tlvs *t, uint8_t *aux, uint8_t *aux_found) {
    *aux_found = 0;
    if (!t->chanseq || t->chanseq_len < 6) return;
    const uint8_t *v = t->chanseq;
    const size_t size = iwx_awdl_chan_entry_size(v[1]), entries = size_t(v[0]) + 1;
    if (!size || entries > 64 || 6 + entries * size > t->chanseq_len) { ++p->parse_bad; return; }
    for (size_t i = 0; i < entries; ++i) {
        const uint8_t *e = v + 6 + i * size;
        const uint8_t chan = v[1] == 1 ? e[1] : e[0];
        if (chan == 6) ++p->slots_6;
        else if (chan == 44) ++p->slots_44;
        else if (chan == 149) ++p->slots_149;
        else if (chan == 0) ++p->slots_idle;
        else ++p->slots_other;
        if (chan && chan == p->rx_chan) {
            ++p->slots_current;
            if (size == 2 && !*aux_found) { *aux = v[1] == 1 ? e[0] : e[1]; *aux_found = 1; }
        }
    }
}

/* Per-sender stability of the announced window boundary, and host latency spread. */
static inline void iwx_awdl_note_timing(struct iwx_awdl_probe *p, const uint8_t *sender, uint16_t ttn, uint16_t aw_period) {
    const uint32_t gp2 = p->rx_gp2, boundary = gp2 + uint32_t(ttn) * IWX_AWDL_TU_US;
    const uint32_t period = uint32_t(aw_period) * IWX_AWDL_TU_US;
    const uint16_t hash = iwx_awdl_sender_hash(sender);
    struct iwx_awdl_timing_peer *slot = nullptr;
    for (unsigned i = 0; i < IWX_AWDL_TIMING_PEERS; ++i)
        if (p->peers[i].valid && p->peers[i].hash == hash) slot = &p->peers[i];
    if (slot && gp2 - slot->gp2 && gp2 - slot->gp2 <= IWX_AWDL_TIMING_MAX_GAP_US) {
        const int32_t delta = int32_t(boundary - slot->boundary);
        const uint32_t mag = delta < 0 ? uint32_t(0) - uint32_t(delta) : uint32_t(delta);
        const uint32_t rem = mag % period, err = rem < period - rem ? rem : period - rem;
        ++p->jitter[err <= 256 ? 0 : (err <= IWX_AWDL_TU_US ? 1 : (err <= 3 * IWX_AWDL_TU_US ? 2 : 3))];
    }
    if (!slot) {
        slot = &p->peers[p->next_peer];
        p->next_peer = (p->next_peer + 1) % IWX_AWDL_TIMING_PEERS;
        slot->valid = 1;
        slot->hash = hash;
    }
    slot->gp2 = gp2;
    slot->boundary = boundary;
    /* Modulo 2^32, so a GP2 wrap does not read as a latency spike. */
    const uint32_t offset = uint32_t(p->rx_host_us) - gp2;
    if (!p->host_window_us || p->rx_host_us - p->host_window_us >= IWX_AWDL_TIMING_MAX_GAP_US) {
        p->host_window_us = p->rx_host_us;
        p->host_min = offset;
    }
    if (int32_t(offset - p->host_min) < 0) p->host_min = offset;
    const uint32_t excess = offset - p->host_min;
    ++p->host_jitter[excess <= 256 ? 0 : (excess <= IWX_AWDL_TU_US ? 1 : (excess <= 4 * IWX_AWDL_TU_US ? 2 :
                     (excess <= 16 * IWX_AWDL_TU_US ? 3 : 4)))];
}

/* Only a full 16 slot sequence: a shorter one has no known mapping from the AW number. */
static inline bool iwx_awdl_seq16(const struct iwx_awdl_tlvs *t, uint8_t out[16]) {
    if (!t->chanseq || t->chanseq_len < 6) return false;
    const uint8_t *v = t->chanseq;
    const size_t size = iwx_awdl_chan_entry_size(v[1]);
    if (!size || v[0] != 15 || 6 + 16 * size > t->chanseq_len) return false;
    for (size_t i = 0; i < 16; ++i) {
        const uint8_t *e = v + 6 + i * size;
        out[i] = v[1] == 1 ? e[1] : e[0];
    }
    return true;
}
static inline void iwx_awdl_sync_note_seq(struct iwx_awdl_sync *s, const struct iwx_awdl_tlvs *t) {
    s->seq_valid = iwx_awdl_seq16(t, s->seq) ? 1 : 0;
}
/*
 * 1.2.13: how long the data peer's own sequence stands in for the reference's after its last frame. 1.2.21: 20 s, was
 * 2 s. A peer's sequence leaves the union once it ages out, so this Mac stops covering that peer's slots, hears
 * nothing more from it, and it ages out for good. 2026-11-14 13:54 (1.2.20), an idle iPhone sending to this Mac: the
 * phone went absent at 13:54:31 and came and went after, no on-demand _asquic answer was ever made, its ASK never
 * came, and the phone showed declined. Sending to the iPad, whose sequence updates less than once a second, one run
 * did 0.77 MB/s and the next 0.07 with a 1.1 s round trip. An idle sequence rarely changes; the last one is the best
 * guess for 20 s.
 */
#define IWX_AWDL_DEST_SEQ_US 20000000u
/* 1.2.15: a peer counts for the union this long after data last went to it, or while its sequence has this many slots. */
#define IWX_AWDL_DPEER_TX_US 5000000u
#define IWX_AWDL_DPEER_WIDE 8u
/*
 * 1.2.16: every fresh peer's slots count this long after an intent (iwx_awdl_sync::intent_us). 2026-11-14 09:13 (1.2.15,
 * first send after boot): sharingd's Bonjour resolution over awdl0 timed out after 30 s (NWError -65553, Refused):
 * the family was in Low Power (2 slots on 149), no data had gone out yet and the iPad never widens, so 1.2.15 covered
 * 2 slots only. 1.2.9-1.2.14 always took the reference's slots and resolved.
 */
#define IWX_AWDL_INTENT_US 60000000u
#define IWX_AWDL_FAM_WIDE 6u
/* 1.2.16 test flag: a peer data goes to counts in every slot (an iPad on an infra network on 149 is there anyway). */
#define IWX_AWDL_ROC_F_DPEER_ALL 0x20000u
/*
 * Sparse-peer gate (1.2.19). 2026-11-14 12:57 (1.2.17), the iPhone sending to this Mac, router on 60: the phone was
 * idle on 3 of 16 slots ([149 0 149 0 0 0 0 0 6 0 149 ...]) while this Mac covered its own 12 Data slots and the
 * phone's 3, and held frames left in any ROC. Most replies went out with the phone away: the TLS handshake of its
 * DISCOVER took 2.7 s and 3.2 s, the phone reset the first connection 4 s in, and its ASK never arrived. A unicast
 * frame to a peer on 149 for fewer than IWX_AWDL_DPEER_WIDE slots leaves the hold only in slots
 * where it is on 149 (iwx_awdl_gate_dest, in its numbering through the union's offset). A widened peer (a phone or
 * iPad receiving) never waits.
 * 1.2.22: off by default, 0x40000 turns it on. Peer absences (wifip2pd "Posted peer absence") went from 12 in 18 min on
 * 1.2.17 to 48, 57 and about 63 on 1.2.19-1.2.21, the phone and iPad came and went every few seconds, asks failed
 * ("Ask failed Code=6") and transfers sat in waiting, while receiving from the phone still did not move data.
 */
#define IWX_AWDL_ROC_F_GATE 0x40000u
/*
 * 1.2.23 A/B switches, each one putting back the 1.2.17 behaviour of one later change. Peer absences on the router's
 * channel 60 ran at 3.3 a minute on 1.2.22 (1.0 while the Mac sat on 149 with no ROC; 0.67 on 1.2.17), with the gate
 * already off. Which change does it is measured, not guessed: the presence check runs each set in turn.
 *   0x80000  peer sequences age out after 2 s in the union again (1.2.21 made it 20 s)
 *   0x100000 received awdl0 packets keep no arrival timestamp (1.2.18)
 *   0x200000 no flush at each slot start (1.2.19)
 */
#define IWX_AWDL_ROC_F_SEQ2S 0x80000u
#define IWX_AWDL_ROC_F_NO_STAMP 0x100000u
#define IWX_AWDL_ROC_F_NO_SLOT_FLUSH 0x200000u
#define IWX_AWDL_DEST_SEQ_OLD_US 2000000u
/* The gate state is set each slot; older than IWX_AWDL_ROC_GATE_STALE_US (two slots) it no longer holds frames. */
#define IWX_AWDL_ROC_GATE_STALE_US 128000u
static inline bool iwx_awdl_roc_gate_wait(bool enabled, bool dest_waits, bool unicast, uint64_t set_us, uint64_t now_us)
{
    return enabled && dest_waits && unicast && set_us && now_us >= set_us && now_us - set_us < IWX_AWDL_ROC_GATE_STALE_US;
}
static inline void iwx_awdl_note_dest_seq(struct iwx_awdl_probe *p, const uint8_t *sender, const struct iwx_awdl_tlvs *t);

/* Follow one cluster: the current reference, or another once it has gone quiet. */
static inline void iwx_awdl_note_frame(struct iwx_awdl_probe *p, const uint8_t *sender, const uint8_t *body, size_t n) {
    struct iwx_awdl_tlvs t;
    if (!iwx_awdl_parse(body, n, &t)) ++p->parse_bad;
    uint8_t aux = 0, aux_found = 0;
    iwx_awdl_note_chanseq(p, &t, &aux, &aux_found);
    iwx_awdl_note_dest_seq(p, sender, &t);
    if (!t.sync || t.sync_len < 31) return;
    const uint16_t aw_period = iwx_awdl_le16(t.sync + 5);
    if (!aw_period || aw_period > 1024) { ++p->parse_bad; return; }
    ++p->sync_frames;
    const uint16_t ttn = iwx_awdl_le16(t.sync + 1);
    iwx_awdl_note_timing(p, sender, ttn, aw_period);
    if (!t.election || t.election_len < 19) return;
    struct iwx_awdl_sync *s = &p->sync;
    const uint8_t *master = t.sync + 21;
    if (s->valid && memcmp(s->master, master, 6) && memcmp(s->reference, sender, 6) &&
        p->rx_host_us - s->host_us < IWX_AWDL_SLOW_INTERVAL_US)
        return;
    s->valid = 1;
    s->action_version = body[5];
    s->version = t.version && t.version_len >= 1 ? t.version[0] : 0x34;
    s->presence = t.sync[27] >= 1 && t.sync[27] <= 16 ? t.sync[27] : 4;
    s->master_channel = t.sync[3];
    s->height = t.election[3];
    s->encoding = t.chanseq && t.chanseq_len >= 6 && aux_found ? t.chanseq[1] : 3;
    s->chan_aux = aux_found ? aux : (p->rx_chan <= 14 ? 0x51 : 0x80);
    memcpy(s->reference, sender, 6);
    memcpy(s->master, master, 6);
    s->aw_period = aw_period;
    s->af_period = iwx_awdl_le16(t.sync + 7);
    s->ttn = ttn;
    s->aw_seq = iwx_awdl_le16(t.sync + 29);
    s->master_metric = iwx_awdl_le32(t.election + 11);
    s->master_counter = t.election2 && t.election2_len >= 16 ? iwx_awdl_le32(t.election2 + 12) : 0;
    iwx_awdl_sync_note_seq(s, &t);
    s->gp2 = p->rx_gp2;
    s->host_us = p->rx_host_us;
    ++p->sync_updates;
    memcpy(p->tx.peer, sender, 6);
    p->tx.peer_valid = 1;
}

/* One frame at most per heard frame. A multicast frame needs no ACK; a unicast one proves delivery. */
static inline enum iwx_awdl_tx_kind iwx_awdl_tx_decide(const struct iwx_awdl_probe *p, uint64_t host_us) {
    const struct iwx_awdl_tx *x = &p->tx;
    if (!x->mode || x->tripped || !p->sync.valid || host_us - p->sync.host_us > IWX_AWDL_TX_WINDOW_US)
        return IWX_AWDL_TX_NONE;
    if (x->native) {
        if (x->native_mif_len && host_us - x->last_mif_us >= IWX_AWDL_NATIVE_MIF_INTERVAL_US) return IWX_AWDL_TX_MIF;
        if (x->native_psf_len && host_us - x->last_psf_us >= IWX_AWDL_PSF_INTERVAL_US) return IWX_AWDL_TX_PSF;
        return IWX_AWDL_TX_NONE;
    }
    if (x->peer_valid && host_us - x->last_unicast_us >= IWX_AWDL_SLOW_INTERVAL_US) return IWX_AWDL_TX_UNICAST;
    if (host_us - x->last_mif_us >= IWX_AWDL_SLOW_INTERVAL_US) return IWX_AWDL_TX_MIF;
    if (host_us - x->last_psf_us >= IWX_AWDL_PSF_INTERVAL_US) return IWX_AWDL_TX_PSF;
    return IWX_AWDL_TX_NONE;
}

/* 1.1.96: seq, when given, is the channel of each slot (0 absent); otherwise every slot is chan. */
static inline uint8_t *iwx_awdl_put_chanseq16(uint8_t *w, const struct iwx_awdl_sync *s, uint8_t chan, const uint8_t *seq) {
    const size_t size = iwx_awdl_chan_entry_size(s->encoding);
    *w++ = 15;
    *w++ = s->encoding;
    *w++ = 0;
    *w++ = 3;
    w = iwx_awdl_put16(w, 0xffff);
    for (unsigned i = 0; i < 16; ++i) {
        const uint8_t c = seq ? seq[i] : chan;
        if (size == 1) { *w++ = c; continue; }
        *w++ = s->encoding == 1 ? (c ? s->chan_aux : 0) : c;
        *w++ = s->encoding == 1 ? c : (c ? s->chan_aux : 0);
    }
    return w;
}
static inline uint8_t *iwx_awdl_put_chanseq(uint8_t *w, const struct iwx_awdl_sync *s, uint8_t chan) {
    return iwx_awdl_put_chanseq16(w, s, chan, NULL);
}

static inline uint8_t *iwx_awdl_put_tl(uint8_t *w, uint8_t type, uint8_t **len) {
    *w = type;
    *len = w + 1;
    return w + 3;
}
static inline void iwx_awdl_end_tl(uint8_t *len, const uint8_t *w) {
    iwx_awdl_put16(len, uint16_t(w - (len + 2)));
}

/*
 * MAC and action headers, then the sync, election and channel TLVs. This node follows the
 * cluster it hears, on the channel it is on, and advertises a low metric so it never
 * becomes the master. The caller has zeroed out.
 */
static inline uint8_t *iwx_awdl_build_head(struct iwx_awdl_probe *p, const uint8_t *da, uint8_t subtype,
                                           uint64_t host_us, uint8_t *out) {
    const struct iwx_awdl_sync *s = &p->sync;
    const uint8_t chan = p->rx_chan;
    uint8_t *w = out, *len;
    *w++ = 0xd0;
    *w++ = 0;
    w = iwx_awdl_put16(w, 0);
    w = iwx_awdl_putmem(w, da, 6);
    w = iwx_awdl_putmem(w, p->tx.self, 6);
    w = iwx_awdl_putmem(w, iwx_awdl_bssid, 6);
    w = iwx_awdl_put16(w, uint16_t(p->tx.seq++ << 4));
    static const uint8_t action[5] = {127, 0x00, 0x17, 0xf2, 8};
    w = iwx_awdl_putmem(w, action, sizeof(action));
    *w++ = s->action_version;
    *w++ = subtype;
    *w++ = 0;
    w = iwx_awdl_put32(w, uint32_t(host_us));
    w = iwx_awdl_put32(w, uint32_t(host_us));

    const int32_t eaw = int32_t(s->presence) * s->aw_period;
    int32_t ttn = int32_t(s->ttn) - int32_t((host_us - s->host_us) / IWX_AWDL_TU_US);
    uint16_t seq = s->aw_seq;
    if (ttn <= 0) {
        const int32_t wraps = (-ttn) / eaw + 1;
        ttn += wraps * eaw;
        seq = uint16_t(seq + wraps * s->presence);
    }
    const int32_t remaining = int32_t(s->aw_period) - (eaw - ttn);
    w = iwx_awdl_put_tl(w, 4, &len);
    *w++ = chan;
    w = iwx_awdl_put16(w, uint16_t(ttn));
    *w++ = s->master_channel;
    *w++ = 0;
    w = iwx_awdl_put16(w, s->aw_period);
    w = iwx_awdl_put16(w, s->af_period ? s->af_period : 110);
    w = iwx_awdl_put16(w, 0x1800);
    w = iwx_awdl_put16(w, s->aw_period);
    w = iwx_awdl_put16(w, s->aw_period);
    w = iwx_awdl_put16(w, remaining > 0 ? uint16_t(remaining) : 0);
    for (unsigned i = 0; i < 4; ++i) *w++ = uint8_t(s->presence - 1);
    w = iwx_awdl_putmem(w, s->master, 6);
    *w++ = s->presence;
    *w++ = 0;
    w = iwx_awdl_put16(w, seq);
    w = iwx_awdl_put16(w, seq);
    /* 1.1.96, ROC mode 4: only the slots ROCs cover, so the phone sends when this Mac is really there. */
    const uint8_t *announced = p->roc.announce_on ? p->roc.cover : NULL;
    w = iwx_awdl_put_chanseq16(w, s, chan, announced);
    w += 2;
    iwx_awdl_end_tl(len, w);

    w = iwx_awdl_put_tl(w, 5, &len);
    w += 3;
    *w++ = uint8_t(s->height + 1);
    *w++ = 0;
    w = iwx_awdl_putmem(w, s->master, 6);
    w = iwx_awdl_put32(w, s->master_metric);
    w = iwx_awdl_put32(w, IWX_AWDL_SELF_METRIC);
    w += 2;
    iwx_awdl_end_tl(len, w);

    w = iwx_awdl_put_tl(w, 18, &len);
    w = iwx_awdl_put_chanseq16(w, s, chan, announced);
    w += 3;
    iwx_awdl_end_tl(len, w);
    return w;
}

/* A whole frame, MAC header included, from this driver's own TLVs. */
static inline size_t iwx_awdl_build(struct iwx_awdl_probe *p, const uint8_t *da, uint8_t subtype, uint64_t host_us,
                                    uint8_t *out, size_t cap) {
    static const uint8_t name[5] = {'b', 'e', '2', '0', '1'};
    const struct iwx_awdl_sync *s = &p->sync;
    if (cap < IWX_AWDL_FRAME_MAX || !s->valid || !iwx_awdl_chan_entry_size(s->encoding)) return 0;
    memset(out, 0, IWX_AWDL_FRAME_MAX);
    uint8_t *len;
    uint8_t *w = iwx_awdl_build_head(p, da, subtype, host_us, out);

    w = iwx_awdl_put_tl(w, 24, &len);
    w = iwx_awdl_putmem(w, s->master, 6);
    w = iwx_awdl_putmem(w, s->reference, 6);
    w = iwx_awdl_put32(w, s->master_counter);
    w = iwx_awdl_put32(w, uint32_t(s->height) + 1);
    w = iwx_awdl_put32(w, s->master_metric);
    w = iwx_awdl_put32(w, IWX_AWDL_SELF_METRIC);
    w += 12;
    iwx_awdl_end_tl(len, w);

    w = iwx_awdl_put_tl(w, 6, &len);
    w += 9;
    iwx_awdl_end_tl(len, w);

    if (subtype == 3) {
        w = iwx_awdl_put_tl(w, 7, &len);
        w += 2;
        w = iwx_awdl_put16(w, 0x11ce);
        *w++ = 0x1b;
        *w++ = 0xff;
        w += 2;
        iwx_awdl_end_tl(len, w);
        w = iwx_awdl_put_tl(w, 16, &len);
        *w++ = 3;
        *w++ = sizeof(name);
        w = iwx_awdl_putmem(w, name, sizeof(name));
        *w++ = 0xc0;
        *w++ = 0x0c;
        iwx_awdl_end_tl(len, w);
    }

    w = iwx_awdl_put_tl(w, 12, &len);
    w = iwx_awdl_put16(w, 0x8f24);
    *w++ = 'X';
    *w++ = '0';
    *w++ = 0;
    w = iwx_awdl_put16(w, s->master_channel == 6 ? 1 : (s->master_channel == 44 ? 2 : 4));
    w = iwx_awdl_putmem(w, p->tx.self, 6);
    w = iwx_awdl_put16(w, 0);
    iwx_awdl_end_tl(len, w);

    w = iwx_awdl_put_tl(w, 21, &len);
    *w++ = s->version;
    *w++ = 1;
    iwx_awdl_end_tl(len, w);
    return size_t(w - out);
}

/* Stack Ethernet to an AWDL data frame, from this interface's address. Returns the frame length, 0 if it does not fit. */
/*
 * awdl0 inherits TSO and partial checksum from the family, whose firmware finishes them; this path
 * has no such step. Rewrites an IPv6 TCP or UDP checksum and returns whether it was wrong.
 */
static inline bool iwx_awdl_fix_l4_csum(uint8_t *ip, size_t n) {
    if (n < 40 || (ip[0] >> 4) != 6 || (ip[6] != 6 && ip[6] != 17)) return false;
    const size_t l4 = (size_t(ip[4]) << 8) | ip[5], at = ip[6] == 6 ? 16 : 6;
    if (l4 > n - 40 || l4 < at + 2) return false;
    uint8_t *field = ip + 40 + at;
    const uint16_t was = uint16_t((field[0] << 8) | field[1]);
    field[0] = field[1] = 0;
    uint32_t sum = uint32_t(ip[6]) + uint32_t(l4);
    for (size_t i = 8; i < 40; i += 2) sum += uint32_t((ip[i] << 8) | ip[i + 1]);
    for (size_t i = 0; i + 1 < l4; i += 2) sum += uint32_t((ip[40 + i] << 8) | ip[40 + i + 1]);
    if (l4 & 1) sum += uint32_t(ip[40 + l4 - 1]) << 8;
    while (sum >> 16) sum = (sum & 0xffff) + (sum >> 16);
    uint16_t now = uint16_t(~sum);
    if (ip[6] == 17 && !now) now = 0xffff;
    field[0] = uint8_t(now >> 8);
    field[1] = uint8_t(now);
    return now != was;
}

static inline size_t iwx_awdl_ether_to_data(struct iwx_awdl_probe *p, const uint8_t *eth, size_t n, uint8_t *out, size_t cap) {
    static const uint8_t llc[10] = {0xaa, 0xaa, 0x03, 0x00, 0x17, 0xf2, 0x08, 0x00, 0x03, 0x04};
    if (!eth || n < 14 || 24 + 16 + (n - 14) > cap) return 0;
    uint8_t *w = out;
    *w++ = 0x08;
    *w++ = 0;
    w = iwx_awdl_put16(w, 0);
    w = iwx_awdl_putmem(w, eth, 6);
    w = iwx_awdl_putmem(w, p->tx.self, 6);
    w = iwx_awdl_putmem(w, iwx_awdl_bssid, 6);
    const uint16_t seq = p->tx.seq++;
    w = iwx_awdl_put16(w, uint16_t(seq << 4));
    w = iwx_awdl_putmem(w, llc, sizeof(llc));
    w = iwx_awdl_put16(w, seq);
    w = iwx_awdl_put16(w, 0);
    w = iwx_awdl_putmem(w, eth + 12, 2);
    uint8_t *payload = w;
    w = iwx_awdl_putmem(w, eth + 14, n - 14);
    if (eth[12] == 0x86 && eth[13] == 0xdd && iwx_awdl_fix_l4_csum(payload, n - 14)) ++p->tx.csum_fixed;
    return size_t(w - out);
}

/* As iwx_awdl_ether_to_data, but a QoS data MPDU on TID 0: the form the firmware aggregates. */
static inline size_t iwx_awdl_ether_to_qos(struct iwx_awdl_probe *p, const uint8_t *eth, size_t n, uint8_t *out, size_t cap) {
    static const uint8_t llc[10] = {0xaa, 0xaa, 0x03, 0x00, 0x17, 0xf2, 0x08, 0x00, 0x03, 0x04};
    if (!eth || n < 14 || 26 + 16 + (n - 14) > cap) return 0;
    uint8_t *w = out;
    *w++ = 0x88;
    *w++ = 0;
    w = iwx_awdl_put16(w, 0);
    w = iwx_awdl_putmem(w, eth, 6);
    w = iwx_awdl_putmem(w, p->tx.self, 6);
    w = iwx_awdl_putmem(w, iwx_awdl_bssid, 6);
    const uint16_t seq = p->tx.seq++;
    w = iwx_awdl_put16(w, uint16_t(seq << 4));
    w = iwx_awdl_put16(w, 0);
    w = iwx_awdl_putmem(w, llc, sizeof(llc));
    w = iwx_awdl_put16(w, seq);
    w = iwx_awdl_put16(w, 0);
    w = iwx_awdl_putmem(w, eth + 12, 2);
    uint8_t *payload = w;
    w = iwx_awdl_putmem(w, eth + 14, n - 14);
    if (eth[12] == 0x86 && eth[13] == 0xdd && iwx_awdl_fix_l4_csum(payload, n - 14)) ++p->tx.csum_fixed;
    return size_t(w - out);
}

/* The data path notes where unicast data goes; the own queue moves to that peer if it is a station. */
static inline void iwx_awdl_note_dest(struct iwx_awdl_probe *p, const uint8_t *eth) {
    if (!eth || (eth[0] & 1)) return;
    memcpy(p->tx.last_dest, eth, 6);
    p->tx.last_dest_valid = 1;
}
/* 1.2.15: the table entry for mac, or the least recently used one, reset for mac. */
static inline struct iwx_awdl_sync::iwx_awdl_dpeer *iwx_awdl_dpeer_slot(struct iwx_awdl_sync *s, const uint8_t *mac) {
    uint32_t old = 0;
    for (uint32_t i = 0; i < 4; ++i) {
        if (!memcmp(s->dpeer[i].mac, mac, 6)) return &s->dpeer[i];
        const auto &a = s->dpeer[i], &b = s->dpeer[old];
        if ((a.tx_us > a.seq_us ? a.tx_us : a.seq_us) < (b.tx_us > b.seq_us ? b.tx_us : b.seq_us)) old = i;
    }
    auto *e = &s->dpeer[old];
    memset(e, 0, sizeof(*e));
    memcpy(e->mac, mac, 6);
    return e;
}
static inline void iwx_awdl_note_dest_tx(struct iwx_awdl_probe *p, const uint8_t *eth, uint64_t now_us) {
    if (!eth || (eth[0] & 1)) return;
    iwx_awdl_dpeer_slot(&p->sync, eth)->tx_us = now_us;
    p->sync.intent_us = now_us;
}
static inline uint32_t iwx_awdl_seq_count(const uint8_t seq[16], uint8_t chan) {
    uint32_t n = 0;
    for (uint32_t i = 0; i < 16; ++i) n += chan && seq[i] == chan;
    return n;
}
static inline uint32_t iwx_awdl_seq_count5(const uint8_t seq[16]) {
    uint32_t n = 0;
    for (uint32_t i = 0; i < 16; ++i) n += seq[i] >= 36;
    return n;
}
/*
 * 1.2.13: a frame from a peer carries its own sequence. 1.2.15: kept per peer for a peer data went to lately, or one
 * whose sequence is widened (a transfer starting: 22:24 the phone widened before any data went to it).
 */
static inline void iwx_awdl_note_dest_seq(struct iwx_awdl_probe *p, const uint8_t *sender, const struct iwx_awdl_tlvs *t) {
    struct iwx_awdl_sync *s = &p->sync;
    if (!sender || (sender[0] & 1)) return;
    uint8_t q[16];
    if (!iwx_awdl_seq16(t, q)) return;
    /* 1.2.16: every sender, so its slots are known when an intent comes (the least recently used entry goes). */
    auto *e = iwx_awdl_dpeer_slot(s, sender);
    memcpy(e->seq, q, sizeof(q));
    e->seq_valid = 1;
    e->seq_us = p->rx_host_us;
    ++s->dest_updates;
}
/*
 * 1.2.15: the slots on chan that any active peer's own fresh sequence has: one data went to within
 * IWX_AWDL_DPEER_TX_US, or one widened to IWX_AWDL_DPEER_WIDE slots of chan. NULL when none: the family's sequence only,
 * as a native Mac with nothing to send (the reference's idle slots no longer keep this Mac off the AP).
 */
/*
 * 1.2.19: whether a unicast frame to mac waits for its peer's slot: that peer's sequence (heard in the last
 * IWX_AWDL_GATE_SEQ_US) is on chan for 1 to IWX_AWDL_DPEER_WIDE - 1 slots, and slot idx (its numbering) is not one.
 * Per destination: 13:24 (first 1.2.19 build) gated by the union of data peers, so frames to the iPad, whose sequence
 * had aged out, waited for an idle iPhone's three slots (GateWaits 349, 0.10 MB/s).
 */
#define IWX_AWDL_GATE_SEQ_US 10000000u
static inline bool iwx_awdl_gate_dest(const struct iwx_awdl_probe *p, const uint8_t *mac, uint8_t chan, uint32_t idx,
                                      uint64_t now_us)
{
    if (!mac || !chan)
        return false;
    for (const auto &e : p->sync.dpeer) {
        if (memcmp(e.mac, mac, 6))
            continue;
        if (!e.seq_valid || e.seq_us + IWX_AWDL_GATE_SEQ_US <= now_us)
            return false;
        uint32_t n = 0;
        for (uint32_t i = 0; i < 16; ++i)
            n += e.seq[i] == chan;
        return n && n < IWX_AWDL_DPEER_WIDE && e.seq[idx % 16] != chan;
    }
    return false;
}
static inline const uint8_t *iwx_awdl_union_seq(struct iwx_awdl_probe *p, uint64_t now_us, uint8_t chan,
                                                 bool dpeer_all = false, uint64_t fresh_us = IWX_AWDL_DEST_SEQ_US) {
    struct iwx_awdl_sync *s = &p->sync;
    uint8_t out[16] = {};
    bool any = false;
    const bool intent = s->intent_us && s->intent_us + IWX_AWDL_INTENT_US > now_us;
    for (const auto &e : s->dpeer) {
        if (!e.seq_valid || e.seq_us + fresh_us <= now_us) continue;
        const bool data = e.tx_us && e.tx_us + IWX_AWDL_DPEER_TX_US > now_us;
        if (!data && !intent && iwx_awdl_seq_count(e.seq, chan) < IWX_AWDL_DPEER_WIDE) continue;
        for (uint32_t i = 0; i < 16; ++i)
            if (chan && (e.seq[i] == chan || (data && dpeer_all))) { out[i] = chan; any = true; }
    }
    if (!any) return nullptr;
    memcpy(s->dest_seq, out, sizeof(out));
    s->dest_seq_valid = 1;
    return s->dest_seq;
}

/*
 * One QoS data MPDU, A-MSDU present, TID 0, normal ack. Each subframe is what iwx_awdl_ether_to_data
 * puts after the MAC header, behind a DA, SA and big-endian length, padded to four bytes but for the last.
 */
static inline size_t iwx_awdl_amsdu_build(struct iwx_awdl_probe *p, const uint8_t *const *eths, const size_t *lens, unsigned count,
    uint8_t *out, size_t cap, uint8_t tid = 0)
{
    static const uint8_t llc[10] = {0xaa, 0xaa, 0x03, 0x00, 0x17, 0xf2, 0x08, 0x00, 0x03, 0x04};
    if (!eths || !lens || !out || count < 2 || count > IWX_AWDL_AMSDU_MAX_FRAMES) return 0;
    size_t total = 26;
    for (unsigned i = 0; i < count; ++i) {
        if (!eths[i] || lens[i] < 14 || memcmp(eths[i], eths[0], 6)) return 0;
        total = ((total - 26 + 3) & ~size_t(3)) + 26 + 14 + 16 + (lens[i] - 14);
    }
    if (total > cap || (eths[0][0] & 1)) return 0;
    uint8_t *w = out;
    *w++ = 0x88;
    *w++ = 0;
    w = iwx_awdl_put16(w, 0);
    w = iwx_awdl_putmem(w, eths[0], 6);
    w = iwx_awdl_putmem(w, p->tx.self, 6);
    w = iwx_awdl_putmem(w, iwx_awdl_bssid, 6);
    w = iwx_awdl_put16(w, uint16_t(p->tx.seq << 4));
    *w++ = uint8_t(0x80 | (tid & 7)); /* A-MSDU present; 1.2.6: the TID is the caller's */
    *w++ = 0;
    uint8_t *const body = w;
    for (unsigned i = 0; i < count; ++i) {
        while ((w - body) & 3) *w++ = 0;
        const size_t payload = lens[i] - 14;
        w = iwx_awdl_putmem(w, eths[i], 6);
        w = iwx_awdl_putmem(w, p->tx.self, 6);
        *w++ = uint8_t((16 + payload) >> 8);
        *w++ = uint8_t(16 + payload);
        w = iwx_awdl_putmem(w, llc, sizeof(llc));
        const uint16_t seq = p->tx.seq++;
        w = iwx_awdl_put16(w, seq);
        w = iwx_awdl_put16(w, 0);
        w = iwx_awdl_putmem(w, eths[i] + 12, 2);
        uint8_t *data = w;
        w = iwx_awdl_putmem(w, eths[i] + 14, payload);
        if (eths[i][12] == 0x86 && eths[i][13] == 0xdd && iwx_awdl_fix_l4_csum(data, payload)) ++p->tx.csum_fixed;
    }
    return size_t(w - out);
}

/* Switched on, VHT rates in use, and this peer has agreed block ack, so it speaks QoS data with this Mac. */
static inline bool iwx_awdl_amsdu_ready(const struct iwx_awdl_probe *p, const uint8_t *dest) {
    if (!p->tx.amsdu || p->tx.amsdu_gave_up || p->tx.rate_step >= 0 || !dest) return false;
    for (uint32_t i = 0; i < IWX_AWDL_BA_MAX; ++i)
        if (p->ba[i].active && !memcmp(p->ba[i].peer, dest, 6)) return true;
    return false;
}

/*
 * 1.2.6: through the AUX station (mode 4) the block-ack test does not apply: the A-MSDU goes on IWX_AWDL_ROC_AMSDU_TID
 * as an ordinary acknowledged frame, and at most IWX_AWDL_ROC_AMSDU_MAX_BYTES long, the A-MSDU every HT receiver takes.
 */
#define IWX_AWDL_ROC_AMSDU_MAX_BYTES 3839u
static inline bool iwx_awdl_amsdu_ready_on(const struct iwx_awdl_probe *p, const uint8_t *dest, bool aux) {
    if (!aux)
        return iwx_awdl_amsdu_ready(p, dest);
    /*
     * 1.2.10: never on the TID 8 queue. 22:38: with the switch on, 6 A-MSDUs went and 1 completed, the transfer stopped
     * at once (AirDrop re-sent and re-resolved the phone), the router lost 20 % and the firmware asserted 0x20000070 on
     * ROC_CMD with an ROC that had not ended (55 ended of 56 started). 1.2.11: only when the AUX queue is on TID 3.
     */
    return p->tx.amsdu && !p->tx.amsdu_gave_up && dest && !(dest[0] & 1) && p->roc.tid == IWX_AWDL_ROC_AMSDU_TID;
}

static inline void iwx_awdl_amsdu_note_done(struct iwx_awdl_probe *p, bool ok) {
    struct iwx_awdl_tx *x = &p->tx;
    if (ok) ++x->amsdu_ok;
    else ++x->amsdu_fail;
    if (!x->amsdu_ok && x->amsdu_fail >= IWX_AWDL_AMSDU_GIVE_UP) x->amsdu_gave_up = 1;
}

/* The system's TLVs must walk cleanly: they go on air behind our own and are not rechecked. */
static inline bool iwx_awdl_native_template(struct iwx_awdl_probe *p, bool mif, const uint8_t *data, size_t n) {
    struct iwx_awdl_tx *x = &p->tx;
    bool ok = data && n && n <= IWX_AWDL_NATIVE_TLV_MAX;
    for (size_t off = 0; ok && off < n;) {
        if (n - off < 3) { ok = false; break; }
        const size_t l = iwx_awdl_le16(data + off + 1);
        if (l > n - off - 3) { ok = false; break; }
        off += 3 + l;
    }
    if (!ok) { ++x->native_rejected; return false; }
    memcpy(mif ? x->native_mif : x->native_psf, data, n);
    (mif ? x->native_mif_len : x->native_psf_len) = uint16_t(n);
    ++x->native_updates;
    return true;
}

/* A whole frame around the system's TLVs. Broadcast only; PSF is subtype 0, MIF 3. */
static inline size_t iwx_awdl_build_native(struct iwx_awdl_probe *p, bool mif, uint64_t host_us, uint8_t *out, size_t cap) {
    static const uint8_t broadcast[6] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff};
    const struct iwx_awdl_tx *x = &p->tx;
    const size_t n = mif ? x->native_mif_len : x->native_psf_len;
    if (cap < IWX_AWDL_NATIVE_FRAME_MAX || !n || !p->sync.valid || !iwx_awdl_chan_entry_size(p->sync.encoding)) return 0;
    memset(out, 0, IWX_AWDL_NATIVE_FRAME_MAX);
    uint8_t *w = iwx_awdl_build_head(p, broadcast, mif ? 3 : 0, host_us, out);
    if (size_t(w - out) + n > cap) return 0;
    memcpy(w, mif ? x->native_mif : x->native_psf, n);
    return size_t(w - out) + n;
}

/* A unicast master indication: the same frame as a MIF, to one peer, with the TLVs the family built for it. */
static inline size_t iwx_awdl_build_umi(struct iwx_awdl_probe *p, const uint8_t *peer, const uint8_t *tlvs, size_t n,
                                        uint64_t host_us, uint8_t *out, size_t cap) {
    if (!peer || (peer[0] & 1) || !tlvs || !n || n > IWX_AWDL_NATIVE_TLV_MAX || cap < IWX_AWDL_NATIVE_FRAME_MAX ||
        !p->sync.valid || !iwx_awdl_chan_entry_size(p->sync.encoding)) return 0;
    for (size_t off = 0; off < n;) {
        if (n - off < 3) return 0;
        const size_t l = iwx_awdl_le16(tlvs + off + 1);
        if (l > n - off - 3) return 0;
        off += 3 + l;
    }
    memset(out, 0, IWX_AWDL_NATIVE_FRAME_MAX);
    uint8_t *w = iwx_awdl_build_head(p, peer, 3, host_us, out);
    if (size_t(w - out) + n > cap) return 0;
    memcpy(w, tlvs, n);
    return size_t(w - out) + n;
}

/* Status for the family, 0 acked. A full list drops the oldest: the family times out on that one. */
static inline void iwx_awdl_umi_note(struct iwx_awdl_probe *p, const uint8_t *peer, bool ok) {
    if (ok) ++p->umi_ok;
    else ++p->umi_fail;
    if (p->umi_done_count == IWX_AWDL_UMI_DONE_MAX) {
        ++p->umi_dropped;
        memmove(&p->umi_done[0], &p->umi_done[1], sizeof(p->umi_done[0]) * (IWX_AWDL_UMI_DONE_MAX - 1));
        --p->umi_done_count;
    }
    memcpy(p->umi_done[p->umi_done_count].mac, peer, 6);
    p->umi_done[p->umi_done_count].status = ok ? 0 : 1;
    ++p->umi_done_count;
}

/*
 * llw0 shares awdl0's address. Native firmware tags which interface a frame is for; nothing here does, so frames
 * to an IPv6 ULA destination, or to a port llw0 has sent from, go to llw0. ICMPv6 goes to both, since either may be
 * resolving a neighbor.
 */
#define IWX_AWDL_LLW_PORTS 16u
struct iwx_awdl_llw_ports {
    uint16_t port[IWX_AWDL_LLW_PORTS];
    uint8_t proto[IWX_AWDL_LLW_PORTS];
    uint8_t next;
};
enum iwx_awdl_llw_route { IWX_AWDL_ROUTE_AWDL, IWX_AWDL_ROUTE_LLW, IWX_AWDL_ROUTE_BOTH };
static inline uint8_t iwx_awdl_llw_proto(const uint8_t *eth, size_t n) {
    if (n < 14 + 40 || eth[12] != 0x86 || eth[13] != 0xdd) return 0;
    return eth[14 + 6];
}
static inline void iwx_awdl_llw_learn(struct iwx_awdl_llw_ports *t, const uint8_t *eth, size_t n) {
    const uint8_t proto = iwx_awdl_llw_proto(eth, n);
    if ((proto != 6 && proto != 17) || n < 14 + 40 + 4) return;
    const uint16_t port = uint16_t(eth[14 + 40] << 8 | eth[14 + 41]);
    for (unsigned i = 0; i < IWX_AWDL_LLW_PORTS; ++i)
        if (t->port[i] == port && t->proto[i] == proto) return;
    t->port[t->next] = port;
    t->proto[t->next] = proto;
    t->next = uint8_t((t->next + 1) % IWX_AWDL_LLW_PORTS);
}
static inline enum iwx_awdl_llw_route iwx_awdl_llw_input(const struct iwx_awdl_llw_ports *t, const uint8_t *eth, size_t n) {
    const uint8_t proto = iwx_awdl_llw_proto(eth, n);
    if (proto == 58) return IWX_AWDL_ROUTE_BOTH;
    if ((proto != 6 && proto != 17) || n < 14 + 40 + 4 || (eth[0] & 1)) return IWX_AWDL_ROUTE_AWDL;
    /*
     * Low latency sessions (Rapport UDPNWPath: Continuity Camera, Sidecar) use per-session IPv6 ULA addresses, fc00::/7,
     * and the Mac is often the server: on 1.1.70 the phone's RTP to a llw0 listener never matched a port llw0 had sent
     * from, went to awdl0 and was lost (RTCP timeout). awdl0's own traffic (AirDrop, Universal Control) is link-local.
     */
    if ((eth[14 + 24] & 0xfe) == 0xfc) return IWX_AWDL_ROUTE_LLW;
    const uint16_t port = uint16_t(eth[14 + 42] << 8 | eth[14 + 43]);
    for (unsigned i = 0; i < IWX_AWDL_LLW_PORTS; ++i)
        if (t->port[i] == port && t->proto[i] == proto) return IWX_AWDL_ROUTE_LLW;
    return IWX_AWDL_ROUTE_AWDL;
}
/* Multicast on llw0 is neighbor discovery only: mDNS already runs on awdl0, and the air time is scarce. */
static inline bool iwx_awdl_llw_output_allowed(const uint8_t *eth, size_t n) {
    return n >= 14 && (!(eth[0] & 1) || iwx_awdl_llw_proto(eth, n) == 58);
}

static inline void iwx_awdl_tx_note_queued(struct iwx_awdl_probe *p, enum iwx_awdl_tx_kind kind, uint64_t host_us) {
    if (kind == IWX_AWDL_TX_UNICAST) { p->tx.last_unicast_us = host_us; ++p->tx.unicast_sent; return; }
    if (kind == IWX_AWDL_TX_MIF) p->tx.last_mif_us = host_us;
    else {
        p->tx.last_psf_us = host_us;
        ++p->tx.psf_sent;
    }
    ++p->tx.mcast_sent;
}

#define IWX_AWDL_RATE_HT (2 << 8)
#define IWX_AWDL_RATE_VHT (3 << 8)
#define IWX_AWDL_RATE_2SS (1 << 4)
#define IWX_AWDL_RATE_80MHZ (2 << 11)
#define IWX_AWDL_RATE_TOP_STEP (-3)

/*
 * The rate field without the antenna mask; -1 for the lowest legacy rate, all 1.1.38 sent, about
 * 0.55 MB/s. Starts at step 0 and climbs after clean runs: a phone advertised VHT, two streams, MCS 0-9.
 */
static inline int32_t iwx_awdl_data_rate(int32_t step) {
    switch (step) {
    case -3: return IWX_AWDL_RATE_VHT | IWX_AWDL_RATE_80MHZ | IWX_AWDL_RATE_2SS | 9;
    case -2: return IWX_AWDL_RATE_VHT | IWX_AWDL_RATE_80MHZ | IWX_AWDL_RATE_2SS | 7;
    case -1: return IWX_AWDL_RATE_VHT | IWX_AWDL_RATE_2SS | 8;
    case 0: return IWX_AWDL_RATE_HT | 7;
    case 1: return IWX_AWDL_RATE_HT | 4;
    case 2: return IWX_AWDL_RATE_HT | 2;
    default: return -1;
    }
}

/*
 * 1.1.95: AWDL unicast rates at 80 MHz only on a PHY that is 80 MHz wide. An ROC is always 20 MHz, and so is link 1 on
 * the second channel (1.1.90); before, only the AP's width was checked, so a climbed rate step put VHT 80 MHz frames
 * on 20 MHz channels. Falls back to the 20 MHz top step.
 */
static inline bool iwx_awdl_rate_fits(int32_t rate, bool ap_wide, bool roc, bool phy2)
{
    return rate < 0 || !(rate & IWX_AWDL_RATE_80MHZ) || (ap_wide && !roc && !phy2);
}

static inline void iwx_awdl_rate_note(struct iwx_awdl_tx *x, bool ok) {
    if (!x->rate_up_after) x->rate_up_after = 64;
    if (ok) {
        x->rate_fail = 0;
        if (++x->rate_ok >= x->rate_up_after && x->rate_step > IWX_AWDL_RATE_TOP_STEP) {
            --x->rate_step;
            x->rate_ok = 0;
            ++x->rate_ups;
        }
        return;
    }
    /* It was on another channel: says nothing about this rate. */
    if (x->peer_away) return;
    x->rate_ok = 0;
    if (++x->rate_fail >= 2 && x->rate_step < 3) {
        ++x->rate_step;
        x->rate_fail = 0;
        ++x->rate_downs;
        /* A rate that failed is not retried soon. */
        if (x->rate_up_after < 4096) x->rate_up_after *= 2;
    }
}

/*
 * 1.2.8: the AUX path's rate. 2026-11-13 22:10 (1.2.7, router on 36): the transfer started but ran at 0.01-0.02 MB/s;
 * AUX unicast went at 0x8100 (6 Mbit/s legacy, about 2 ms per frame) where 21:39 used 0xC318 (VHT 2SS MCS8, 171 us).
 * The link-wide ladder (iwx_awdl_rate_note) steps down after 2 failures of any AWDL unicast, own queue and ROC-end
 * flushes included, below HT to the legacy rate, and doubles the successes it needs to climb each time (up to 4096),
 * so once down it stayed down, and A-MSDU, which needs step 0 or better, never came on. Now AUX frames have their own
 * step: it starts at VHT 20 MHz MCS8 (99.9 % acknowledged at 21:39), counts only failures inside an ROC, steps down
 * after IWX_AWDL_ROC_RATE_DOWN of them and up after IWX_AWDL_ROC_RATE_UP successes, and never below HT MCS2.
 */
#define IWX_AWDL_ROC_RATE_START (-1)
#define IWX_AWDL_ROC_RATE_FLOOR 2
#define IWX_AWDL_ROC_RATE_UP 32u
#define IWX_AWDL_ROC_RATE_DOWN 4u
static inline void iwx_awdl_roc_rate_note(struct iwx_awdl_roc *r, bool ok, bool in_roc, int32_t top)
{
    if (ok) {
        r->rate_fail = 0;
        if (++r->rate_ok >= IWX_AWDL_ROC_RATE_UP && r->rate_step > top) {
            --r->rate_step;
            r->rate_ok = 0;
            ++r->rate_ups;
        }
        return;
    }
    if (!in_roc)
        return; /* failed by the ROC's end: says nothing about the rate */
    r->rate_ok = 0;
    if (++r->rate_fail >= IWX_AWDL_ROC_RATE_DOWN && r->rate_step < IWX_AWDL_ROC_RATE_FLOOR) {
        ++r->rate_step;
        r->rate_fail = 0;
        ++r->rate_downs;
    }
}

/* unicast comes from the frame's address 1; retries are the firmware's own. */
static inline void iwx_awdl_tx_note_done(struct iwx_awdl_probe *p, bool unicast, bool ok, uint32_t status, uint32_t retries,
                                         bool rate = true) {
    struct iwx_awdl_tx *x = &p->tx;
    if (!ok) x->last_fail_status = status;
    if (unicast) {
        if (rate) /* 1.2.8: not for AUX frames, which have their own step */
            iwx_awdl_rate_note(x, ok);
        ++*(x->peer_away ? (ok ? &x->ok_away : &x->fail_away) : (ok ? &x->ok_here : &x->fail_here));
        if (ok) ++x->unicast_ack;
        else ++x->unicast_noack;
        x->unicast_retries += retries;
    } else if (ok) ++x->mcast_ok;
    else ++x->mcast_fail;
}

/* Category 3, sent to this interface in the AWDL BSS. Fills req for an ADDBA request or a DELBA. */
static inline bool iwx_awdl_ba_parse(const uint8_t *self, const uint8_t *f, size_t len, struct iwx_awdl_ba_req *req) {
    if (!self || !f || !req || len < 24 + 6 || f[0] != 0xd0 || memcmp(f + 4, self, 6) ||
        memcmp(f + 16, iwx_awdl_bssid, 6) || f[24] != 3)
        return false;
    const uint8_t *b = f + 24;
    memset(req, 0, sizeof(*req));
    memcpy(req->peer, f + 10, 6);
    if (b[1] == 0) {
        if (len < 24 + 9) return false;
        req->dialog = b[2];
        req->param = iwx_awdl_le16(b + 3);
        req->timeout = iwx_awdl_le16(b + 5);
        req->ssn = uint16_t(iwx_awdl_le16(b + 7) >> 4);
        req->tid = uint8_t((req->param >> 2) & 15);
        req->win = uint16_t(req->param >> 6);
        if (!req->win || req->win > IWX_AWDL_BA_WINDOW) req->win = IWX_AWDL_BA_WINDOW;
        return req->tid < 8;
    }
    if (b[1] == 2) {
        const uint16_t param = iwx_awdl_le16(b + 2);
        /* A session the peer started: the initiator bit. Sessions this side started do not exist yet. */
        if (!(param & 0x0800)) return false;
        req->del = 1;
        req->tid = uint8_t(param >> 12);
        return req->tid < 8;
    }
    return false;
}

/* No A-MSDU: delivery here takes one packet per MPDU. Immediate policy, the peer's TID and timeout. */
static inline size_t iwx_awdl_ba_build_resp(const uint8_t *self, const struct iwx_awdl_ba_req *req, uint16_t status,
    uint8_t *out, size_t cap)
{
    if (!self || !req || !out || cap < 24 + 9) return 0;
    memset(out, 0, 24);
    out[0] = 0xd0;
    memcpy(out + 4, req->peer, 6);
    memcpy(out + 10, self, 6);
    memcpy(out + 16, iwx_awdl_bssid, 6);
    uint8_t *w = out + 24;
    *w++ = 3;
    *w++ = 1;
    *w++ = req->dialog;
    w = iwx_awdl_put16(w, status);
    w = iwx_awdl_put16(w, uint16_t(0x0002 | (uint16_t(req->tid) << 2) | (req->win << 6)));
    w = iwx_awdl_put16(w, req->timeout);
    return size_t(w - out);
}

static inline int iwx_awdl_peer_index(const struct iwx_awdl_probe *p, const uint8_t *peer) {
    for (uint32_t i = 0; i < p->peer_added && i < IWX_AWDL_PEER_STA_MAX; ++i)
        if (!memcmp(p->peer_addr[i], peer, 6)) return int(i);
    return -1;
}

/* Counts unicast data bytes for a peer station; others are not candidates for the own queue. */
static inline void iwx_awdl_note_bytes(struct iwx_awdl_probe *p, const uint8_t *eth, size_t n) {
    if (!eth || (eth[0] & 1)) return;
    const int i = iwx_awdl_peer_index(p, eth);
    if (i < 0) return;
    const uint64_t sum = uint64_t(p->tx.dest_bytes[i]) + n;
    p->tx.dest_bytes[i] = sum > 0xffffffffull ? 0xffffffffu : uint32_t(sum);
}

static inline bool iwx_awdl_bulk_active(const struct iwx_awdl_probe *p, uint64_t now_us) {
    if (!p->tx.dest_window_us || now_us < p->tx.dest_window_us || now_us - p->tx.dest_window_us > IWX_AWDL_SCAN_DEFER_STALE_US)
        return false;
    uint64_t sum = 0;
    for (uint32_t i = 0; i < IWX_AWDL_PEER_STA_MAX; ++i)
        sum += uint64_t(p->tx.dest_bytes_last[i]) + p->tx.dest_bytes[i];
    return sum >= IWX_AWDL_SCAN_DEFER_BYTES;
}

/* Bulk now, or within IWX_AWDL_SCAN_HOLD_US of the last tick that saw it (1.1.80). */
static inline bool iwx_awdl_bulk_recent(const struct iwx_awdl_probe *p, uint64_t now_us) {
    return iwx_awdl_bulk_active(p, now_us) ||
        (p->tx.bulk_last_us && now_us >= p->tx.bulk_last_us && now_us - p->tx.bulk_last_us < IWX_AWDL_SCAN_HOLD_US);
}

/* Appends one sample; the ring keeps the last IWX_AWDL_HIST_LEN. */
static inline void iwx_awdl_hist_add(struct iwx_awdl_probe *p, const struct iwx_awdl_hist *h) {
    p->hist[p->hist_next % IWX_AWDL_HIST_LEN] = *h;
    p->hist_next = (p->hist_next + 1) % IWX_AWDL_HIST_LEN;
}

/* Closes the byte window once it is IWX_AWDL_OWN_BULK_WINDOW_US old. True when a new window was closed. */
static inline bool iwx_awdl_bytes_roll(struct iwx_awdl_probe *p, uint64_t now_us) {
    if (!p->tx.dest_window_us) {
        p->tx.dest_window_us = now_us;
        return false;
    }
    if (now_us - p->tx.dest_window_us < IWX_AWDL_OWN_BULK_WINDOW_US) return false;
    memcpy(p->tx.dest_bytes_last, p->tx.dest_bytes, sizeof(p->tx.dest_bytes_last));
    memset(p->tx.dest_bytes, 0, sizeof(p->tx.dest_bytes));
    p->tx.dest_window_us = now_us;
    return true;
}

/* The peer that should take the own queue from current (-1 for none yet), or -1 to leave it where it is. */
static inline int iwx_awdl_own_bulk_peer(const uint32_t *bytes, uint32_t count, int current) {
    int best = -1;
    uint32_t most = 0;
    for (uint32_t i = 0; i < count; ++i)
        if (bytes[i] > most) { most = bytes[i]; best = int(i); }
    if (best < 0 || best == current || most < IWX_AWDL_OWN_BULK_BYTES) return -1;
    const uint64_t cur = current >= 0 && uint32_t(current) < count ? bytes[current] : 0;
    return uint64_t(most) >= 4 * cur ? best : -1;
}

static inline struct iwx_awdl_ba *iwx_awdl_ba_find(struct iwx_awdl_probe *p, const uint8_t *peer, uint8_t tid) {
    for (uint32_t i = 0; i < IWX_AWDL_BA_MAX; ++i)
        if (p->ba[i].active && p->ba[i].tid == tid && !memcmp(p->ba[i].peer, peer, 6)) return &p->ba[i];
    return NULL;
}

static inline struct iwx_awdl_ba *iwx_awdl_ba_free(struct iwx_awdl_probe *p) {
    for (uint32_t i = 0; i < IWX_AWDL_BA_MAX; ++i)
        if (!p->ba[i].active) return &p->ba[i];
    return NULL;
}

/* True when the task should run. One slot: the peer repeats a request nobody answered. */
static inline bool iwx_awdl_ba_note(struct iwx_awdl_probe *p, const uint8_t *f, size_t len) {
    struct iwx_awdl_ba_req req;
    if (!iwx_awdl_ba_parse(p->tx.self, f, len, &req)) return false;
    if (!req.del) {
        ++p->ba_heard;
        memcpy(p->ba_sample, f + 24, sizeof(p->ba_sample));
    }
    p->ba_pending = req;
    p->ba_pending_valid = 1;
    return true;
}

static inline void iwx_awdl_probe_note_sender(struct iwx_awdl_probe *p, const uint8_t *sender) {
    const uint16_t hash = iwx_awdl_sender_hash(sender);
    for (uint32_t i = 0; i < p->sender_count; ++i)
        if (p->senders[i] == hash) return;
    if (p->sender_count < IWX_AWDL_PROBE_MAX_SENDERS)
        p->senders[p->sender_count++] = hash;
}

/*
 * Runs once the station is associated, on the raw frame. Only frames the wider
 * filter newly admits are dropped; beacons, probe responses and everything in
 * our own BSS continue exactly as before.
 */
/* For the native interface: management, and AWDL data for this address or a group. */
static inline bool iwx_awdl_rx_wanted(const struct iwx_awdl_probe *p, const uint8_t *f, size_t len) {
    if (!f || len < 24) return false;
    if ((f[0] & 0x0c) == 0x00) return true;
    return (f[0] & 0x0c) == 0x08 && !(f[1] & 0x03) && !memcmp(f + 16, iwx_awdl_bssid, 6) &&
        ((f[4] & 1) || !memcmp(f + 4, p->tx.self, 6));
}

/* The heard cluster's next AW boundary: its number, and how long until it starts. False if nothing recent. */
static inline bool iwx_awdl_sync_next(const struct iwx_awdl_probe *p, uint64_t host_us, uint16_t *seq, uint32_t *wait_us) {
    const struct iwx_awdl_sync *s = &p->sync;
    if (!s->valid || !s->aw_period || !s->presence || host_us < s->host_us || host_us - s->host_us > 2000000u)
        return false;
    const int64_t period = int64_t(s->presence) * s->aw_period * IWX_AWDL_TU_US;
    int64_t left = int64_t(s->ttn) * IWX_AWDL_TU_US - int64_t(host_us - s->host_us);
    uint16_t next = uint16_t(s->aw_seq + s->presence);
    if (left <= 0) {
        const int64_t wraps = (-left) / period + 1;
        left += wraps * period;
        next = uint16_t(next + wraps * s->presence);
    }
    *seq = next;
    *wait_us = uint32_t(left);
    return true;
}

/*
 * True when the peer that sets the schedule is on another channel right now. False whenever that
 * is not known, or when it never visits chan: holding would then stop traffic for good.
 */
static inline bool iwx_awdl_peer_away(const struct iwx_awdl_probe *p, const uint8_t *dest, uint64_t host_us, uint8_t chan) {
    const struct iwx_awdl_sync *s = &p->sync;
    uint16_t next = 0;
    uint32_t wait = 0;
    if (!s->seq_valid || !chan || !dest || memcmp(dest, s->reference, 6) || !iwx_awdl_sync_next(p, host_us, &next, &wait))
        return false;
    bool visits = false;
    for (unsigned i = 0; i < 16; ++i)
        visits |= s->seq[i] == chan;
    if (!visits) return false;
    return s->seq[(uint16_t(next - s->presence) / s->presence) % 16] != chan;
}

/* The channel the reference peer's schedule has for the slot running now; 0 when unknown or asleep. */
static inline uint8_t iwx_awdl_peer_slot_chan(const struct iwx_awdl_probe *p, uint64_t host_us) {
    const struct iwx_awdl_sync *s = &p->sync;
    uint16_t next = 0;
    uint32_t wait = 0;
    if (!s->seq_valid || !s->presence || !iwx_awdl_sync_next(p, host_us, &next, &wait))
        return 0;
    return s->seq[(uint16_t(next - s->presence) / s->presence) % 16];
}

/*
 * 1.2.1: the reference peer's (the phone's) run of chan that runs now or starts at its next boundary, from its own
 * sequence and AW timing, covering at most run_max slots of the run. -1 unknown, 0 no such run, 1 found (w filled).
 * 2026-11-13 17:03 (1.2.0, router on 157, idle sequence with single 149 slots): AUX unicast 0 of 137 acknowledged,
 * 130 failed after their ROC with the phone's schedule still on 149: ROCs timed by this Mac's slots missed the phone's.
 */
struct iwx_awdl_peer_window {
    uint64_t start_us, end_us;
    uint32_t cur, slots, wait_us, slot_us;
};
static inline int iwx_awdl_peer_run(const struct iwx_awdl_probe *p, uint8_t chan, uint32_t run_max, uint64_t host_us,
                                    struct iwx_awdl_peer_window *w)
{
    const struct iwx_awdl_sync *s = &p->sync;
    uint16_t next = 0;
    uint32_t wait = 0;
    if (!s->seq_valid || !s->presence || !s->aw_period || !chan || !run_max ||
        !iwx_awdl_sync_next(p, host_us, &next, &wait))
        return -1;
    const uint64_t slot = uint64_t(s->presence) * s->aw_period * IWX_AWDL_TU_US;
    const uint32_t cur = (uint16_t(next - s->presence) / s->presence) % 16;
    w->cur = cur;
    w->wait_us = wait;
    w->slot_us = uint32_t(slot);
    uint8_t cov[16];
    iwx_awdl_roc_cover(s->seq, chan, run_max, cov);
    uint32_t first;
    if (cov[cur]) {
        first = cur;
        w->start_us = host_us;
    } else if (cov[(cur + 1) % 16]) {
        first = (cur + 1) % 16;
        w->start_us = host_us + wait;
    } else {
        w->slots = 0;
        w->start_us = w->end_us = host_us;
        return 0;
    }
    uint32_t n = 0;
    while (n < 16 && cov[(first + n) % 16])
        ++n;
    w->slots = n;
    w->end_us = (first == cur ? host_us + wait : host_us + wait + slot) + uint64_t(n - 1) * slot;
    return 1;
}
/* 1.2.1: the phone's slot index less ours at our tick, rounding a boundary less than half a slot away to the next. */
static inline uint32_t iwx_awdl_peer_k(uint32_t peer_cur, uint32_t wait_us, uint32_t slot_us, uint32_t own_idx)
{
    const uint32_t at = (peer_cur + (slot_us && wait_us < slot_us / 2 ? 1u : 0u)) % 16;
    return (at + 16 - own_idx % 16) % 16;
}
/* 1.2.1: the phone's boundary against our tick: later (+) by wait, or earlier (-) by the rest of its slot. */
static inline int32_t iwx_awdl_peer_lag(uint32_t wait_us, uint32_t slot_us)
{
    if (!slot_us)
        return 0;
    return wait_us < slot_us / 2 ? int32_t(wait_us) : -int32_t(slot_us - wait_us % slot_us);
}
/*
 * 1.2.9: cover the phone's 149 slots too. 2026-11-13 22:24 (1.2.8, router on 36): AUX unicast 18/2, 67/1, 87/1 at
 * VHT, yet AirDrop sent almost nothing: sharingd's Bonjour resolution of the phone over awdl0 failed after 30 s
 * ("DNS Error: Refused", repeated "Ask failed Code=6"), and the QUIC/TLS connection that finally came up at the end
 * took 7.5 s. The phone had widened its sequence to 15 of 16 slots on 149 to receive, while this Mac's family stayed
 * idle (2 slots) until a connection existed, so every reply waited up to a second for our next visit. The union
 * marks a slot on chan where the family's sequence or the phone's (in this Mac's numbering, shifted by k) has it.
 */
#define IWX_AWDL_ROC_F_NO_UNION 0x4000u
static inline uint32_t iwx_awdl_seq_union(const uint8_t fam[16], const uint8_t *peer, uint32_t k, uint8_t chan, uint8_t out[16])
{
    uint32_t added = 0;
    for (uint32_t i = 0; i < 16; ++i) {
        const bool f = fam[i] == chan, ph = peer && chan && peer[(i + k) % 16] == chan;
        out[i] = (f || ph) ? chan : fam[i];
        if (ph && !f)
            ++added;
    }
    return added;
}
/* 1.2.1: a held frame waits for the phone's run to start, even inside an ROC. */
static inline bool iwx_awdl_roc_peer_wait(const struct iwx_awdl_roc *r, uint64_t now_us)
{
    return r->peer_timed && now_us < r->peer_start_us;
}

/* Whether to ask for a window now: mode 1 once a second, mode 2 while the peer is on the second channel. */
static inline uint32_t iwx_awdl_te_due(const struct iwx_awdl_probe *p, uint32_t mode, uint32_t chan, uint64_t host_us, uint64_t last_us) {
    if (!chan || !mode) return 0;
    if (mode == 1)
        return host_us - last_us >= IWX_AWDL_TE_INTERVAL_US ? IWX_AWDL_TE_DURATION_TU : 0;
    if (mode != 2 || host_us - last_us < IWX_AWDL_TE_SLOT_GAP_US) return 0;
    return iwx_awdl_peer_slot_chan(p, host_us) == chan ? IWX_AWDL_TE_SLOT_TU : 0;
}

/*
 * Mode 3: a window when this Mac's own slot starting now is on the second channel. Only at a run's first slot (run > 0),
 * only for the slot tick just reported, and not while an earlier window still runs. Duration in TU, 0 for none.
 */
static inline uint32_t iwx_awdl_te_own_due(uint8_t slot_chan, uint8_t slot_run, uint32_t chan, uint64_t slot_us,
                                           uint64_t host_us, uint64_t te_end_us) {
    if (!chan || slot_chan != chan || !slot_run || host_us < te_end_us) return 0;
    /* A tick handled late would put the window into the next slot: AP time lost for nothing. */
    if (host_us - slot_us > IWX_AWDL_OWN_SLOT_TU * IWX_AWDL_TU_US / 4) return 0;
    const uint32_t run = slot_run < IWX_AWDL_OWN_SLOT_RUN_MAX ? slot_run : IWX_AWDL_OWN_SLOT_RUN_MAX;
    return run * IWX_AWDL_OWN_SLOT_TU;
}

/* Modes that make link 1 follow this Mac's own sequence, and those that keep the own queue across the moves. */
static inline bool iwx_awdl_te_follows(uint32_t te) { return te >= 4 && te <= 7; }
static inline bool iwx_awdl_te_keeps_own(uint32_t te) { return te >= 5 && te <= 7; }
/* Modes whose AWDL frames use link 1's queue on the second channel (6 to 8). */
static inline bool iwx_awdl_te_phy2q(uint32_t te) { return te >= 6 && te <= 8; }
/*
 * Modes with session protection windows (1 to 6). 7 and 8 open none and leave link 1's time to the firmware:
 * in 1.1.64 nothing on link 1's queues was sent during windows (Phy2QDone 0 of 8 held, own queue 2 of 47).
 */
static inline bool iwx_awdl_te_windows(uint32_t te) { return te >= 1 && te <= 6; }

/*
 * Mode 4: where link 1 should be for the coming slots. The second channel when the next 5 GHz slot of this Mac's own
 * sequence is on it, otherwise the AP's channel (0). On a router on 36 the sequence 36 0 149 0 ... 6 0 149 gives 149
 * from slot 1 to slot 10 and 36 from slot 11 to slot 0: slot 0 on 36 is where the phone found this Mac (2026-11-08).
 */
static inline uint8_t iwx_awdl_phy2_follow(uint8_t cand, uint8_t next5) {
    return cand && next5 == cand ? cand : 0;
}

/*
 * Automatic second channel: a 5 GHz channel of this Mac's own sequence that the AP is not on. seq holds the first two
 * different ones, low byte first. On a router on 36 the family's sequence was 36 0 149 0 0 0 0 0 6 0 149 ...: slot 0
 * on the AP's channel, so taking only the first 5 GHz channel (1.1.54 to 1.1.57) never chose 149.
 */
static inline uint8_t iwx_awdl_phy2_auto(uint16_t seq, uint8_t home) {
    const uint8_t a = uint8_t(seq & 0xff), b = uint8_t(seq >> 8);
    if (a >= 36 && a != home) return a;
    return b >= 36 && b != home ? b : 0;
}

/*
 * The station a new peer may replace: an added one with nothing staged for it, not keep (the own queue's peer), heard
 * least recently; with idle_only, only one quiet for IWX_AWDL_PEER_IDLE_US. now_us 0 (no clock) replaces nothing.
 */
static inline int iwx_awdl_peer_victim(const struct iwx_awdl_probe *p, uint64_t now_us, int keep, bool idle_only) {
    int victim = -1;
    for (uint32_t i = 0; now_us && i < p->peer_added && i < IWX_AWDL_PEER_STA_MAX; ++i) {
        if (int(i) == keep || (p->peer_replace & (1u << i))) continue;
        if (idle_only && now_us - p->peer_seen_us[i] < IWX_AWDL_PEER_IDLE_US) continue;
        if (victim < 0 || p->peer_seen_us[i] < p->peer_seen_us[victim]) victim = int(i);
    }
    return victim;
}

/* Index whose staged replacement is this address, or -1. */
static inline int iwx_awdl_peer_pending(const struct iwx_awdl_probe *p, const uint8_t *mac) {
    for (uint32_t i = 0; i < IWX_AWDL_PEER_STA_MAX; ++i)
        if ((p->peer_replace & (1u << i)) && !memcmp(p->peer_new[i], mac, 6)) return int(i);
    return -1;
}

/*
 * True when an AWDL action frame names a new nearby sender (a station to add or to put in a quiet station's place).
 * Far ones would use up the table in a crowd. A known sender only refreshes when it was last heard.
 */
static inline bool iwx_awdl_peer_note(struct iwx_awdl_probe *p, const uint8_t *f, size_t len, int rssi,
                                      uint64_t now_us = 0, int keep = -1) {
    if (!p->assoc_rx || p->peer_failed || !f || len < 24 || f[0] != 0xd0 || (f[10] & 1) ||
        memcmp(f + 16, iwx_awdl_bssid, 6))
        return false;
    for (uint32_t i = 0; i < p->peer_count && i < IWX_AWDL_PEER_STA_MAX; ++i)
        if (!memcmp(p->peer_addr[i], f + 10, 6)) {
            p->peer_seen_us[i] = now_us;
            return false;
        }
    if (rssi < IWX_AWDL_PEER_MIN_RSSI || iwx_awdl_peer_pending(p, f + 10) >= 0)
        return false;
    if (p->peer_count < IWX_AWDL_PEER_STA_MAX) {
        p->peer_seen_us[p->peer_count] = now_us;
        memcpy(p->peer_addr[p->peer_count++], f + 10, 6);
        return true;
    }
    const int v = iwx_awdl_peer_victim(p, now_us, keep, true);
    if (v < 0) return false;
    memcpy(p->peer_new[v], f + 10, 6);
    p->peer_replace = uint8_t(p->peer_replace | (1u << v));
    return true;
}

/*
 * The family asks for a peer in the firmware's cache: for this driver that is a peer station. True when the
 * task should run. A delete is answered and the station stays, but it is the first to give its place (1.1.77). A full
 * table makes room: the family asks for the peer it is about to send to, so the least recently heard station that
 * the own queue does not use is replaced, quiet or not. Full with no such station is no answer.
 */
static inline bool iwx_awdl_cache_request(struct iwx_awdl_probe *p, const uint8_t *mac, uint32_t op,
                                          uint64_t now_us = 0, int keep = -1) {
    if (!p->assoc_rx || p->peer_failed || !mac || (mac[0] & 1)) return false;
    uint32_t i = 0;
    while (i < p->peer_count && memcmp(p->peer_addr[i], mac, 6)) ++i;
    if (op == IWX_AWDL_CACHE_REQ_DELETE) {
        if (i == p->peer_count) return false;
        p->cache_del_wait = uint8_t(p->cache_del_wait | (1u << i));
        p->peer_seen_us[i] = 0;
        return true;
    }
    if (i == p->peer_count) {
        const int pending = iwx_awdl_peer_pending(p, mac);
        if (pending >= 0) {
            i = uint32_t(pending);
        } else if (p->peer_count < IWX_AWDL_PEER_STA_MAX) {
            p->peer_seen_us[p->peer_count] = now_us;
            memcpy(p->peer_addr[p->peer_count++], mac, 6);
        } else {
            const int v = iwx_awdl_peer_victim(p, now_us, keep, false);
            if (v < 0) {
                ++p->cache_full;
                return false;
            }
            memcpy(p->peer_new[v], mac, 6);
            p->peer_replace = uint8_t(p->peer_replace | (1u << v));
            i = uint32_t(v);
        }
    } else
        p->peer_seen_us[i] = now_us;
    p->cache_add_wait = uint8_t(p->cache_add_wait | (1u << i));
    return true;
}

static inline enum iwx_awdl_probe_action
iwx_awdl_probe_rx(struct iwx_awdl_probe *p, const uint8_t *f, size_t len, const uint8_t *bss) {
    if (!f || !bss || len < 2) return IWX_AWDL_PROBE_DROP;
    const uint8_t type = f[0] & 0x0c, subtype = f[0] & 0xf0;
    if (type == 0x04) /* Control: keep only BlockAckReq for our own traffic. */
        return subtype == 0x80 ? IWX_AWDL_PROBE_KEEP : IWX_AWDL_PROBE_DROP;
    if (len < 24) return IWX_AWDL_PROBE_KEEP;
    const uint8_t ds = f[1] & 0x03;
    if (type == 0x08 && ds != 0) return IWX_AWDL_PROBE_KEEP; /* Infrastructure data. */
    if (type != 0x00 && type != 0x08) return IWX_AWDL_PROBE_KEEP;
    const uint8_t *bssid = f + 16;
    if (!memcmp(bssid, bss, 6)) return IWX_AWDL_PROBE_KEEP;
    const bool in_awdl = !memcmp(bssid, iwx_awdl_bssid, 6);
    if (in_awdl) {
        ++p->awdl_bssid;
        iwx_awdl_probe_note_sender(p, f + 10);
    }
    if (type == 0x08) {
        if (!in_awdl) ++p->foreign_data;
        else {
            ++p->awdl_data;
            if (!memcmp(f + 4, p->tx.self, 6)) ++p->awdl_data_self;
        }
        ++p->dropped;
        return IWX_AWDL_PROBE_DROP;
    }
    if (subtype == 0x80 || subtype == 0x50) return IWX_AWDL_PROBE_KEEP; /* Beacon, probe response. */
    ++p->foreign_mgmt;
    if (subtype == 0xd0) {
        ++p->foreign_action;
        const uint8_t *b = f + 24;
        if (len >= 24 + 4 && b[0] == 127 && b[1] == 0x00 && b[2] == 0x17 && b[3] == 0xf2) {
            ++p->apple_action;
            if (len >= 24 + 7 && b[4] == 8) {
                ++p->awdl_action;
                iwx_awdl_probe_note_sender(p, f + 10);
                if (b[6] == 0) ++p->awdl_psf;
                else if (b[6] == 3) ++p->awdl_mif;
                iwx_awdl_note_frame(p, f + 10, b, len - 24);
            }
        }
    }
    ++p->dropped;
    return IWX_AWDL_PROBE_DROP;
}
/*
 * Data-mode hold (1.2.17). The family keeps the AWDL data schedule only while it counts at least 8 packets between two
 * monitorAWDLDataMode checks (initParamsToDefaults 0x3ea4, a check every 8 AWs). 2026-11-14 12:04-12:08 (iPad, 1.2.16):
 * the transfer started slow, the checks saw "Tx:0 Rx:0" or a few packets, and the schedule went Data, Idle, Low Power
 * ([60 0 149 0 0 0 0 0 6 0 149 ...]) within seconds, over and over. The Mac then announced 2 slots of 16 on 149, so the
 * iPad could answer only twice a second, the round trip grew, and the transfer never left 0.01-0.05 MB/s. The iPhone
 * climbed out of the same start; the iPad did not.
 *
 * While a unicast flow runs both ways (IWX_AWDL_HOLD_FLOW_PKTS in a window of IWX_AWDL_HOLD_WIN_US, at least one each
 * way), each report until IWX_AWDL_HOLD_US after the last such window counts at least IWX_AWDL_HOLD_PKTS packets. Idle
 * Bonjour or a lone keepalive does not start it, and the family idles as before once the flow stops.
 */
#define IWX_AWDL_HOLD_PKTS 8u
#define IWX_AWDL_HOLD_FLOW_PKTS 4u
#define IWX_AWDL_HOLD_WIN_US 1000000u
#define IWX_AWDL_HOLD_US 4000000u
/*
 * 1.2.21: a bulk flow (IWX_AWDL_HOLD_BULK_PKTS unicast packets in a window of IWX_AWDL_HOLD_BULK_WIN_US) holds for
 * IWX_AWDL_HOLD_BULK_US after it. 13:49-13:53 (1.2.20, to the iPad): QUIC's backoff left gaps longer than 4 s, the
 * family went Idle and Low Power each time, the round trip reached 1.1 s and the transfer never recovered.
 */
#define IWX_AWDL_HOLD_BULK_PKTS 300u
#define IWX_AWDL_HOLD_BULK_WIN_US 10000000u
#define IWX_AWDL_HOLD_BULK_US 15000000u
struct iwx_awdl_dmhold {
    uint64_t win_us, flow_us;
    uint32_t win_tx, win_rx;
    uint32_t flows, padded_reports, padded_pkts;
    uint64_t bulk_win_us, bulk_until_us;
    uint32_t bulk_n, bulk_holds;
};
/* Unicast packets since the last call; returns how many to add to this report so it reaches IWX_AWDL_HOLD_PKTS. */
static inline uint32_t iwx_awdl_dmhold_pad(struct iwx_awdl_dmhold *h, uint64_t now_us, uint32_t utx, uint32_t urx,
                                           uint32_t tx, uint32_t rx)
{
    if (!h->win_us || now_us - h->win_us >= IWX_AWDL_HOLD_WIN_US) {
        h->win_us = now_us ? now_us : 1;
        h->win_tx = h->win_rx = 0;
    }
    h->win_tx += utx;
    h->win_rx += urx;
    /* The hold runs from the last unicast packet of a window that met the flow rule. */
    if ((utx || urx) && h->win_tx && h->win_rx && h->win_tx + h->win_rx >= IWX_AWDL_HOLD_FLOW_PKTS) {
        if (!h->flow_us || now_us - h->flow_us >= IWX_AWDL_HOLD_US)
            ++h->flows;
        h->flow_us = now_us ? now_us : 1;
    }
    if (!h->bulk_win_us || now_us - h->bulk_win_us >= IWX_AWDL_HOLD_BULK_WIN_US) {
        h->bulk_win_us = now_us ? now_us : 1;
        h->bulk_n = 0;
    }
    h->bulk_n += utx + urx;
    if (h->bulk_n >= IWX_AWDL_HOLD_BULK_PKTS && (utx || urx)) {
        if (!h->bulk_until_us || now_us >= h->bulk_until_us)
            ++h->bulk_holds;
        h->bulk_until_us = now_us + IWX_AWDL_HOLD_BULK_US;
    }
    const bool flowHold = h->flow_us && now_us - h->flow_us < IWX_AWDL_HOLD_US;
    const bool bulkHold = h->bulk_until_us && now_us < h->bulk_until_us;
    if ((!flowHold && !bulkHold) || tx + rx >= IWX_AWDL_HOLD_PKTS)
        return 0;
    const uint32_t pad = IWX_AWDL_HOLD_PKTS - (tx + rx);
    ++h->padded_reports;
    h->padded_pkts += pad;
    return pad;
}

/* 1.2.19: whether the frame to a1 waits now (iwx_awdl_roc_gate_wait for its own peer, iwx_awdl_gate_dest). */
static inline bool iwx_awdl_roc_gate_check(const struct iwx_awdl_probe *p, const uint8_t *a1, uint64_t now_us)
{
    const auto r = &p->roc;
    const bool unicast = a1 && !(a1[0] & 1);
    return iwx_awdl_roc_gate_wait((r->want & IWX_AWDL_ROC_F_GATE) != 0,
                                  unicast && iwx_awdl_gate_dest(p, a1, r->gate_chan, uint32_t(r->slot_idx) + r->gate_k, now_us),
                                  unicast, r->gate_us, now_us);
}

#endif
