/* SPDX-License-Identifier: ISC
 * Firmware commands for a separate AWDL context (be201_awdl_ctx=2 to 6): its own MAC,
 * link and station, so the AP station's receive filter stays as it is.
 * It is a P2P client that never associates, the state a station holds before
 * authentication, with the AWDL BSSID as its peer. Linux allows a station and a P2P
 * client together. Group filter alone (2) delivered no AWDL frame on 1.1.14;
 * 3 also takes management and control frames on this MAC only, and received 463 AWDL
 * frames on 1.1.15, but the firmware completed almost none of its transmits. 4 also marks
 * this MAC associated; firmware still held its frames on 1.1.16. 5 stays unassociated and
 * asks for session protection; firmware accepted the windows on 1.1.17 and still held the
 * frames. 6 keeps only the MAC and link, for the address and receive filter, and transmits on
 * the AP station's queue, the one path a phone has been seen to accept frames from. The native
 * AWDL interface also marks this MAC associated with the AWDL BSSID as its AP: unassociated, it
 * delivered no data on 1.1.31. AWDL data is framed like TDLS, no DS with A3 the BSSID. Alternatives
 * tried: promiscuous delivered group data on 1.1.33 and 1.1.36, associated or not, but stopped all
 * this MAC's ACKs and the AP station's traffic; an IBSS MAC was refused at activation on 1.1.34
 * (0x200014FC, 149). Association alone delivered no data on 1.1.36 while the phone sent SYNs, so
 * each nearby sender also gets a station, as a TDLS peer would on a client link.
 */
#ifndef IWX_AWDL_CTX_H
#define IWX_AWDL_CTX_H
#include "iwx_awdl_probe.h"

#define IWX_AWDL_MAC_ID 1
#define IWX_AWDL_LINK_ID 1
#define IWX_AWDL_STA_ID 3
#define IWX_AWDL_PEER_STA_FIRST 4

static inline void iwx_awdl_fill_mac(struct iwx_mac_config_cmd *cmd, uint32_t action, const uint8_t *addr, bool wide, bool assoc) {
    memset(cmd, 0, sizeof(*cmd));
    cmd->id_and_color = htole32(IWX_AWDL_MAC_ID);
    cmd->action = htole32(action);
    if (action == IWX_FW_CTXT_ACTION_REMOVE) return;
    cmd->mac_type = htole32(IWX_FW_MAC_TYPE_P2P_STA);
    memcpy(cmd->local_mld_addr, addr, 6);
    cmd->filter_flags = htole32(IWX_MAC_CFG_FILTER_ACCEPT_GRP |
                                (wide ? IWX_MAC_CFG_FILTER_ACCEPT_CONTROL_AND_MGMT : 0));
    if (assoc) {
        cmd->client.is_assoc = 1;
        cmd->client.assoc_id = htole16(1);
    }
}

static inline void iwx_awdl_fill_link(struct iwx_link_config_cmd *cmd, uint32_t action, uint32_t phy_id,
                                      const uint8_t *addr, uint32_t modify_mask, uint32_t active) {
    memset(cmd, 0, sizeof(*cmd));
    cmd->action = htole32(action);
    cmd->link_id = htole32(IWX_AWDL_LINK_ID);
    cmd->mac_id = htole32(IWX_AWDL_MAC_ID);
    cmd->phy_id = htole32(phy_id);
    if (action == IWX_FW_CTXT_ACTION_REMOVE) return;
    memcpy(cmd->local_link_addr, addr, 6);
    cmd->modify_mask = htole32(modify_mask);
    cmd->active = htole32(active);
}

static inline void iwx_awdl_fill_sta(struct iwx_sta_cfg_cmd *cmd, bool assoc) {
    memset(cmd, 0, sizeof(*cmd));
    cmd->sta_id = htole32(IWX_AWDL_STA_ID);
    cmd->link_id = htole32(IWX_AWDL_LINK_ID);
    memcpy(cmd->peer_mld_address, iwx_awdl_bssid, 6);
    memcpy(cmd->peer_link_address, iwx_awdl_bssid, 6);
    cmd->station_type = htole32(IWX_STATION_TYPE_PEER);
    if (assoc) cmd->assoc_id = htole32(1);
}

static inline void iwx_awdl_fill_peer_sta(struct iwx_sta_cfg_cmd *cmd, uint32_t index, const uint8_t *peer) {
    memset(cmd, 0, sizeof(*cmd));
    cmd->sta_id = htole32(IWX_AWDL_PEER_STA_FIRST + index);
    cmd->link_id = htole32(IWX_AWDL_LINK_ID);
    memcpy(cmd->peer_mld_address, peer, 6);
    memcpy(cmd->peer_link_address, peer, 6);
    cmd->station_type = htole32(IWX_STATION_TYPE_PEER);
    cmd->assoc_id = htole32(2 + index);
}

/* STA_DISABLE_TX_CMD (MAC_CONF group, 0xd), as Linux iwl_mvm_sta_disable_tx_cmd. */
struct iwx_awdl_sta_disable_tx_cmd {
    uint32_t sta_id;
    uint32_t disable;
} __packed;

static inline void iwx_awdl_fill_te(struct iwx_session_prot_cmd *cmd, uint32_t action, uint32_t duration_tu) {
    memset(cmd, 0, sizeof(*cmd));
    cmd->id_and_color = htole32(IWX_AWDL_LINK_ID);
    cmd->action = htole32(action);
    cmd->conf_id = htole32(IWX_SESSION_PROTECT_CONF_ASSOC);
    cmd->duration_tu = htole32(duration_tu);
}
#endif
