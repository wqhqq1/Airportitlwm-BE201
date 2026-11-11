// GPL-2.0-or-later. Side-effect-free validation before firmware state changes.
#pragma once
#ifdef KERNEL
#include <libkern/libkern.h>
#else
#include <cstddef>
#include <cstdint>
#endif

static inline uint32_t ItlReadLE32(const uint8_t *p)
{
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 |
           uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}

static inline bool ItlFirmwareEnvelopeValid(const void *buffer, size_t size)
{
    if (!buffer || size < 8)
        return false;
    const auto bytes = static_cast<const uint8_t *>(buffer);
    size_t offset = 0;
    while (offset < size) {
        if (size - offset < 8)
            return false;
        const size_t length = ItlReadLE32(bytes + offset + 4);
        offset += 8;
        // Check payload and padding separately, without rounded-length overflow.
        if (length > size - offset)
            return false;
        offset += length;
        const size_t padding = (4 - (length & 3)) & 3;
        if (padding > size - offset)
            return false;
        offset += padding;
    }
    return true;
}
