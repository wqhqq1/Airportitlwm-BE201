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
#define IWX_AWDL_ROC_SLOT_TU 16u
#define IWX_AWDL_ROC_MAX_TU 128u
#define IWX_AWDL_ROC_DELAY_TU 16u
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
    uint32_t fault_roc, fault_phy2;
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
};

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

struct iwx_awdl_probe {
    uint32_t mode;            /* 0 off, 1 mgmt filter, 2 mgmt filter + promiscuous, 3 own context */
    uint32_t assoc_rx;        /* Mode 6 also holds a station and association, for data receive. */
    /* Nearby AWDL senders that get a firmware station. Staged here, sent by the peer task. */
    uint8_t peer_addr[IWX_AWDL_PEER_STA_MAX][6];
    uint32_t peer_count, peer_added, peer_failed, peer_errors;
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
static inline void iwx_awdl_sync_note_seq(struct iwx_awdl_sync *s, const struct iwx_awdl_tlvs *t) {
    s->seq_valid = 0;
    if (!t->chanseq || t->chanseq_len < 6) return;
    const uint8_t *v = t->chanseq;
    const size_t size = iwx_awdl_chan_entry_size(v[1]);
    if (!size || v[0] != 15 || 6 + 16 * size > t->chanseq_len) return;
    for (size_t i = 0; i < 16; ++i) {
        const uint8_t *e = v + 6 + i * size;
        s->seq[i] = v[1] == 1 ? e[1] : e[0];
    }
    s->seq_valid = 1;
}

/* Follow one cluster: the current reference, or another once it has gone quiet. */
static inline void iwx_awdl_note_frame(struct iwx_awdl_probe *p, const uint8_t *sender, const uint8_t *body, size_t n) {
    struct iwx_awdl_tlvs t;
    if (!iwx_awdl_parse(body, n, &t)) ++p->parse_bad;
    uint8_t aux = 0, aux_found = 0;
    iwx_awdl_note_chanseq(p, &t, &aux, &aux_found);
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

static inline uint8_t *iwx_awdl_put_chanseq(uint8_t *w, const struct iwx_awdl_sync *s, uint8_t chan) {
    const size_t size = iwx_awdl_chan_entry_size(s->encoding);
    *w++ = 15;
    *w++ = s->encoding;
    *w++ = 0;
    *w++ = 3;
    w = iwx_awdl_put16(w, 0xffff);
    for (unsigned i = 0; i < 16; ++i) {
        if (size == 1) { *w++ = chan; continue; }
        *w++ = s->encoding == 1 ? s->chan_aux : chan;
        *w++ = s->encoding == 1 ? chan : s->chan_aux;
    }
    return w;
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
    w = iwx_awdl_put_chanseq(w, s, chan);
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
    w = iwx_awdl_put_chanseq(w, s, chan);
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

/*
 * One QoS data MPDU, A-MSDU present, TID 0, normal ack. Each subframe is what iwx_awdl_ether_to_data
 * puts after the MAC header, behind a DA, SA and big-endian length, padded to four bytes but for the last.
 */
static inline size_t iwx_awdl_amsdu_build(struct iwx_awdl_probe *p, const uint8_t *const *eths, const size_t *lens, unsigned count,
    uint8_t *out, size_t cap)
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
    *w++ = 0x80;
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

/* unicast comes from the frame's address 1; retries are the firmware's own. */
static inline void iwx_awdl_tx_note_done(struct iwx_awdl_probe *p, bool unicast, bool ok, uint32_t status, uint32_t retries) {
    struct iwx_awdl_tx *x = &p->tx;
    if (!ok) x->last_fail_status = status;
    if (unicast) {
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
#endif
