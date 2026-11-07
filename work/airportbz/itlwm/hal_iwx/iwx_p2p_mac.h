/* SPDX-License-Identifier: ISC
 * BE201 API92 P2P MAC command preparation.
 * Wire ABI: Linux v6.12 drivers/net/wireless/intel/iwlwifi/fw/api/mac-cfg.h
 * and mvm/mld-mac.c. Include after if_iwxreg.h and endian definitions.
 *
 * This builder does not send a command, reserve a MAC ID, bind a PHY, or
 * advertise AWDL support. The caller must own a separate MAC context before
 * issuing the result on the driver's serialized firmware-command path.
 */
#ifndef IWX_P2P_MAC_H
#define IWX_P2P_MAC_H

enum iwx_p2p_mac_prepare_result {
    IWX_P2P_MAC_PREPARED = 0,
    IWX_P2P_MAC_BAD_BUFFER,
    IWX_P2P_MAC_UNSUPPORTED_VERSION,
    IWX_P2P_MAC_BAD_ACTION,
    IWX_P2P_MAC_RESERVED_ID,
    IWX_P2P_MAC_BAD_ADDRESS
};

static inline enum iwx_p2p_mac_prepare_result
iwx_prepare_p2p_mac_config(struct iwx_mac_config_cmd *output,
    unsigned command_version, uint32_t action, uint32_t mac_id,
    const uint8_t *address, size_t address_length, bool nic_ack_enabled)
{
    if (output == NULL)
        return IWX_P2P_MAC_BAD_BUFFER;
    if (command_version != 2)
        return IWX_P2P_MAC_UNSUPPORTED_VERSION;
    if (action != IWX_FW_CTXT_ACTION_ADD &&
        action != IWX_FW_CTXT_ACTION_MODIFY &&
        action != IWX_FW_CTXT_ACTION_REMOVE)
        return IWX_P2P_MAC_BAD_ACTION;
    /* Keep both the existing infrastructure MAC and the AUX MAC untouched. */
    if (mac_id == IWX_MLD_MAC_ID || mac_id >= IWX_NUM_MAC_INDEX_DRIVER)
        return IWX_P2P_MAC_RESERVED_ID;
    if (action != IWX_FW_CTXT_ACTION_REMOVE) {
        if (address == NULL || address_length != ETHER_ADDR_LEN ||
            (address[0] & 1) != 0)
            return IWX_P2P_MAC_BAD_ADDRESS;
        uint8_t nonzero = 0;
        for (unsigned i = 0; i < ETHER_ADDR_LEN; ++i)
            nonzero |= address[i];
        if (nonzero == 0)
            return IWX_P2P_MAC_BAD_ADDRESS;
    }

    /* Do not modify the caller's buffer when validation fails. */
    struct iwx_mac_config_cmd command = {};
    command.id_and_color = htole32(mac_id);
    command.action = htole32(action);
    if (action != IWX_FW_CTXT_ACTION_REMOVE) {
        command.mac_type = htole32(IWX_FW_MAC_TYPE_P2P_DEVICE);
        for (unsigned i = 0; i < ETHER_ADDR_LEN; ++i)
            command.local_mld_addr[i] = address[i];
        command.filter_flags =
            htole32(IWX_MAC_CFG_FILTER_ACCEPT_CONTROL_AND_MGMT);
        command.nic_not_ack_enabled = htole32(nic_ack_enabled ? 0 : 1);
        /* No active Wi-Fi Direct GO: never extend discovery to all MACs. */
        command.p2p_dev.is_disc_extended = 0;
    }
    *output = command;
    return IWX_P2P_MAC_PREPARED;
}
#endif
