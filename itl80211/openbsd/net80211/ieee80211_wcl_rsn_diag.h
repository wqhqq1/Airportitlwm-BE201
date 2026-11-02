/* Bounded numeric-only join diagnostics; no frames, addresses or secrets. */
#ifndef IEEE80211_WCL_RSN_DIAG_H
#define IEEE80211_WCL_RSN_DIAG_H
#include <stdint.h>
struct wcl_rsn_event { uint32_t code, value; };
struct wcl_rsn_trace {
    uint32_t enabled, count, next;
    struct wcl_rsn_event events[32];
};
static inline void wcl_rsn_note(struct wcl_rsn_trace *t, uint32_t code, uint32_t value) {
    if (!t->enabled) return;
    t->events[t->next].code = code;
    t->events[t->next].value = value;
    t->next = (t->next + 1) % 32;
    if (t->count != UINT32_MAX) ++t->count;
}
struct wcl_join_snapshot {
    uint32_t magic, version, request, starts, status, reason, driver_status;
    uint32_t state, node_flags, assoc, beacon, port, channel, akm, cipher, proto;
    uint32_t eapol, badmic, replay, deauth, key_cipher, rsn_length, deferred;
    struct wcl_rsn_trace rsn;
};
#ifdef __cplusplus
static_assert(sizeof(wcl_rsn_trace) == 268, "numeric trace wire size");
static_assert(sizeof(wcl_join_snapshot) == 360, "numeric join snapshot wire size");
#endif
#ifdef AIRPORT_WCL
#define WCL_RSN_NOTE(ic, code, value) wcl_rsn_note(&(ic)->ic_wcl_rsn_trace, code, value)
#else
#define WCL_RSN_NOTE(ic, code, value) ((void)0)
#endif
#endif
