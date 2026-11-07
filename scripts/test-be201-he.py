"""Exercise production HE builders and API selection, without loading a kext.

Command bytes/offsets are checked against Linux v6.12's documented API92 ABI.
The real packaged firmware supplies the command-version table for the gate test.
"""
from pathlib import Path
import re, struct, subprocess, tempfile, hashlib, json

root = Path(__file__).resolve().parents[1]
source = (root/'itlwm/hal_iwx/ItlIwx.cpp').read_text()
reg = (root/'itlwm/hal_iwx/if_iwxreg.h').read_text()
headers = '\n'.join(p.read_text() for p in (root/'itl80211/openbsd/net80211').glob('*.h')) + '\n' + reg
headers += '\n' + (root/'itlwm/hal_iwx/if_iwxvar.h').read_text()

def block(text, signature, terminate=''):
    start = text.index(signature)
    brace = text.index('{', start)
    end, depth = brace + 1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + terminate

functions = '\n'.join(block(source, name) for name in [
    'static uint8_t iwx_mvm_mac80211_ac_to_ucode_ac(enum ieee80211_edca_ac ac)\n{',
    'static uint8_t\niwx_he_ppe_value(',
    'static void\niwx_build_he_sta(',
    'static void\niwx_mld_fill_he_sta(',
    'static void\niwx_mld_fill_he_link(',
    'void ItlIwx::\niwx_setup_he_rates(',
    'static uint32_t\niwx_he_rate_kbps('])
declarations = '\n'.join(block(headers, 'struct '+name+' {', ' __packed;') for name in [
    'ieee80211_he_cap_elem', 'ieee80211_he_mcs_nss_supp',
    'iwx_he_backoff_conf', 'iwx_he_sta_context_cmd', 'iwx_ac_qos',
    'iwx_link_config_cmd', 'iwx_sta_cfg_cmd'])
declarations += '\n' + block(headers, 'enum ieee80211_edca_ac {', ';')
node_source = (root/'itl80211/openbsd/net80211/ieee80211_node.c').read_text()
parsers = '\n'.join(block(headers, signature) for signature in [
    'static inline uint8_t\nieee80211_he_mcs_nss_size(',
    'static inline uint8_t\nieee80211_he_ppe_size(',
    'static inline uint8_t\nieee80211_he_oper_size('])
parsers += '\n' + '\n'.join(block(node_source, signature) for signature in [
    'int\nieee80211_setup_hecaps(', 'int\nieee80211_setup_heop('])
declarations += '\n' + '\n'.join(block(headers, 'struct '+name+' {', ' __packed;') for name in [
    'ieee80211_he_operation', 'ieee80211_he_6ghz_oper'])
all_defines = dict(re.findall(r'^\s*#define\s+((?:IWX|IEEE80211)_[A-Za-z0-9_]+)\s+([^\n]+)', headers, re.M))
needed = set(re.findall(r'\b(?:IWX|IEEE80211)_[A-Za-z0-9_]+\b', functions + declarations + parsers))
needed |= {'IWX_FW_CTXT_ACTION_REMOVE', 'IWX_RATE_MCS_HE_TYPE_MU'}
selected = {}
while True:
    for key in needed:
        if key in all_defines:
            selected[key] = all_defines[key]
    extra = set(re.findall(r'\b(?:IWX|IEEE80211)_[A-Za-z0-9_]+\b', '\n'.join(selected.values())))
    if extra <= needed:
        break
    needed |= extra
defines = '\n'.join('#define '+k+' '+v for k, v in selected.items())

firmware = root/'build/firmware-be201/iwlwifi-bz-b0-fm-c0-92.ucode'
b = firmware.read_bytes()
assert hashlib.sha256(b).hexdigest() == '820f9fb78e43b424befdc2d9253e2b56f9d2bb250d8a42217d9bb1d8b6d7957d'
versions = []
offset = 88
while offset + 8 <= len(b):
    kind, length = struct.unpack_from('<II', b, offset)
    assert offset + 8 + length <= len(b)
    if kind == 48:
        assert length % 4 == 0
        versions += [struct.unpack_from('BBBB', b, offset+8+i) for i in range(0, length, 4)]
    offset += 8 + ((length+3) & ~3)
assert offset == len(b) and versions
version_code = '\n'.join('sc.versions[{%d,%d}]=%d;' % (g,c,v) for c,g,v,n in versions)

harness = r'''
#include <cstdint>
#include <cstring>
#include <cassert>
#include <cstddef>
#include <cstdio>
#include <map>
#include <string>
#include <vector>
#include <libkern/OSByteOrder.h>
#define htole16 OSSwapHostToLittleInt16
#define htole32 OSSwapHostToLittleInt32
#define le16toh OSSwapLittleToHostInt16
#define le32toh OSSwapLittleToHostInt32
#define __packed __attribute__((packed))
#define BIT(x) (1U << (x))
#define hweight8(x) __builtin_popcount(static_cast<unsigned>(x))
#define DIV_ROUND_UP(x,y) (((x)+(y)-1)/(y))
#define ETHER_ADDR_LEN 6
#define XYLog(...) ((void)0)
''' + defines + '\n' + declarations + r'''
struct ieee80211_node {
 uint32_t ni_flags=0, ni_he_oper_params=0;
 uint16_t ni_he_oper_nss_set=0xffff;
 uint8_t ni_he_optional[9]={};
 ieee80211_he_cap_elem ni_he_cap_elem={};
 ieee80211_he_mcs_nss_supp ni_he_mcs_nss_supp={};
 uint8_t ni_ppe_thres[25]={}, ni_he_mu_edca[13]={};
};
struct ieee80211com {
 uint32_t ic_flags=0,ic_userflags=0,ic_htcaps=0;
 ieee80211_he_cap_elem ic_he_cap_elem={};
 ieee80211_he_mcs_nss_supp ic_he_mcs_nss_supp={};
 uint8_t ic_ppe_thres[25]={};
};
struct Registry {
 std::map<std::string,uint64_t> numbers;
 void setProperty(const char*key,bool v) { numbers[key]=v; }
 void setProperty(const char*key,uint64_t v,unsigned) { numbers[key]=v; }
 void setProperty(const char*,const char*) {}
};
#ifndef IWX_DEVICE_FAMILY_BZ
#define IWX_DEVICE_FAMILY_BZ 999
#endif
struct iwx_softc {
 ieee80211com sc_ic;
 char sc_fwver[32]="92.test.0";
 struct { bool sku_cap_11ax_enable=true,sku_cap_band_52GHz_enable=true,vht160_supported=true; } sc_nvm;
 Registry registry; Registry *sc_pcitag=&registry;
 int sc_device_family=IWX_DEVICE_FAMILY_BZ;
 bool mld=true;
 std::map<std::pair<uint8_t,uint8_t>,uint8_t> versions;
};
struct ItlIwx {
 void iwx_setup_he_rates(iwx_softc*);
 bool iwx_use_mld_api(iwx_softc*s) {return s->mld;}
 uint8_t iwx_lookup_cmd_ver(iwx_softc*s,uint8_t g,uint8_t c) {
  auto i=s->versions.find({g,c});return i==s->versions.end()?99:i->second;
 }
 uint8_t iwx_fw_valid_rx_ant(iwx_softc*) {return 3;}
 uint8_t iwx_fw_valid_tx_ant(iwx_softc*) {return 3;}
 unsigned iwx_num_of_ant(uint8_t a) {return __builtin_popcount(a);}
 bool iwx_mimo_enabled(iwx_softc*) {return true;}
};
''' + parsers + '\n' + functions + r'''
static void putbits(uint8_t*p,unsigned bit,unsigned value) {
 for(unsigned i=0;i<3;i++) {
  p[(bit+i)/8] &= ~(1U<<((bit+i)%8));
  p[(bit+i)/8] |= ((value>>i)&1U)<<((bit+i)%8);
 }
}
static uint32_t word(const void*p,unsigned offset) {
 uint32_t v;memcpy(&v,static_cast<const uint8_t*>(p)+offset,4);return v;
}
int main() {
 // Independently documented Linux API wire offsets; not computed by builders.
 static_assert(sizeof(iwx_link_config_cmd)==208,"LINK v2");
 static_assert(offsetof(iwx_link_config_cmd,trig_based_txf)==104,"MU EDCA offset");
 static_assert(offsetof(iwx_link_config_cmd,frame_time_rts_th)==146,"RTS offset");
 static_assert(offsetof(iwx_link_config_cmd,bss_color)==165,"BSS color offset");
 static_assert(sizeof(iwx_sta_cfg_cmd)==96,"STA v1");
 static_assert(offsetof(iwx_sta_cfg_cmd,pkt_ext)==72,"PPE v2 offset");
 static_assert(offsetof(iwx_sta_cfg_cmd,htc_flags)==92,"HTC offset");
 ieee80211_node n;
 iwx_sta_cfg_cmd sta={}, untouched={};
 iwx_link_config_cmd link={}, original={};
 iwx_mld_fill_he_sta(&n,&sta);iwx_mld_fill_he_link(&n,&link);
 assert(memcmp(&sta,&untouched,sizeof(sta))==0);
 assert(memcmp(&link,&original,sizeof(link))==0);

 n.ni_flags=IEEE80211_NODE_HE | IEEE80211_NODE_HE_MU_EDCA;
 n.ni_he_oper_params=3 | (0x155<<4) | (37U<<24) | IEEE80211_HE_OPERATION_BSS_COLOR_DISABLED;
 n.ni_he_cap_elem.mac_cap_info[0]=IEEE80211_HE_MAC_CAP0_HTC_HE;
 n.ni_he_cap_elem.mac_cap_info[2]=IEEE80211_HE_MAC_CAP2_ACK_EN | IEEE80211_HE_MAC_CAP2_BSR;
 n.ni_he_cap_elem.mac_cap_info[3]=IEEE80211_HE_MAC_CAP3_OMI_CONTROL;
 n.ni_he_cap_elem.mac_cap_info[4]=IEEE80211_HE_MAC_CAP4_BQR;
 n.ni_he_cap_elem.mac_cap_info[5]=IEEE80211_HE_MAC_CAP5_OM_CTRL_UL_MU_DATA_DIS_RX;
 n.ni_he_cap_elem.phy_cap_info[6]=IEEE80211_HE_PHY_CAP6_PPE_THRESHOLD_PRESENT;
 n.ni_ppe_thres[0]=1 | (5<<3); // two NSS, RU sizes 242 and 996
 const unsigned high[]={1,3,2,4},low[]={0,2,1,3};
 for(unsigned i=0;i<4;i++) {putbits(n.ni_ppe_thres,7+6*i,high[i]);putbits(n.ni_ppe_thres,10+6*i,low[i]);}
 for(unsigned ac=0;ac<4;ac++) {
  n.ni_he_mu_edca[1+3*ac]=ac+1;
  n.ni_he_mu_edca[2+3*ac]=0xa0+ac;
  n.ni_he_mu_edca[3+3*ac]=10+ac;
 }
 iwx_mld_fill_he_sta(&n,&sta);
 assert(word(&sta,48)==1 && word(&sta,92)==0x71);
 assert(sta.pkt_ext[0][0][0]==0 && sta.pkt_ext[0][0][1]==1);
 assert(sta.pkt_ext[0][2][0]==2 && sta.pkt_ext[0][2][1]==3);
 assert(sta.pkt_ext[1][0][0]==1 && sta.pkt_ext[1][0][1]==2);
 assert(sta.pkt_ext[1][2][0]==3 && sta.pkt_ext[1][2][1]==4);
 for(unsigned ss=0;ss<2;ss++) for(unsigned bw: {1U,3U,4U})
  assert(sta.pkt_ext[ss][bw][0]==7 && sta.pkt_ext[ss][bw][1]==7);
 // No UORA or MLO configuration was invented.
 assert(sta.trig_rnd_alloc==0 && sta.beamform_flags==0);
 link.action=IWX_FW_CTXT_ACTION_MODIFY;link.active=1;
 link.modify_mask=IWX_LINK_CONTEXT_MODIFY_QOS_PARAMS;
 iwx_mld_fill_he_link(&n,&link);
 assert(word(&link,24)==0x68 && link.htc_trig_based_pkt_ext==3);
 assert(link.frame_time_rts_th==0x155 && reinterpret_cast<uint8_t*>(&link)[165]==37);
 assert(word(&link,148)==3 && word(&link,152)==3 && link.ul_mu_data_disable==1);
 // IEEE ACI BE/BK/VI/VO -> Intel enum iwl_ac BK/BE/VI/VO.
 const unsigned expected_fw_ac[]={1,0,2,3};
 for(unsigned ac=0;ac<4;ac++) {
  auto &v=link.trig_based_txf[expected_fw_ac[ac]];
  assert(v.cwmin==ac && v.cwmax==10 && v.aifsn==ac+1 && v.mu_time==10+ac);
 }
 // Beacon removal of MU EDCA and disabled-color state must clear old flags.
 n.ni_flags &= ~IEEE80211_NODE_HE_MU_EDCA;
 n.ni_he_oper_params &= ~IEEE80211_HE_OPERATION_BSS_COLOR_DISABLED;
 iwx_mld_fill_he_link(&n,&link);assert(link.flags==0 && link.flags_mask==3);
 original=link;link.active=0;original.active=0;
 iwx_mld_fill_he_link(&n,&link);assert(memcmp(&link,&original,sizeof(link))==0);
 link.active=1;link.action=IWX_FW_CTXT_ACTION_REMOVE;original=link;
 iwx_mld_fill_he_link(&n,&link);assert(memcmp(&link,&original,sizeof(link))==0);
 for(unsigned padding=0;padding<4;padding++) {
  n.ni_he_cap_elem.phy_cap_info[6]=0;n.ni_he_cap_elem.phy_cap_info[9]=padding<<6;
  memset(&sta,0,sizeof(sta));iwx_mld_fill_he_sta(&n,&sta);
  for(unsigned ss=0;ss<2;ss++) for(unsigned bw=0;bw<4;bw++) {
   assert(sta.pkt_ext[ss][bw][0]==(padding==1?0:7));
   assert(sta.pkt_ext[ss][bw][1]==(padding==2?0:7));
  }
 }
 // Random PPE capability bytes exercise cross-byte extraction under ASan/UBSan.
 uint32_t random=0x38d2e301;
 for(unsigned i=0;i<100000;i++) {
  for(auto &v:n.ni_ppe_thres) {random=random*1664525+1013904223;v=random>>24;}
  n.ni_he_cap_elem.phy_cap_info[6]=IEEE80211_HE_PHY_CAP6_PPE_THRESHOLD_PRESENT;
  iwx_mld_fill_he_sta(&n,&sta);iwx_mld_fill_he_link(&n,&link);
  for(auto &ss:sta.pkt_ext) for(auto &bw:ss) for(auto v:bw)assert(v<=7);
 }
 ItlIwx driver;iwx_softc sc;
''' + version_code + r'''
 assert(driver.iwx_lookup_cmd_ver(&sc,5,7)==99); // real API92 lacks the old HE command
 driver.iwx_setup_he_rates(&sc);assert(!(sc.sc_ic.ic_flags&IEEE80211_F_HEON));
 sc.sc_ic.ic_userflags=IEEE80211_F_HEON;sc.sc_ic.ic_htcaps=IEEE80211_HTCAP_CBW20_40;
 driver.iwx_setup_he_rates(&sc);assert(sc.sc_ic.ic_flags&IEEE80211_F_HEON);
 assert(sc.sc_ic.ic_he_mcs_nss_supp.rx_mcs_80==0xfffa);
 assert(sc.sc_ic.ic_he_mcs_nss_supp.rx_mcs_160==0xffff);
 assert(!(sc.sc_ic.ic_he_cap_elem.phy_cap_info[0] & IEEE80211_HE_PHY_CAP0_CHANNEL_WIDTH_SET_160MHZ_IN_5G));
 for(auto command: {std::make_pair(3,8),std::make_pair(3,9),std::make_pair(5,15)}) {
  auto saved=sc.versions[command];sc.versions[command]=99;
  driver.iwx_setup_he_rates(&sc);assert(!(sc.sc_ic.ic_flags&IEEE80211_F_HEON));sc.versions[command]=saved;
 }
 sc.versions[{3,10}]=2;driver.iwx_setup_he_rates(&sc);
 assert(!(sc.sc_ic.ic_flags&IEEE80211_F_HEON));sc.versions.erase({3,10});
 strcpy(sc.sc_fwver,"93.test.0");driver.iwx_setup_he_rates(&sc);
 assert(!(sc.sc_ic.ic_flags&IEEE80211_F_HEON));strcpy(sc.sc_fwver,"92.test.0");
 sc.sc_nvm.sku_cap_11ax_enable=false;driver.iwx_setup_he_rates(&sc);
 assert(!(sc.sc_ic.ic_flags&IEEE80211_F_HEON));
 // Real HE SU encoding: 2 NSS, 80MHz, MCS11, 0.8us GI -> 1200.98 Mbps.
 uint32_t rate=IWX_RATE_MCS_HE_MSK | (1U<<IWX_RATE_MCS_NSS_POS) |
  (2U<<IWX_RATE_MCS_CHAN_WIDTH_POS) | 11;
 assert(iwx_he_rate_kbps(rate)==1200980);
 assert(iwx_he_rate_kbps(rate|IWX_RATE_MCS_HE_TYPE_MU)==0);
 // Exercise actual RX IE parsers at exact allocation boundaries.
 // Truncated HE capability/operation IEs may not keep validated flags.
 uint8_t valid_cap[21]={};
 valid_cap[17]=valid_cap[19]=0xfa;valid_cap[18]=valid_cap[20]=0xff;
 for(unsigned len=0;len<21;len++) {
  std::vector<uint8_t> bytes(valid_cap,valid_cap+len);
  assert(!ieee80211_setup_hecaps(&n,bytes.data(),len));
  assert(!(n.ni_flags&IEEE80211_NODE_HECAP));
 }
 assert(ieee80211_setup_hecaps(&n,valid_cap,21));
 for(unsigned trial=0;trial<100000;trial++) {
  random=random*1664525+1013904223;unsigned length=random%256;
  std::vector<uint8_t> bytes(length);
  for(auto &v:bytes){random=random*1664525+1013904223;v=random>>24;}
  ieee80211_setup_hecaps(&n,bytes.data(),length);
  ieee80211_setup_heop(&n,bytes.data(),length);
 }
 puts("PASS: real API92 HE gate; LINK v2/STA v1 wire offsets and golden fields; AC no-op; PPE v2 NSS stride; MU EDCA mapping/removal; 100000 randomized PPE cases; HE PHY-rate decoding; 100000 bounded production HE IE parser cases (ASan/UBSan).");
}
'''
with tempfile.TemporaryDirectory() as directory:
    p=Path(directory);(p/'test.cpp').write_text(harness)
    subprocess.run(['clang++','-std=c++14','-fsanitize=address,undefined','-Wall','-Wextra','-Werror',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
