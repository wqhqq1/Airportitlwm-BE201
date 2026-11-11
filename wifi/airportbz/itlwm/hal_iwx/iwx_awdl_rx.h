/* SPDX-License-Identifier: ISC
 * Native receive adapter, pinned to Sequoia 24G824. Input has no FCS or DMA pad.
 * Only action bodies are passed to the family's parser; this does not enable TX.
 */
#ifndef IWX_AWDL_RX_H
#define IWX_AWDL_RX_H
#include "iwx_awdl_probe.h"
struct iwx_awdl_rx_header {
    uint8_t sender[6], reserved0[6];
    uint32_t channel_version, channel, channel_flags;
    uint8_t reserved1[16];
    uint32_t device_us;
    int32_t rssi_dbm;
    uint32_t rate;
    uint8_t reserved2[20];
};
static_assert(sizeof(iwx_awdl_rx_header) == 0x48, "24G824 action header size");
static_assert(__builtin_offsetof(iwx_awdl_rx_header, channel) == 0x10, "channel offset");
static_assert(__builtin_offsetof(iwx_awdl_rx_header, device_us) == 0x28, "device time offset");
static_assert(__builtin_offsetof(iwx_awdl_rx_header, rssi_dbm) == 0x2c, "RSSI offset");

static inline bool iwx_awdl_rx_prepare(const uint8_t *frame, size_t length,
    uint8_t channel, int rssi, uint32_t device_us, iwx_awdl_rx_header *header)
{
    if (!frame || !header || length < 24 + IWX_AWDL_ACTION_LEN || length > 2048 ||
        !channel || channel > 177 || rssi < -127 || rssi > 0)
        return false;
    // Unfragmented, unencrypted vendor action frame, no DS addressing.
    if (frame[0] != 0xd0 || (frame[1] & 0xc7) || (frame[22] & 15) ||
        (frame[10] & 1) || memcmp(frame + 16, iwx_awdl_bssid, 6))
        return false;
    uint8_t nonzero = 0;
    for (unsigned i = 0; i < 6; ++i) nonzero |= frame[10 + i];
    if (!nonzero) return false;
    const uint8_t *body = frame + 24;
    // body[5] is the AWDL version, which actionFrameHasCorrectOUI requires to be nonzero.
    if (body[0] != 127 || body[1] || body[2] != 0x17 || body[3] != 0xf2 ||
        body[4] != 8 || !body[5] || (body[6] != 0 && body[6] != 3))
        return false;
    // TLVs are left to the family's parser, which bounds each one. Firmware delivers frames this
    // walk rejects (ParseBad): dropping them here lost most PSFs on 1.1.30.
    memset(header, 0, sizeof(*header));
    memcpy(header->sender, frame + 10, 6);
    header->channel_version = 1;
    header->channel = channel;
    header->channel_flags = 2 | (channel <= 14 ? 8 : 16); // 20 MHz, 2.4/5 GHz
    header->device_us = device_us; // Same clock as the AW start events this driver posts.
    header->rssi_dbm = rssi;
    return true;
}

/*
 * Peer data to Ethernet for the stack. AWDL data as the family frames it: LLC aa aa 03 00 17 f2 08 00,
 * then 03 04, sequence, pad, Ethertype. Returns the Ethernet length, 0 for anything else.
 */
static inline size_t iwx_awdl_data_to_ether(const uint8_t *frame, size_t length, const uint8_t *self,
    uint8_t *out, size_t cap)
{
    static const uint8_t llc[10] = {0xaa, 0xaa, 0x03, 0x00, 0x17, 0xf2, 0x08, 0x00, 0x03, 0x04};
    if (!frame || !self || !out || length < 24 || (frame[0] & 0x0c) != 0x08 || (frame[0] & 0x40) || (frame[1] & 0xc7))
        return 0;
    const size_t mac = (frame[0] & 0x80) ? 26 : 24;
    const size_t head = mac + 16;
    if (length <= head || memcmp(frame + 16, iwx_awdl_bssid, 6) || (frame[10] & 1) || (frame[22] & 15) ||
        ((frame[4] & 1) == 0 && memcmp(frame + 4, self, 6)) || memcmp(frame + mac, llc, sizeof(llc)))
        return 0;
    const size_t payload = length - head;
    if (payload + 14 > cap) return 0;
    memcpy(out, frame + 4, 6);
    memcpy(out + 6, frame + 10, 6);
    memcpy(out + 12, frame + head - 2, 2);
    memcpy(out + 14, frame + head, payload);
    return payload + 14;
}
#endif
