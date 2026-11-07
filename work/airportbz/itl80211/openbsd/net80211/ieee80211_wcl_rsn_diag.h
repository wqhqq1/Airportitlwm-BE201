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
/* Addresses are compared only; no identifiers enter the diagnostic ring. */
static inline int wcl_address_equal(const uint8_t *a, const uint8_t *b) {
    unsigned diff = 0;
    for (unsigned i = 0; i < 6; ++i) diff |= a[i] ^ b[i];
    return diff == 0;
}
static inline int wcl_sta_teardown_matches(const uint8_t *da,
    const uint8_t *sa, const uint8_t *bssid, const uint8_t *local,
    const uint8_t *peer, const uint8_t *peer_bssid) {
    if (!da || !sa || !bssid || !local || !peer || !peer_bssid) return 0;
    unsigned broadcast = 0;
    for (unsigned i = 0; i < 6; ++i) broadcast |= da[i] ^ 0xff;
    return (wcl_address_equal(da, local) || broadcast == 0) &&
        wcl_address_equal(sa, peer) && wcl_address_equal(bssid, peer_bssid);
}
/* Only inspect the public eight-byte SNAP header of an unprotected frame. */
static inline uint32_t wcl_rsn_tx_kind(const uint8_t *snap, unsigned length,
    unsigned stage, int port_valid, int protected_frame) {
    if (!snap || length < 8 || port_valid || protected_frame ||
        (stage != 2 && stage != 4)) return 0;
    const uint8_t eapol[8] = {0xaa, 0xaa, 3, 0, 0, 0, 0x88, 0x8e};
    unsigned diff = 0;
    for (unsigned i = 0; i < 8; ++i) diff |= snap[i] ^ eapol[i];
    return diff ? 0 : stage;
}
static inline void wcl_rsn_tx_completed(struct wcl_rsn_trace *trace,
    uint32_t marked_cookie, uint32_t current_cookie, uint32_t kind, uint32_t status) {
    if (marked_cookie && marked_cookie == current_cookie && (kind == 2 || kind == 4))
        wcl_rsn_note(trace, kind == 2 ? 23 : 24, status);
}
/* SEC_KEY v1: inspect only action/key-id/flags; skip the secret key bytes. */
static inline uint32_t wcl_key_read32(const uint8_t *p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) |
        (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
static inline uint32_t wcl_key_command_tag(uint32_t code, const uint8_t *p, unsigned length) {
    if ((code & 0xffff) != 0x0518 || !p || length != 80) return 0;
    uint32_t action = wcl_key_read32(p), key_id = wcl_key_read32(p + 8);
    if ((action != 1 && action != 3) || key_id > 5) return 0;
    return (action << 24) | (key_id << 16) | (wcl_key_read32(p + 12) & 0xffff);
}
static inline void wcl_key_command_completed(struct wcl_rsn_trace *trace,
    uint32_t marked_cookie, uint32_t current_cookie, uint32_t tag, int failed) {
    if (marked_cookie && marked_cookie == current_cookie &&
        ((tag >> 24) == 1 || (tag >> 24) == 3))
        wcl_rsn_note(trace, failed ? 28 : 27, tag);
}
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
