#!/usr/bin/env python3
"""Offline checks for the default-off AWDL firmware context (1.1.18). No hardware commands."""
from pathlib import Path
import re, subprocess, tempfile
ROOT = Path(__file__).resolve().parent.parent
reg = (ROOT/'itlwm/hal_iwx/if_iwxreg.h').read_text()
def block(name):
    start = reg.index('struct '+name+' {'); q = reg.index('{', start)+1; depth = 1
    while depth:
        depth += (reg[q] == '{')-(reg[q] == '}'); q += 1
    return reg[start:q]+' __packed;'
macros = ['IWX_FW_CTXT_ACTION_ADD','IWX_FW_CTXT_ACTION_MODIFY','IWX_FW_CTXT_ACTION_REMOVE','IWX_FW_MAC_TYPE_P2P_STA','IWX_MAC_CFG_FILTER_ACCEPT_GRP','IWX_MAC_CFG_FILTER_ACCEPT_CONTROL_AND_MGMT','IWX_MAC_CFG_FILTER_PROMISC','IWX_STATION_TYPE_PEER','IWX_LINK_CONTEXT_MODIFY_ACTIVE','IWX_AC_NUM','IWX_SESSION_PROTECT_CONF_ASSOC']
defs = '\n'.join(re.search(r'^#define\s+'+n+r'\s+[^\n]+', reg, re.M)[0] for n in macros)
structs = ['iwx_mac_client_data','iwx_mac_p2p_dev_data','iwx_mac_config_cmd','iwx_session_prot_cmd','iwx_ac_qos','iwx_he_backoff_conf','iwx_link_config_cmd','iwx_sta_cfg_cmd']
src = '''#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define __packed __attribute__((packed))
#define ETHER_ADDR_LEN 6
#define htole32(x) static_cast<uint32_t>(x)
#define htole16(x) static_cast<uint16_t>(x)
#define IWX_FW_CTXT_INVALID 0xffffffffu
'''+defs+'\n'+'\n'.join(block(n) for n in structs)+r'''
#include "iwx_awdl_ctx.h"
static_assert(sizeof(iwx_link_config_cmd)==208,"link");static_assert(sizeof(iwx_mac_config_cmd)==52,"mac");static_assert(sizeof(iwx_sta_cfg_cmd)==96,"sta");
int main(){
 const uint8_t A[6]={2,5,5,5,5,5};
 iwx_mac_config_cmd m;iwx_awdl_fill_mac(&m,IWX_FW_CTXT_ACTION_ADD,A,false,false);
 assert(m.id_and_color==1&&m.id_and_color!=0&&m.mac_type==7&&!memcmp(m.local_mld_addr,A,6));
 assert(m.filter_flags==IWX_MAC_CFG_FILTER_ACCEPT_GRP&&!(m.filter_flags&(IWX_MAC_CFG_FILTER_ACCEPT_CONTROL_AND_MGMT|IWX_MAC_CFG_FILTER_PROMISC)));
 {iwx_mac_config_cmd h;iwx_awdl_fill_mac(&h,IWX_FW_CTXT_ACTION_MODIFY,A,true,true);assert(h.mac_type==htole32(IWX_FW_MAC_TYPE_P2P_STA)&&h.filter_flags==htole32(IWX_MAC_CFG_FILTER_ACCEPT_GRP|IWX_MAC_CFG_FILTER_ACCEPT_CONTROL_AND_MGMT)&&h.client.is_assoc==1);}
 {const uint8_t P[6]={2,7,7,7,7,7};iwx_sta_cfg_cmd c;iwx_awdl_fill_peer_sta(&c,2,P);assert(c.sta_id==6&&c.link_id==1&&!memcmp(c.peer_mld_address,P,6)&&!memcmp(c.peer_link_address,P,6)&&c.station_type==IWX_STATION_TYPE_PEER&&c.assoc_id==4);assert(IWX_AWDL_PEER_STA_FIRST+IWX_AWDL_PEER_STA_MAX<=16);}
 iwx_mac_config_cmd w;iwx_awdl_fill_mac(&w,IWX_FW_CTXT_ACTION_ADD,A,true,false);assert(w.mac_type==htole32(IWX_FW_MAC_TYPE_P2P_STA));assert(!w.client.is_assoc);iwx_mac_config_cmd as;iwx_awdl_fill_mac(&as,IWX_FW_CTXT_ACTION_MODIFY,A,true,true);assert(as.client.is_assoc==1&&as.client.assoc_id==1&&as.action==IWX_FW_CTXT_ACTION_MODIFY);assert(w.filter_flags==(IWX_MAC_CFG_FILTER_ACCEPT_GRP|IWX_MAC_CFG_FILTER_ACCEPT_CONTROL_AND_MGMT)&&!(w.filter_flags&IWX_MAC_CFG_FILTER_PROMISC));
 iwx_awdl_fill_mac(&m,IWX_FW_CTXT_ACTION_REMOVE,nullptr,false,false);assert(m.id_and_color==1&&m.action==IWX_FW_CTXT_ACTION_REMOVE&&!m.mac_type&&!m.filter_flags);
 iwx_link_config_cmd l;iwx_awdl_fill_link(&l,IWX_FW_CTXT_ACTION_ADD,IWX_FW_CTXT_INVALID,A,0,0);
 assert(l.link_id==1&&l.mac_id==1&&l.phy_id==IWX_FW_CTXT_INVALID&&!memcmp(l.local_link_addr,A,6)&&l.ibss_bssid_addr[0]==0&&!l.active);
 iwx_awdl_fill_link(&l,IWX_FW_CTXT_ACTION_MODIFY,0,A,IWX_LINK_CONTEXT_MODIFY_ACTIVE,1);assert(l.phy_id==0&&l.active==1&&l.modify_mask==IWX_LINK_CONTEXT_MODIFY_ACTIVE);
 iwx_awdl_fill_link(&l,IWX_FW_CTXT_ACTION_REMOVE,IWX_FW_CTXT_INVALID,nullptr,0,0);assert(l.link_id==1&&l.phy_id==IWX_FW_CTXT_INVALID);
 iwx_session_prot_cmd te;iwx_awdl_fill_te(&te,IWX_FW_CTXT_ACTION_ADD,100);assert(te.id_and_color==1&&te.action==IWX_FW_CTXT_ACTION_ADD&&te.conf_id==0&&te.duration_tu==100);iwx_awdl_fill_te(&te,IWX_FW_CTXT_ACTION_REMOVE,0);assert(te.action==IWX_FW_CTXT_ACTION_REMOVE&&!te.duration_tu);
 iwx_sta_cfg_cmd s;iwx_awdl_fill_sta(&s,true);assert(s.assoc_id==1);iwx_awdl_fill_sta(&s,false);assert(s.sta_id==3&&s.link_id==1&&s.station_type==0&&!s.mfp&&!s.assoc_id&&!memcmp(s.peer_mld_address,iwx_awdl_bssid,6)&&!memcmp(s.peer_link_address,iwx_awdl_bssid,6));
 puts("PASS: unassociated P2P client MAC id 1 with group filter only; link 1; peer station 3 at the AWDL BSSID");
}
'''
with tempfile.TemporaryDirectory() as d:
    c = Path(d)/'t.cpp'; c.write_text(src)
    subprocess.run(['clang++','-std=c++17','-w','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(ROOT/'itlwm/hal_iwx'),str(c),'-o',d+'/t'],check=True)
    subprocess.run([d+'/t'],check=True)
s = (ROOT/'itlwm/hal_iwx/ItlIwx.cpp').read_text()
def fn(name, end):
    i = s.index(name); return s[i:s.index(end, i)]
assert 'sc_awdl_probe.ctx.mode && le32toh(mbn->mac_id) == IWX_AWDL_MAC_ID' in s
assert 'awdlCtx >= 2 && awdlCtx <= 6' in s
a0=s[s.index('iwx_awdl_ctx_add(struct iwx_softc *sc, struct iwx_node *in)\n{'):]; assert a0.index('c->mode == 6') < a0.index('IWX_AWDL_CTX_STA') and a0.index('IWX_AWDL_CTX_ACTIVE') < a0.index('c->mode == 6')
assert 'ctx.mode != 6' in s and 'apQueue ? sc->first_data_qid : p->ctx.qid' in s and 'awdlCtx == 1' not in s
assert 'ACTION_ADD, p->tx.self, c->mode >= 3, false)' in s and 'IWX_MAC_CFG_FILTER_PROMISC' not in (ROOT/'itlwm/hal_iwx/iwx_awdl_ctx.h').read_text()
# Peer stations: added only at the final stage, counted before the command, removed before anything else.
rm = s[s.index('iwx_awdl_ctx_remove(struct iwx_softc *sc)\n{'):s.index('iwx_awdl_peer_task(void *arg)\n{')]
assert rm.index('p->peer_added = p->peer_count = 0') < rm.index('IWX_AWDL_PEER_STA_FIRST + i') < rm.index('stage >= IWX_AWDL_CTX_ASSOC')
task = s[s.index('iwx_awdl_peer_task(void *arg)\n{'):s.index('iwx_awdl_tx_maybe(struct iwx_softc *sc)\n{')]
assert 'p->ctx.stage != IWX_AWDL_CTX_ASSOC' in task and task.index('p->peer_added++') < task.index('iwx_send_cmd_pdu') and 'p->peer_failed = 1' in task
assert 'iwx_del_task(sc, systq, &sc->awdl_peer_task)' in s and 'task_set(&sc->awdl_peer_task' in s and 'peer_added = sc->sc_awdl_probe.peer_count = 0' in s
assert 'IWX_FW_MAC_TYPE_IBSS' not in (ROOT/'itlwm/hal_iwx/iwx_awdl_ctx.h').read_text()
# Native mode: station, then association, no queue, in that order; undone in reverse with no queue teardown.
add = s[s.index('iwx_awdl_ctx_add(struct iwx_softc'):s.index('iwx_awdl_ctx_remove(struct iwx_softc *sc)\n{')]
assert add.index('c->mode == 6 && !p->assoc_rx') < add.index('iwx_awdl_fill_sta(&cmd, c->mode == 4 || c->mode == 6)') < add.index('if (c->mode != 6) {') < add.index('iwx_tvqm_enable_txq') < add.index('IWX_AWDL_CTX_ASSOC')
assert 'stage >= IWX_AWDL_CTX_QUEUE && c->mode != 6' in s
assert 'probe->ctx.stage >= IWX_AWDL_CTX_ACTIVE' in s and 'p->ctx.stage < IWX_AWDL_CTX_ACTIVE || p->tx.tripped' in s
t0=s[s.index('iwx_awdl_tx_maybe(struct iwx_softc *sc)\n{'):]; assert t0.index('p->ctx.mode == 5 && p->rx_host_us') < t0.index('.queued >= IWX_AWDL_TX_MAX_QUEUED') and 'IWX_CMD_ASYNC, sizeof(te), &te)' in t0
n0=s[s.index('IWX_MAC_CONF_GROUP, IWX_SESSION_PROTECTION_NOTIF'):]; assert n0.index('le32toh(notif->mac_id) == IWX_AWDL_LINK_ID') < n0.index('++sc->sc_sess_prot_notif')
assert '.queued >= IWX_AWDL_TX_MAX_QUEUED' in s and 'ItlwmAwdlTxStalls' in s
w = s[s.index('AWDL frames the firmware holds must not restart'):]; assert w.index('others') < w.index('device timeout') and 'sc->sc_tx_timer = 0;' in w[:w.index('device timeout')]
mac = fn('iwx_mld_mac_config_cmd(struct iwx_softc *sc, struct iwx_node *in,', 'iwx_mld_link_config_cmd(struct iwx_softc *sc')
assert 'sc->sc_awdl_probe.mode == 1 || sc->sc_awdl_probe.mode == 2' in mac and 'IWX_AWDL' not in mac
add = fn('iwx_awdl_ctx_add(struct iwx_softc *sc, struct iwx_node *in)\n{', 'iwx_awdl_ctx_remove(struct iwx_softc *sc)\n{')
order = ['IWX_AWDL_CTX_MAC','IWX_AWDL_CTX_LINK','IWX_AWDL_CTX_ACTIVE','IWX_AWDL_CTX_STA','IWX_AWDL_CTX_QUEUE','IWX_AWDL_CTX_ASSOC']
pos = [add.index(x) for x in order]; assert pos == sorted(pos)
assert 'IWX_FW_CTXT_ACTION_MODIFY, 0, 0)' in add and 'IWX_LINK_CONTEXT_MODIFY_ACTIVE | IWX_LINK_CONTEXT_MODIFY_RATES_INFO, 1)' in add
assert add.index('IWX_FW_CTXT_ACTION_MODIFY, 0, 0)') < add.index('IWX_LINK_CONTEXT_MODIFY_ACTIVE | IWX_LINK_CONTEXT_MODIFY_RATES_INFO, 1)')
lk = fn('iwx_awdl_ctx_link_cmd(struct iwx_softc *sc, struct iwx_node *in, uint32_t action,', 'iwx_awdl_ctx_add(struct iwx_softc *sc')
assert 'if (has_phy) {' in lk and 'modify_mask &' not in lk and 'cmd.bi =' in lk and 'cmd.ofdm_rates' in lk
assert 'p->tx.tripped = 1' in add and 'c->stage = stage - 1' in add and 'c->stage != stage' in add
rm = fn('iwx_awdl_ctx_remove(struct iwx_softc *sc)\n{', 'iwx_awdl_tx_maybe(struct iwx_softc *sc)\n{')
pos = [rm.index(x) for x in ['iwx_flush_sta_tids','iwx_mld_disable_txq']] + [rm.rindex('IWX_STA_REMOVE_CMD')] + [rm.index(x) for x in ['IWX_LINK_CONTEXT_MODIFY_ACTIVE, 0','IWX_FW_CTXT_ACTION_REMOVE, 0, 0','IWX_FW_CTXT_ACTION_REMOVE, nullptr']]
assert pos == sorted(pos) and rm.index('c->stage = IWX_AWDL_CTX_NONE') < pos[0]
for f, marker in [('iwx_mld_run_stop(struct iwx_softc *sc, struct iwx_node *in)\n{','iwx_flush_sta_tids(sc, IWX_STATION_ID'),('iwx_mld_deauth(struct iwx_softc *sc, struct iwx_node *in)\n{','iwx_cancel_session_protection')]:
    b = s[s.index(f):]; assert b.index('iwx_awdl_ctx_remove(sc)') < b.index(marker), f
tx = fn('iwx_tx(struct iwx_softc *sc, mbuf_t m, struct ieee80211_node *ni, int ac)\n{', 'iwx_flush_sta_tids(struct iwx_softc *sc, int sta_id')
assert tx.index('qid = sc->sc_awdl_probe.ctx.qid') < tx.index('ring = &sc->txq[qid]')
task = fn('iwx_mld_authorized_task(void *arg)', 'iwx_awdl_probe_publish(struct iwx_softc *sc)')
assert task.index('sc_mld_authorized_done_epoch = epoch') < task.index('iwx_awdl_ctx_add(sc, in)')
assert 'sc->sc_awdl_probe.ctx.stage = IWX_AWDL_CTX_NONE' in fn('iwx_stop(struct _ifnet *ifp)\n{', 'iwx_watchdog') if 'iwx_watchdog' in s else True
print('PASS: station filter untouched with a context; add after authorization, unwound in reverse before AP teardown; frames never fall back to the AP queue; any failure latches off')
