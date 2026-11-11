int ItlIwx::
iwx_mld_sta_config_cmd(struct iwx_softc *sc, struct iwx_node *in, int assoc)
{
    struct ieee80211_node *ni = &in->in_ni;
    struct iwx_sta_cfg_cmd cmd;
    uint32_t agg_size = 0, mpdu_dens = 0;

    /*
     * Station entry for the AP, following Linux iwl_mvm_mld_cfg_sta().
     * Before association only the addresses and MFP are set; the run path
     * adds the association ID, MIMO and A-MPDU parameters.
     */
    memset(&cmd, 0, sizeof(cmd));
    cmd.sta_id = htole32(IWX_STATION_ID);
    cmd.link_id = htole32(IWX_MLD_LINK_ID);
    IEEE80211_ADDR_COPY(cmd.peer_mld_address, in->in_macaddr);
    IEEE80211_ADDR_COPY(cmd.peer_link_address, in->in_macaddr);
    cmd.station_type = htole32(IWX_STATION_TYPE_PEER);
    /*
     * Linux sets mfp while the station is not yet authorized when the
     * firmware has STA_EXP_MFP_SUPPORT, which covers every STA_CONFIG it
     * sends in client mode; otherwise only for MFP associations.
     */
    if (isset(sc->sc_enabled_capa, IWX_UCODE_TLV_CAPA_STA_EXP_MFP_SUPPORT) ||
        (ni->ni_flags & IEEE80211_NODE_MFP))
        cmd.mfp = htole32(1);

    if (assoc) {
        cmd.assoc_id = htole32(ni->ni_associd & 0x3fff);
        if ((ni->ni_flags & (IEEE80211_NODE_HT | IEEE80211_NODE_VHT |
            IEEE80211_NODE_HE)) && iwx_mimo_enabled(sc) && ni->ni_rx_nss > 1)
            cmd.mimo = htole32(1);
        if (ni->ni_flags & IEEE80211_NODE_HT) {
            agg_size = ni->ni_ampdu_param & IEEE80211_AMPDU_PARAM_LE;
            mpdu_dens = (ni->ni_ampdu_param & IEEE80211_AMPDU_PARAM_SS) >> 2;
        }
        if (ni->ni_flags & IEEE80211_NODE_VHT)
            agg_size = (ni->ni_vhtcaps &
                IEEE80211_VHTCAP_MAX_A_MPDU_LENGTH_EXPONENT_MASK) >>
                IEEE80211_VHTCAP_MAX_A_MPDU_LENGTH_EXPONENT_SHIFT;
        if (agg_size > (IWX_STA_FLG_MAX_AGG_SIZE_4M >>
            IWX_STA_FLG_MAX_AGG_SIZE_SHIFT))
            agg_size = IWX_STA_FLG_MAX_AGG_SIZE_4M >>
                IWX_STA_FLG_MAX_AGG_SIZE_SHIFT;
        cmd.tx_ampdu_spacing = htole32(mpdu_dens);
        cmd.tx_ampdu_max_size = htole32(agg_size);
        if (ni->ni_flags & IEEE80211_NODE_QOS)
            cmd.sp_length = htole32(128);
        iwx_mld_fill_he_sta(ni, &cmd);
    }

    return iwx_send_cmd_pdu(sc, iwx_cmd_id(IWX_STA_CONFIG_CMD,
        IWX_MAC_CONF_GROUP, 0), 0, sizeof(cmd), &cmd);
}
