"""Exercise the production native RX validator with boundaries, guard pages and mutated frames."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
src=r'''
#include "iwx_awdl_rx.h"
#include <cassert>
#include <cstdio>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>
using V=std::vector<uint8_t>;
V good(){V f(40);f[0]=0xd0;f[10]=2;memcpy(f.data()+16,iwx_awdl_bssid,6);
 const uint8_t body[16]={127,0,0x17,0xf2,8,0x10,3};memcpy(f.data()+24,body,16);return f;}
bool valid(const V& f){iwx_awdl_rx_header h;memset(&h,0xaa,sizeof(h));auto old=h;
 bool ok=iwx_awdl_rx_prepare(f.data(),f.size(),149,-43,0xfffffff0,&h);
 if(!ok)assert(!memcmp(&h,&old,sizeof(h)));return ok;}
int main(){
 auto f=good();assert(valid(f));iwx_awdl_rx_header h;
 assert(iwx_awdl_rx_prepare(f.data(),f.size(),149,-43,0xfffffff0,&h));
 assert(h.channel_version==1&&h.channel==149&&h.channel_flags==18&&h.rssi_dbm==-43&&h.device_us==0xfffffff0&&!h.rate);
 assert(!memcmp(h.sender,f.data()+10,6));
 for(unsigned channel:{1,6,14,36,44,149,177}){assert(iwx_awdl_rx_prepare(f.data(),f.size(),channel,-127,7,&h));assert(h.channel_flags==(channel<=14?10u:18u));}
 for(unsigned n=0;n<40;++n){auto g=f;g.resize(n);assert(!valid(g));}
 for(unsigned flag:{1,2,4,64,128}){auto g=f;g[1]=flag;assert(!valid(g));}
 for(unsigned offset:{0,10,16,22,24,25,26,27,28,30}){auto g=f;g[offset]^=1;assert(!valid(g));}
 // Real frames carry a version; the family's own check refuses zero.
 {auto g=f;g[29]=0;assert(!valid(g));g[29]=1;assert(valid(g));}
 {auto g=f;g.resize(2049,0xff);assert(!valid(g));}
 auto tlv=f;tlv.insert(tlv.end(),{21,2,0,0x93,1});assert(valid(tlv));
 // Bad TLVs go to the family's bounded parser; only the fixed header decides here.
 for(unsigned n=41;n<45;++n){auto g=tlv;g.resize(n);assert(valid(g));}
 assert(!iwx_awdl_rx_prepare(nullptr,40,149,-40,0,&h));
 assert(!iwx_awdl_rx_prepare(f.data(),40,0,-40,0,&h));assert(!iwx_awdl_rx_prepare(f.data(),40,178,-40,0,&h));
 assert(!iwx_awdl_rx_prepare(f.data(),40,149,1,0,&h));assert(!iwx_awdl_rx_prepare(f.data(),40,149,-128,0,&h));
 assert(!iwx_awdl_rx_prepare(f.data(),40,149,-40,0,nullptr));
 size_t page=getpagesize();auto mem=(uint8_t*)mmap(nullptr,page*2,PROT_READ|PROT_WRITE,MAP_ANON|MAP_PRIVATE,-1,0);
 assert(mem!=MAP_FAILED&&!mprotect(mem+page,page,PROT_NONE));
 for(size_t n=0;n<=tlv.size();++n){memcpy(mem+page-n,tlv.data(),n);iwx_awdl_rx_prepare(mem+page-n,n,149,-40,123,&h);}
 munmap(mem,page*2);
 uint32_t seed=17;auto random=[&]{seed=seed*1664525+1013904223;return seed;};
 for(unsigned i=0;i<300000;++i){auto g=tlv;for(unsigned j=0;j<4;++j)g[random()%g.size()]=random()>>16;
  g.resize(random()%(g.size()+1));valid(g);}
 {
  // Peer data round trip with the sender's builder, and rejections.
  static iwx_awdl_probe q;memset(q.tx.self,0,6);q.tx.self[0]=6;q.tx.self[5]=9;const uint8_t me[6]={2,1,2,3,4,5};
  uint8_t eth[60];memcpy(eth,me,6);memset(eth+6,0xee,6);eth[12]=0x86;eth[13]=0xdd;memset(eth+14,0x42,46);
  uint8_t air[256],back[256];size_t n=iwx_awdl_ether_to_data(&q,eth,sizeof(eth),air,sizeof(air));
  assert(n==24+16+46&&air[0]==8&&!memcmp(air+4,me,6)&&!memcmp(air+10,q.tx.self,6)&&!memcmp(air+16,iwx_awdl_bssid,6)&&air[24]==0xaa&&air[31]==0&&air[32]==3&&air[33]==4&&air[38]==0x86&&air[39]==0xdd&&air[40]==0x42);
  size_t m=iwx_awdl_data_to_ether(air,n,me,back,sizeof(back));assert(m==60&&!memcmp(back,me,6)&&!memcmp(back+6,q.tx.self,6)&&back[12]==0x86&&back[13]==0xdd&&back[14]==0x42);
  assert(!iwx_awdl_ether_to_data(&q,eth,13,air,sizeof(air))&&!iwx_awdl_ether_to_data(&q,eth,60,air,50));
  const uint8_t other[6]={2,9,9,9,9,9};assert(!iwx_awdl_data_to_ether(air,n,other,back,sizeof(back)));
  air[4]|=1;assert(iwx_awdl_data_to_ether(air,n,other,back,sizeof(back))==60);air[4]&=~1;
  assert(!iwx_awdl_data_to_ether(air,n,me,back,20));
  for(unsigned bad:{0u,1u,10u,16u,24u,32u}){uint8_t c[256];memcpy(c,air,n);c[bad]^=(bad==0?0x40:(bad==10||bad==1)?1:0x10);assert(!iwx_awdl_data_to_ether(c,n,me,back,sizeof(back)));}
  uint8_t q2[256]={};memcpy(q2,air,24);q2[0]=0x88;memcpy(q2+26,air+24,n-24);assert(iwx_awdl_data_to_ether(q2,n+2,me,back,sizeof(back))==60);
  for(size_t t=0;t<n;++t)if(t<=40)assert(!iwx_awdl_data_to_ether(air,t,me,back,sizeof(back)));
 }
 {
  // RFC 8200 checksum: a filled packet verifies to all ones, and a partial one is rewritten to match.
  uint8_t ip[60]={};ip[0]=0x60;ip[4]=0;ip[5]=20;ip[6]=6;ip[7]=255;ip[8]=0xfe;ip[9]=0x80;ip[23]=1;ip[24]=0xfe;ip[25]=0x80;ip[39]=2;ip[41]=0x50;ip[43]=0x51;
  assert(iwx_awdl_fix_l4_csum(ip,sizeof(ip)));
  auto verify=[](const uint8_t*b,size_t l4){uint32_t s=b[6]+uint32_t(l4);for(size_t i=8;i+1<40+l4;i+=2)s+=uint32_t((b[i]<<8)|b[i+1]);if(l4&1)s+=uint32_t(b[40+l4-1])<<8;while(s>>16)s=(s&0xffff)+(s>>16);return s==0xffff;};
  assert(verify(ip,20));assert(!iwx_awdl_fix_l4_csum(ip,sizeof(ip)));assert(verify(ip,20));
  uint8_t u[49]={};u[0]=0x60;u[5]=9;u[6]=17;u[47]=9;u[48]=0x77;assert(iwx_awdl_fix_l4_csum(u,sizeof(u)));assert(verify(u,9));
  uint8_t z[48]={};z[0]=0x60;z[5]=8;z[6]=17;z[45]=8;for(int i=0;i<2;++i)iwx_awdl_fix_l4_csum(z,sizeof(z));assert(z[46]||z[47]);
  // Offsets inside the ICMPv6, IPv4 and short cases are left alone.
  uint8_t c[48]={};c[0]=0x60;c[5]=8;c[6]=58;uint8_t c0[48];memcpy(c0,c,48);assert(!iwx_awdl_fix_l4_csum(c,48)&&!memcmp(c,c0,48));
  uint8_t v4[48]={};v4[0]=0x45;v4[6]=6;assert(!iwx_awdl_fix_l4_csum(v4,48));
  uint8_t s[48]={};s[0]=0x60;s[5]=200;s[6]=6;assert(!iwx_awdl_fix_l4_csum(s,48));s[5]=4;assert(!iwx_awdl_fix_l4_csum(s,48));assert(!iwx_awdl_fix_l4_csum(s,39));
  // A TCP frame through the builder comes out valid and is counted once.
  static iwx_awdl_probe q;uint8_t eth[74]={};eth[12]=0x86;eth[13]=0xdd;memcpy(eth+14,ip,60);eth[14+40+16]^=0x5a;uint8_t air[256];
  size_t n=iwx_awdl_ether_to_data(&q,eth,sizeof(eth),air,sizeof(air));assert(n==24+16+60&&q.tx.csum_fixed==1&&verify(air+40,20)&&eth[14+40+16]==(ip[40+16]^0x5a));
  // What reaches the interface: management, and AWDL data for this address or a group.
  static iwx_awdl_probe w;memset(w.tx.self,0x22,6);uint8_t f[32]={};f[0]=0xd0;assert(iwx_awdl_rx_wanted(&w,f,32));assert(!iwx_awdl_rx_wanted(&w,f,23));assert(!iwx_awdl_rx_wanted(&w,nullptr,32));
  f[0]=0x88;assert(!iwx_awdl_rx_wanted(&w,f,32));memcpy(f+16,iwx_awdl_bssid,6);assert(!iwx_awdl_rx_wanted(&w,f,32));memset(f+4,0x22,6);assert(iwx_awdl_rx_wanted(&w,f,32));
  f[1]=2;assert(!iwx_awdl_rx_wanted(&w,f,32));f[1]=0;memset(f+4,0x44,6);assert(!iwx_awdl_rx_wanted(&w,f,32));f[4]=0x33;assert(iwx_awdl_rx_wanted(&w,f,32));f[0]=0xc4;assert(!iwx_awdl_rx_wanted(&w,f,32));
 }
 puts("PASS: native 72-byte RX metadata, offsets, sender/channel/RSSI/clock, rejection without mutation, truncations, guard page and 300000 malformed frames");
}
'''
with tempfile.TemporaryDirectory() as t:
    p=Path(t);(p/'rx.cpp').write_text(src)
    subprocess.run(['clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(root/'itlwm/hal_iwx'),str(p/'rx.cpp'),'-o',str(p/'rx')],check=True)
    subprocess.run([str(p/'rx')],check=True)
s=(root/'itlwm/hal_iwx/ItlIwx.cpp').read_text();a=s.index('iwx_rx_mpdu_mq(struct');b=s.index('iwx_rx_tx_cmd_single(',a);rx=s[a:b]
assert rx.index('mic_crc_len') < rx.index('mbuf_adj(m, 2)') < rx.index('iwx_awdl_probe_rx(') < rx.index('inputAWDLActionFrame(') < rx.index('mbuf_freem(m);',rx.index('inputAWDLActionFrame('))
for guard in ['iwx_awdl_rx_wanted(','sc_awdl_native_requested','IWX_AWDL_CTX_ACTIVE','IWX_FLAG_SHUTDOWN','IWX_FLAG_HW_ERR','ic_wcl_teardown_pending','getMainWorkLoop()->inGate()']:assert guard in rx,guard
print('PASS: real RX integration strips firmware trailer/pad first; borrows frame only under active monitor/gate and before freeing it')
