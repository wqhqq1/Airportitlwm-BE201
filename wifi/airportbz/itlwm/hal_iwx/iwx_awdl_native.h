/* SPDX-License-Identifier: ISC
 * Receive-only native AWDL binding. The caller owns the workloop gate.
 * Does not send firmware commands or modify the AP address/filter.
 */
#ifndef IWX_AWDL_NATIVE_H
#define IWX_AWDL_NATIVE_H
#include "iwx_awdl_probe.h"
// 0: first request staged, 1: identical request, -1: invalid, -2: conflicting legacy/native context.
static inline int iwx_awdl_native_request(struct iwx_awdl_probe *p, bool *requested, const uint8_t *address)
{
    if (!address || (address[0] & 1)) return -1;
    uint8_t nonzero = 0;
    for (unsigned i = 0; i < 6; ++i) nonzero |= address[i];
    if (!nonzero) return -1;
    if (*requested) return memcmp(p->tx.self, address, 6) ? -2 : 1;
    if (p->ctx.mode || p->ctx.stage || p->tx.mode) return -2;
    memcpy(p->tx.self, address, 6);
    p->ctx.mode = 6; p->ctx.qid = -1; p->ctx.phy2_qid = -1;
    p->mode = 3; p->tx.mode = 0; p->assoc_rx = 1;
    *requested = true;
    return 0;
}
#endif
