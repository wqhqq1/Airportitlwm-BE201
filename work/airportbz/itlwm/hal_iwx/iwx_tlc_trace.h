/* Bounded TLC v4 / sanitized LINK v2 history. No command-path allocation. */
#ifndef IWX_TLC_TRACE_H
#define IWX_TLC_TRACE_H
#include <stdint.h>

struct iwx_tlc_trace_record {
    uint32_t ordinal, generation, state, node_flags, node_width, rx_nss;
    uint32_t command_header, command_version, payload_length;
    uint8_t payload[28];
};

struct iwx_tlc_trace {
    uint32_t magic, version, count, next, frozen;
    uint32_t error_id, error_data1, error_command, error_generation;
    iwx_tlc_trace_record records[8];
};
static_assert(sizeof(iwx_tlc_trace_record) == 64, "TLC trace record ABI");
static_assert(sizeof(iwx_tlc_trace) == 548, "TLC trace snapshot ABI");

inline void iwx_tlc_trace_append(iwx_tlc_trace &trace, uint32_t generation,
    uint32_t state, uint32_t node_flags, uint32_t width, uint32_t nss,
    uint32_t header, uint32_t version, const void *payload, unsigned length)
{
    // The caller supplies the final command-ring bytes, immediately before
    // the doorbell. Never retain a different command (especially key material).
    const bool tlc = (header & 0xffff) == 0x050f && version == 4 && length == 28;
    const bool link = (header & 0xffff) == 0x0309 && version == 2 && length == 208;
    if (trace.frozen || (!tlc && !link) || !payload)
        return;
    trace.magic = 0x31434c54; // "TLC1", little endian x86_64
    trace.version = 2;
    if (trace.count != UINT32_MAX)
        ++trace.count;
    iwx_tlc_trace_record &r = trace.records[trace.next];
    r.ordinal = trace.count;
    r.generation = generation;
    r.state = state;
    r.node_flags = node_flags;
    r.node_width = width;
    r.rx_nss = nss;
    r.command_header = header;
    r.command_version = version;
    r.payload_length = length;
    const uint8_t *bytes = static_cast<const uint8_t *>(payload);
    if (tlc) {
        for (unsigned i = 0; i < sizeof(r.payload); ++i)
            r.payload[i] = bytes[i];
    } else {
        // Exactly seven documented u32 fields. Skip all link/BSSID addresses.
        const unsigned offsets[7] = {0, 4, 8, 12, 24, 28, 32};
        for (unsigned i = 0; i < 7; ++i)
            for (unsigned j = 0; j < 4; ++j)
                r.payload[4*i+j] = bytes[offsets[i]+j];
    }
    trace.next = (trace.next + 1) % 8;
}

inline bool iwx_tlc_trace_freeze(iwx_tlc_trace &trace, uint32_t error_id,
    uint32_t data1, uint32_t command, uint32_t generation)
{
    if (trace.frozen || !error_id)
        return false;
    trace.magic = 0x31434c54;
    trace.version = 2;
    trace.error_id = error_id;
    trace.error_data1 = data1;
    trace.error_command = command;
    trace.error_generation = generation;
    trace.frozen = 1;
    return true;
}
#endif
