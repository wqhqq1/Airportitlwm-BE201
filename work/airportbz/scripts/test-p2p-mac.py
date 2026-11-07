"""Offline API92 P2P wire-ABI checks. No commands are sent to hardware."""
from pathlib import Path
import re,subprocess,struct,json,hashlib
root=Path(__file__).resolve().parents[1];out=root/'build/p2p-mac-test';out.mkdir(parents=True,exist_ok=True)
reg=(root/'itlwm/hal_iwx/if_iwxreg.h').read_text()
def block(name):
 start=reg.index('struct '+name+' {');p=reg.index('{',start);q=p+1;depth=1
 while depth:
  depth+=(reg[q]=='{')-(reg[q]=='}');q+=1
 return reg[start:q]+' __packed;'
names=['iwx_mac_client_data','iwx_mac_p2p_dev_data','iwx_mac_config_cmd']
macros=['IWX_MLD_MAC_ID','IWX_MAC_INDEX_AUX','IWX_NUM_MAC_INDEX_DRIVER','IWX_FW_CTXT_ACTION_ADD','IWX_FW_CTXT_ACTION_MODIFY','IWX_FW_CTXT_ACTION_REMOVE','IWX_FW_MAC_TYPE_P2P_DEVICE','IWX_MAC_CFG_FILTER_ACCEPT_CONTROL_AND_MGMT']
defines='\n'.join(re.search(r'^#define\s+'+n+r'\s+[^\n]+',reg,re.M)[0] for n in macros)
golden=struct.pack('<III6sHIHHII16s',1,1,6,bytes.fromhex('021122334455'),0,2,0,0,0,1,bytes(16))
assert len(golden)==52
src='''#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cassert>
#include <cstdio>
#define __packed __attribute__((packed))
#define ETHER_ADDR_LEN 6
#define htole32(x) static_cast<uint32_t>(x)
'''+defines+'\n'+'\n'.join(block(n) for n in names)+'\n#include "iwx_p2p_mac.h"\n'+r'''
static_assert(sizeof(iwx_mac_config_cmd)==52,"MAC v2 length");
static_assert(offsetof(iwx_mac_config_cmd,client)==36,"station union offset");
static_assert(offsetof(iwx_mac_config_cmd,p2p_dev)==36,"P2P union offset");
static_assert(offsetof(iwx_mac_config_cmd,filter_flags)==20,"filter offset");
static_assert(offsetof(iwx_mac_config_cmd,nic_not_ack_enabled)==32,"ACK flag offset");
struct LegacyMac {
 uint32_t id_and_color,action,mac_type;uint8_t local_mld_addr[6];uint16_t reserved;
 uint32_t filter_flags;uint16_t he_support,he_ap_support;uint32_t eht_support,nic_not_ack_enabled;
 iwx_mac_client_data client;
} __packed;
int main(){
 const uint8_t address[]={2,0x11,0x22,0x33,0x44,0x55};
 const uint8_t expected[]={'''+','.join(str(x) for x in golden)+r'''};
 iwx_mac_config_cmd cmd;
 assert(iwx_prepare_p2p_mac_config(&cmd,2,1,1,address,6,false)==IWX_P2P_MAC_PREPARED);
 assert(!memcmp(&cmd,expected,sizeof cmd));
 assert(iwx_prepare_p2p_mac_config(&cmd,2,2,3,address,6,true)==IWX_P2P_MAC_PREPARED);
 assert(cmd.id_and_color==3 && cmd.action==2 && cmd.nic_not_ack_enabled==0 && cmd.p2p_dev.is_disc_extended==0);
 assert(iwx_prepare_p2p_mac_config(&cmd,2,3,1,nullptr,0,false)==IWX_P2P_MAC_PREPARED);
 for(size_t i=8;i<sizeof cmd;++i)assert(((uint8_t*)&cmd)[i]==0);
 uint8_t bad[6]={};
 for(unsigned version:{0u,1u,2u,3u,99u})for(uint32_t id:{0u,1u,2u,3u,4u,255u,0xffffffffu}){
  memset(&cmd,0xa5,sizeof cmd);iwx_mac_config_cmd before=cmd;
  auto r=iwx_prepare_p2p_mac_config(&cmd,version,1,id,address,6,true);
  bool valid=version==2 && id>0 && id<4;
  assert((r==IWX_P2P_MAC_PREPARED)==valid);
  if(!valid)assert(!memcmp(&cmd,&before,sizeof cmd));
 }
 for(unsigned action:{0u,4u,99u}){
  memset(&cmd,0xa5,sizeof cmd);auto before=cmd;
  assert(iwx_prepare_p2p_mac_config(&cmd,2,action,1,address,6,true)==IWX_P2P_MAC_BAD_ACTION);
  assert(!memcmp(&cmd,&before,sizeof cmd));
 }
 for(size_t length:{size_t(0),size_t(5),size_t(7),size_t(-1)}){
  memset(&cmd,0xa5,sizeof cmd);auto before=cmd;
  assert(iwx_prepare_p2p_mac_config(&cmd,2,1,1,address,length,true)==IWX_P2P_MAC_BAD_ADDRESS);
  assert(!memcmp(&cmd,&before,sizeof cmd));
 }
 assert(iwx_prepare_p2p_mac_config(&cmd,2,1,1,nullptr,6,true)==IWX_P2P_MAC_BAD_ADDRESS);
 assert(iwx_prepare_p2p_mac_config(nullptr,2,1,1,address,6,true)==IWX_P2P_MAC_BAD_BUFFER);
 assert(iwx_prepare_p2p_mac_config(&cmd,2,1,1,bad,6,true)==IWX_P2P_MAC_BAD_ADDRESS);
 bad[0]=1;assert(iwx_prepare_p2p_mac_config(&cmd,2,1,1,bad,6,true)==IWX_P2P_MAC_BAD_ADDRESS);
 LegacyMac old={};old.mac_type=3;old.filter_flags=4;old.he_support=1;old.client.is_assoc=1;old.client.assoc_id=0x123;
 cmd={};cmd.mac_type=3;cmd.filter_flags=4;cmd.he_support=1;cmd.client.is_assoc=1;cmd.client.assoc_id=0x123;
 assert(sizeof old==sizeof cmd && !memcmp(&old,&cmd,sizeof cmd));
 puts("PASS: API92 MAC v2 52-byte golden packet; reserved IDs, unknown API/action, malformed addresses rejected; remove zeroes payload; station ABI unchanged.");
}
'''
src=src.replace('#include <cstdio>','#include <cstdio>\n#include <initializer_list>')
p=out/'p2p.cpp';p.write_text(src)
subprocess.run(['clang++','-std=c++14','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(root/'itlwm/hal_iwx'),str(p),'-o',str(out/'p2p-test')],check=True)
r=subprocess.run([str(out/'p2p-test')],check=True,capture_output=True,text=True);print(r.stdout,end='')
(out/'validation.json').write_text(json.dumps({'api':2,'command_length':52,'p2p_union_offset':36,'sanitizers':['ASan','UBSan'],'station_wire_abi_unchanged':True,'hardware_commands_sent':0,'runtime_path_enabled':False},indent=2)+'\n')
