// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <stdint.h>
#include <stddef.h>

namespace be201address {
// Experimental transport-based policy, not proof of HCI command completion.
// Keeps no Bluetooth address/key. A new reset/address submission invalidates
// the previous decision; late USB returns cannot resurrect an older decision.
struct Guard {
    uintptr_t owner;
    uint64_t epoch;
    bool bind(uintptr_t device) {
        if (!device) return false;
        uintptr_t expected = 0;
        __atomic_compare_exchange_n(&owner, &expected, device, false,
                                    __ATOMIC_RELAXED, __ATOMIC_RELAXED);
        return __atomic_load_n(&owner, __ATOMIC_RELAXED) == device;
    }
    uint64_t invalidate() {
        uint64_t old = __atomic_load_n(&epoch, __ATOMIC_ACQUIRE), next;
        do { next = (old | 1ULL) + 1; }
        while (!__atomic_compare_exchange_n(&epoch, &old, next, false,
                                            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE));
        return next;
    }
    bool preserve(uintptr_t device) const {
        return __atomic_load_n(&owner, __ATOMIC_RELAXED) == device &&
               (__atomic_load_n(&epoch, __ATOMIC_ACQUIRE) & 1);
    }
    void rejected(uint64_t ticket) {
        uint64_t current = __atomic_load_n(&epoch, __ATOMIC_ACQUIRE);
        while ((current & ~1ULL) == ticket && ticket &&
               !__atomic_compare_exchange_n(&epoch, &current, ticket + 2, false,
                                              __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {}
    }
    bool accepted(uint64_t ticket, bool synchronous, bool usbOK, size_t transferred) {
        if (!ticket || !synchronous || !usbOK || transferred != 9) return false;
        return __atomic_compare_exchange_n(&epoch, &ticket, ticket | 1, false,
                                            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE);
    }
};
static inline bool header(const uint8_t *p, size_t n, uint16_t opcode, uint8_t length) {
    return p && n >= size_t(length) + 3 && p[0] == uint8_t(opcode) &&
           p[1] == uint8_t(opcode >> 8) && p[2] == length;
}
static inline bool validRPACommand(const uint8_t *p, size_t n) {
    if (!header(p, n, 0x2005, 6) || (p[8] >> 6) != 1) return false;
    // The 22 random prand bits must contain at least one 0 and one 1.
    const uint32_t prand = uint32_t(p[6]) | uint32_t(p[7]) << 8 | uint32_t(p[8] & 0x3f) << 16;
    return prand != 0 && prand != 0x3fffff;
}
}
