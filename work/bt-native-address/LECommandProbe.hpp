// SPDX-License-Identifier: GPL-2.0-or-later
// Submission metadata only. No address, IRK, key, PIN, or payload is retained.
#pragma once
#include <stdint.h>
#include <stddef.h>

namespace be201probe {
struct Statistics {
    uint64_t sequence;
    uint64_t commandCount, malformedCount, submitErrors;
    uint64_t nativeRandomCount, nativeRandomSequence, nativeRandomKind;
    uint64_t nativeRandomSinceReset;
    uint64_t placeholderCount, placeholderSequence, nativeBeforePlaceholder;
    uint64_t scanCount, scanOwnAddressType;
    uint64_t connectCount, connectSequence, connectOpcode;
    uint64_t connectOwnAddressType, connectPeerAddressType, connectFilterPolicy;
    uint64_t connectPHYMask, nativeBeforeConnect;
    uint64_t resolvingListAdds, resolvingListClears;
    uint64_t resolutionEnableCount, resolutionEnabled;
    uint64_t controllerResetCount;
    uint64_t nativeRPAUSBAccepted, placeholderSkipped;
};
static inline uint64_t load(const uint64_t &v) {
    return __atomic_load_n(&v, __ATOMIC_RELAXED);
}
static inline void put(uint64_t &v, uint64_t x) {
    __atomic_store_n(&v, x, __ATOMIC_RELAXED);
}
static inline uint64_t increment(uint64_t &v) {
    return __atomic_add_fetch(&v, 1, __ATOMIC_RELAXED);
}
static inline void injectedRandomAddress(Statistics &s) {
    increment(s.placeholderCount);
    put(s.placeholderSequence, increment(s.sequence));
    put(s.nativeBeforePlaceholder, load(s.nativeRandomSinceReset));
}
static inline void submitted(Statistics &s, const uint8_t *bytes, size_t size) {
    const uint64_t seq = increment(s.sequence);
    if (!bytes || size < 3) { increment(s.malformedCount); return; }
    const size_t length = bytes[2];
    if (length > size - 3) { increment(s.malformedCount); return; }
    const uint16_t opcode = uint16_t(bytes[0] | (uint16_t(bytes[1]) << 8));
    const uint8_t *p = bytes + 3;
    increment(s.commandCount);
    switch (opcode) {
    case 0x0c03: // Reset submission, not its completion.
        if (length == 0) {
            increment(s.controllerResetCount); put(s.nativeRandomSinceReset, 0);
        }
        break;
    case 0x2005: // LE Set Random Address: retain only the two-bit address kind.
        if (length != 6) { increment(s.malformedCount); break; }
        increment(s.nativeRandomCount); put(s.nativeRandomSequence, seq);
        put(s.nativeRandomSinceReset, 1);
        put(s.nativeRandomKind, p[5] >> 6);
        break;
    case 0x200b: // LE Set Scan Parameters.
        if (length != 7) { increment(s.malformedCount); break; }
        increment(s.scanCount); put(s.scanOwnAddressType, p[5]);
        break;
    case 0x200d: // LE Create Connection.
        if (length != 25) { increment(s.malformedCount); break; }
        increment(s.connectCount); put(s.connectSequence, seq);
        put(s.connectOpcode, opcode); put(s.connectFilterPolicy, p[4]);
        put(s.connectPeerAddressType, p[5]); put(s.connectOwnAddressType, p[12]);
        put(s.connectPHYMask, 1);
        put(s.nativeBeforeConnect, load(s.nativeRandomSinceReset));
        break;
    case 0x2043: { // LE Extended Create Connection, 16 bytes per selected PHY.
        if (length < 10) { increment(s.malformedCount); break; }
        const unsigned phys = p[9];
        const unsigned count = ((phys & 1) != 0) + ((phys & 2) != 0) + ((phys & 4) != 0);
        if (!count || (phys & ~7U) || length != 10 + 16 * count) {
            increment(s.malformedCount); break;
        }
        increment(s.connectCount); put(s.connectSequence, seq);
        put(s.connectOpcode, opcode); put(s.connectFilterPolicy, p[0]);
        put(s.connectOwnAddressType, p[1]); put(s.connectPeerAddressType, p[2]);
        put(s.connectPHYMask, phys);
        put(s.nativeBeforeConnect, load(s.nativeRandomSinceReset));
        break;
    }
    case 0x2027: // Resolving-list entry: deliberately never inspect key bytes.
        if (length == 39) increment(s.resolvingListAdds);
        else increment(s.malformedCount);
        break;
    case 0x2029:
        if (length == 0) increment(s.resolvingListClears);
        else increment(s.malformedCount);
        break;
    case 0x202d:
        if (length == 1) {
            increment(s.resolutionEnableCount); put(s.resolutionEnabled, p[0]);
        } else increment(s.malformedCount);
        break;
    default:
        break;
    }
}
} // namespace be201probe
