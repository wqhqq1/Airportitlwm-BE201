// AirportBZ source 10f8e1482c468f66ff78ca0efa8c1755ee7ac5fa; unchanged production function.
uint16_t ItlIwx::
iwx_rs_fw_get_config_flags(struct iwx_softc *sc)
{
    struct ieee80211com *ic = &sc->sc_ic;
    struct ieee80211_node *ni = ic->ic_bss;
    uint16_t flags = 0;
    
    if (ic->ic_state < IEEE80211_S_ASSOC) {
        return flags;
    }
    
    if (iwx_num_of_ant(iwx_fw_valid_tx_ant(sc)) > 1) {
        if (ni->ni_flags & IEEE80211_NODE_HE) {
            if (ni->ni_he_cap_elem.phy_cap_info[2] & IEEE80211_HE_PHY_CAP2_STBC_RX_UNDER_80MHZ)
                flags |= IWX_TLC_MNG_CFG_FLAGS_STBC_MSK;
        } else if (ni->ni_vhtcaps & IEEE80211_VHTCAP_RXSTBC_MASK)
            flags |= IWX_TLC_MNG_CFG_FLAGS_STBC_MSK;
        else if (ni->ni_htcaps & IEEE80211_HTCAP_RXSTBC_MASK)
            flags |= IWX_TLC_MNG_CFG_FLAGS_STBC_MSK;
    }
    
    if (((ni->ni_htcaps & IEEE80211_HTCAP_LDPC) ||
         ((ic->ic_flags & IEEE80211_F_VHTON) && (ni->ni_vhtcaps & IEEE80211_VHTCAP_RXLDPC))))
        flags |= IWX_TLC_MNG_CFG_FLAGS_LDPC_MSK;
    
    /* consider LDPC support in case of HE */
    if ((ni->ni_flags & IEEE80211_NODE_HE) &&
        (ni->ni_he_cap_elem.phy_cap_info[1] &
        IEEE80211_HE_PHY_CAP1_LDPC_CODING_IN_PAYLOAD))
        flags |= IWX_TLC_MNG_CFG_FLAGS_LDPC_MSK;
    
    if ((ni->ni_flags & IEEE80211_NODE_HE) &&
        !(ni->ni_he_cap_elem.phy_cap_info[1] &
         IEEE80211_HE_PHY_CAP1_LDPC_CODING_IN_PAYLOAD))
        flags &= ~IWX_TLC_MNG_CFG_FLAGS_LDPC_MSK;

    if ((ni->ni_flags & IEEE80211_NODE_HE) &&
        (ic->ic_he_cap_elem.phy_cap_info[3] & IEEE80211_HE_PHY_CAP3_DCM_MAX_CONST_TX_MASK) &&
        (ni->ni_he_cap_elem.phy_cap_info[3] &
         IEEE80211_HE_PHY_CAP3_DCM_MAX_CONST_RX_MASK))
        flags |= IWX_TLC_MNG_CFG_FLAGS_HE_DCM_NSS_1_MSK;
    
    return flags;
}
