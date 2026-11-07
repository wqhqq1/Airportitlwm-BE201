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
    uint64_t nativeRPAValidCommands, nativeRPAAsyncSubmissions, nativeRPAAsyncCompletions;
    uint64_t nativeRPAAsyncStatus, nativeRPAAsyncBytes, nativeRPASyncBytes;
    uint64_t nativeRPAObserverAllocationFailures;
    uint64_t acceptListAdds, acceptListClears, acceptListLastAddressType;
    uint64_t eventCount, eventMalformed, lastCommandOpcode, lastCommandStatus;
    uint64_t randomAddressHCICompletions, randomAddressHCIErrors;
    uint64_t connectCommandStatuses, connectCommandLastStatus;
    uint64_t connectionCompleteCount, connectionCompleteLastStatus;
    uint64_t connectionCompleteSuccesses, connectionCompleteFailures;
    uint64_t eventObserverAllocationFailures, eventUSBErrors;
    uint64_t eventPipeCaptures, eventReadCallbacks, eventReadFailures;
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
    case 0x2010:
        if (length == 0) increment(s.acceptListClears);
        else increment(s.malformedCount);
        break;
    case 0x2011:
        if (length == 7) { increment(s.acceptListAdds); put(s.acceptListLastAddressType, p[0]); }
        else increment(s.malformedCount);
        break;
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
static inline void eventPrefix(Statistics &s, const uint8_t *p, size_t prefixSize, size_t totalSize) {
    increment(s.sequence); increment(s.eventCount);
    if (!p || prefixSize < 2 || totalSize < 2 || size_t(p[1]) > totalSize - 2) {
        increment(s.eventMalformed); return;
    }
    if (p[0] == 0x0e) {
        if (p[1] < 4 || prefixSize < 6) { increment(s.eventMalformed); return; }
        const unsigned opcode = p[3] | (unsigned(p[4]) << 8);
        if (opcode == 0x2005 || opcode == 0x200b || opcode == 0x200e ||
            opcode == 0x2010 || opcode == 0x2011 || opcode == 0x2027 || opcode == 0x202d) {
            put(s.lastCommandOpcode, opcode); put(s.lastCommandStatus, p[5]);
        }
        if (opcode == 0x2005) {
            increment(s.randomAddressHCICompletions);
            if (p[5]) increment(s.randomAddressHCIErrors);
        }
    } else if (p[0] == 0x0f) {
        if (p[1] != 4 || prefixSize < 6) { increment(s.eventMalformed); return; }
        const unsigned opcode = p[4] | (unsigned(p[5]) << 8);
        if (opcode == 0x200d || opcode == 0x2043) {
            increment(s.connectCommandStatuses); put(s.connectCommandLastStatus, p[2]);
        }
    } else if (p[0] == 0x3e) {
        if (p[1] < 1 || prefixSize < 3) { increment(s.eventMalformed); return; }
        if (p[2] != 1 && p[2] != 0x0a) return;
        if (p[1] < (p[2] == 1 ? 19 : 31) || prefixSize < 4) {
            increment(s.eventMalformed); return;
        }
        increment(s.connectionCompleteCount); put(s.connectionCompleteLastStatus, p[3]);
        if (p[3]) increment(s.connectionCompleteFailures);
        else increment(s.connectionCompleteSuccesses);
    }
}
} // namespace be201probe
