#!/usr/bin/env python3
"""Offline checks for the default-off AWDL sync and transmit (1.1.11)."""
from pathlib import Path
import subprocess, tempfile
ROOT = Path(__file__).resolve().parent.parent
src = r'''
#include <assert.h>
#include <stdio.h>
#include <vector>
#include "iwx_awdl_probe.h"
typedef std::vector<uint8_t> V;
static const uint8_t BSS[6]={2,1,1,1,1,1},PEER[6]={2,2,2,2,2,1},PEER2[6]={2,2,2,2,2,2},MASTER[6]={2,3,3,3,3,3},MASTER2[6]={2,4,4,4,4,4},SELF[6]={2,5,5,5,5,5};
static void tlv(V&b,uint8_t t,const V&v){b.push_back(t);b.push_back(uint8_t(v.size()));b.push_back(uint8_t(v.size()>>8));b.insert(b.end(),v.begin(),v.end());}
static V seqv(uint8_t enc,uint8_t chan,uint8_t aux){V v={15,enc,0,3,0xff,0xff};for(int i=0;i<16;++i){if(enc==0)v.push_back(chan);else if(enc==1){v.push_back(aux);v.push_back(chan);}else{v.push_back(chan);v.push_back(aux);}}return v;}
static V peerframe(const uint8_t*sa,const uint8_t*master,uint16_t ttn,uint8_t enc=3){
 V f(24,0);f[0]=0xd0;memset(&f[4],0xff,6);memcpy(&f[10],sa,6);memcpy(&f[16],iwx_awdl_bssid,6);
 V b={127,0,0x17,0xf2,8,0x10,0,0, 1,0,0,0, 1,0,0,0};
 V s(33,0);s[0]=149;s[1]=uint8_t(ttn);s[2]=uint8_t(ttn>>8);s[3]=149;s[5]=16;s[7]=110;memcpy(&s[21],master,6);s[27]=4;s[29]=0x40;tlv(b,4,s);
 V e(21,0);e[3]=2;memcpy(&e[5],master,6);e[11]=0x10;e[12]=0x27;tlv(b,5,e);
 tlv(b,18,seqv(enc,149,0x80));
 V e2(40,0);e2[12]=7;tlv(b,24,e2);
 tlv(b,21,V{0x3e,2});
 f.insert(f.end(),b.begin(),b.end());return f;}
static iwx_awdl_probe fresh(){iwx_awdl_probe p={};p.mode=1;p.tx.mode=1;memcpy(p.tx.self,SELF,6);p.rx_chan=149;p.rx_gp2=1000000;p.rx_host_us=50000000;return p;}
int main(){
 iwx_awdl_probe p=fresh();auto f=peerframe(PEER,MASTER,30);
 assert(iwx_awdl_tx_decide(&p,p.rx_host_us)==IWX_AWDL_TX_NONE); // No sync yet: never transmit.
 assert(iwx_awdl_probe_rx(&p,f.data(),f.size(),BSS)==IWX_AWDL_PROBE_DROP);
 assert(p.sync.valid&&p.sync.aw_period==16&&p.sync.presence==4&&p.sync.ttn==30&&p.sync.height==2&&p.sync.encoding==3&&p.sync.chan_aux==0x80&&p.sync.master_metric==10000&&p.sync.master_counter==7&&p.sync.version==0x3e&&p.slots_149==16&&p.slots_current==16&&!p.parse_bad);
 // Our own frame must parse back to what we announce.
 uint8_t o[IWX_AWDL_FRAME_MAX];static const uint8_t BC[6]={255,255,255,255,255,255};
 for(uint8_t sub:{0,3}){size_t n=iwx_awdl_build(&p,BC,sub,p.rx_host_us,o,sizeof(o));assert(n>100&&n<=IWX_AWDL_FRAME_MAX);
  assert(o[0]==0xd0&&!memcmp(o+4,BC,6)&&!memcmp(o+10,SELF,6)&&!memcmp(o+16,iwx_awdl_bssid,6));
  const uint8_t*b=o+24;assert(b[0]==127&&b[4]==8&&b[5]==0x10&&b[6]==sub);
  iwx_awdl_tlvs t;assert(iwx_awdl_parse(b,n-24,&t));
  assert(t.sync&&t.election&&t.election2&&t.chanseq&&t.version);
  assert(t.sync_len==33+38+2&&t.chanseq_len==38+3&&t.election_len==21&&t.election2_len==40&&t.version_len==2);
  assert(t.sync[0]==149&&iwx_awdl_le16(t.sync+1)==30&&iwx_awdl_le16(t.sync+5)==16&&!memcmp(t.sync+21,MASTER,6)&&t.sync[27]==4&&iwx_awdl_le16(t.sync+29)==0x40);
  assert(t.election[3]==3&&!memcmp(t.election+5,MASTER,6)&&iwx_awdl_le32(t.election+11)==10000&&iwx_awdl_le32(t.election+15)<iwx_awdl_le32(t.election+11));
  assert(!memcmp(t.election2,MASTER,6)&&!memcmp(t.election2+6,PEER,6)&&iwx_awdl_le32(t.election2+16)==3);
  assert(t.chanseq[0]==15&&t.chanseq[1]==3&&t.chanseq[6]==149&&t.chanseq[7]==0x80);
  assert(t.version[0]==0x3e&&t.version[1]==1);
  // A second peer reading our frame gets a usable sync state.
  iwx_awdl_probe q=fresh();q.tx.mode=0;V g(o,o+n);iwx_awdl_probe_rx(&q,g.data(),g.size(),BSS);assert(q.sync.valid&&q.sync.ttn==30&&q.sync.height==3&&!q.parse_bad);
 }
 size_t psf=iwx_awdl_build(&p,BC,0,p.rx_host_us,o,sizeof(o)),mif=iwx_awdl_build(&p,BC,3,p.rx_host_us,o,sizeof(o));assert(mif>psf);
 assert(iwx_awdl_build(&p,BC,0,p.rx_host_us,o,IWX_AWDL_FRAME_MAX-1)==0);
 {
  // Native: the system's TLVs behind our head; only well-formed ones, broadcast, no unicast decisions.
  static iwx_awdl_probe q;q=p;q.tx.native=1;q.tx.peer_valid=1;static uint8_t big[IWX_AWDL_NATIVE_FRAME_MAX];
  const uint8_t tl[]={21,2,0,0x93,1,6,1,0,9};
  assert(iwx_awdl_tx_decide(&q,q.rx_host_us)==IWX_AWDL_TX_NONE);
  assert(!iwx_awdl_native_template(&q,true,tl,sizeof(tl)-1)&&q.tx.native_rejected==1);assert(!q.tx.native_mif_len);
  assert(!iwx_awdl_native_template(&q,true,nullptr,4));assert(!iwx_awdl_native_template(&q,false,tl,IWX_AWDL_NATIVE_TLV_MAX+1));
  assert(iwx_awdl_native_template(&q,true,tl,sizeof(tl))&&iwx_awdl_native_template(&q,false,tl,5));
  q.tx.last_mif_us=q.tx.last_psf_us=0;
  assert(iwx_awdl_tx_decide(&q,q.rx_host_us)==IWX_AWDL_TX_MIF);
  for(bool mif:{true,false}){size_t n=iwx_awdl_build_native(&q,mif,q.rx_host_us,big,sizeof(big));assert(n>40);
   assert(big[0]==0xd0&&big[4]==0xff&&!memcmp(big+10,q.tx.self,6)&&big[24]==127&&big[29]==q.sync.action_version&&big[30]==(mif?3:0));
   iwx_awdl_tlvs t;assert(iwx_awdl_parse(big+24,n-24,&t)&&t.sync&&t.chanseq&&t.version&&t.version_len==2);}
  assert(!iwx_awdl_build_native(&q,true,q.rx_host_us,big,IWX_AWDL_NATIVE_FRAME_MAX-1));
  q.tx.native_mif_len=0;assert(!iwx_awdl_build_native(&q,true,q.rx_host_us,big,sizeof(big)));
  {iwx_awdl_tx x={};
   assert(iwx_awdl_data_rate(0)==0x207&&iwx_awdl_data_rate(1)==0x204&&iwx_awdl_data_rate(2)==0x202&&iwx_awdl_data_rate(3)==-1&&iwx_awdl_data_rate(9)==-1);
   assert(iwx_awdl_data_rate(-1)==(0x300|0x10|8)&&iwx_awdl_data_rate(-2)==(0x300|0x1000|0x10|7)&&iwx_awdl_data_rate(-3)==(0x300|0x1000|0x10|9)&&iwx_awdl_data_rate(-4)==-1);
   for(int i=0;i<63;++i)iwx_awdl_rate_note(&x,true);assert(x.rate_step==0);iwx_awdl_rate_note(&x,true);assert(x.rate_step==-1&&x.rate_ups==1);
   for(int i=0;i<64;++i)iwx_awdl_rate_note(&x,true);assert(x.rate_step==-2);for(int i=0;i<64;++i)iwx_awdl_rate_note(&x,true);assert(x.rate_step==-3&&x.rate_ups==3);
   for(int i=0;i<500;++i)iwx_awdl_rate_note(&x,true);assert(x.rate_step==-3);
   iwx_awdl_rate_note(&x,false);assert(x.rate_step==-3);iwx_awdl_rate_note(&x,true);iwx_awdl_rate_note(&x,false);assert(x.rate_step==-3);iwx_awdl_rate_note(&x,false);assert(x.rate_step==-2&&x.rate_downs==1&&x.rate_up_after==128);
   for(int i=0;i<100;++i)iwx_awdl_rate_note(&x,false);assert(x.rate_step==3&&iwx_awdl_data_rate(x.rate_step)==-1&&x.rate_up_after==4096&&x.rate_downs==6);
   for(int i=0;i<4095;++i)iwx_awdl_rate_note(&x,true);assert(x.rate_step==3);iwx_awdl_rate_note(&x,true);assert(x.rate_step==2);
   iwx_awdl_probe m={};iwx_awdl_tx_note_done(&m,true,false,131,14);iwx_awdl_tx_note_done(&m,true,false,131,14);assert(m.tx.rate_step==1&&m.tx.unicast_noack==2);iwx_awdl_tx_note_done(&m,false,false,131,14);iwx_awdl_tx_note_done(&m,false,false,131,14);assert(m.tx.rate_step==1);}
  {iwx_awdl_probe a={};uint16_t sq=0;uint32_t wu=0;assert(!iwx_awdl_sync_next(&a,1000,&sq,&wu));a.sync.valid=1;a.sync.aw_period=16;a.sync.presence=4;a.sync.ttn=10;a.sync.aw_seq=100;a.sync.host_us=1000000;
   assert(iwx_awdl_sync_next(&a,1000000,&sq,&wu)&&sq==104&&wu==10*IWX_AWDL_TU_US);
   assert(iwx_awdl_sync_next(&a,1000000+5*IWX_AWDL_TU_US,&sq,&wu)&&sq==104&&wu==5*IWX_AWDL_TU_US);
   assert(iwx_awdl_sync_next(&a,1000000+11*IWX_AWDL_TU_US,&sq,&wu)&&sq==108&&wu==63*IWX_AWDL_TU_US);
   assert(iwx_awdl_sync_next(&a,1000000+10*IWX_AWDL_TU_US,&sq,&wu)&&sq==108&&wu==64*IWX_AWDL_TU_US);
   assert(iwx_awdl_sync_next(&a,1000000+(10+64*3+1)*IWX_AWDL_TU_US,&sq,&wu)&&sq==120&&wu==63*IWX_AWDL_TU_US);
   assert(!iwx_awdl_sync_next(&a,3100000,&sq,&wu)&&!iwx_awdl_sync_next(&a,999999,&sq,&wu));a.sync.valid=0;assert(!iwx_awdl_sync_next(&a,1000000,&sq,&wu));
   a.sync.valid=1;a.sync.presence=0;assert(!iwx_awdl_sync_next(&a,1000000,&sq,&wu));}
  {iwx_awdl_probe d=q;d.tx.native_mif_len=4;d.tx.native_psf_len=4;d.tx.last_mif_us=d.tx.last_psf_us=0;d.rx_host_us+=IWX_AWDL_NATIVE_MIF_INTERVAL_US;d.sync.host_us=d.rx_host_us;
   assert(iwx_awdl_tx_decide(&d,d.rx_host_us)==IWX_AWDL_TX_MIF);iwx_awdl_tx_note_queued(&d,IWX_AWDL_TX_MIF,d.rx_host_us);
   assert(iwx_awdl_tx_decide(&d,d.rx_host_us)==IWX_AWDL_TX_PSF);iwx_awdl_tx_note_queued(&d,IWX_AWDL_TX_PSF,d.rx_host_us);assert(d.tx.psf_sent==1);
   assert(iwx_awdl_tx_decide(&d,d.rx_host_us)==IWX_AWDL_TX_NONE);}
  q.tx.native_psf_len=0;q.tx.last_psf_us=0;assert(iwx_awdl_tx_decide(&q,q.rx_host_us)==IWX_AWDL_TX_NONE);
 }
 // The down counter wraps into the next extended window as time passes.
 {size_t n=iwx_awdl_build(&p,BC,0,p.rx_host_us+40*1024,o,sizeof(o));iwx_awdl_tlvs t;iwx_awdl_parse(o+24,n-24,&t);uint16_t c=iwx_awdl_le16(t.sync+1);assert(c==54&&iwx_awdl_le16(t.sync+29)==0x44);}
 // Other encodings keep our channel readable.
 for(uint8_t enc:{0,1,3}){iwx_awdl_probe q=fresh();auto g=peerframe(PEER,MASTER,30,enc);iwx_awdl_probe_rx(&q,g.data(),g.size(),BSS);assert(q.slots_current==16);size_t n=iwx_awdl_build(&q,BC,0,q.rx_host_us,o,sizeof(o));iwx_awdl_tlvs t;assert(iwx_awdl_parse(o+24,n-24,&t));iwx_awdl_probe r=fresh();r.tx.mode=0;V h(o,o+n);iwx_awdl_probe_rx(&r,h.data(),h.size(),BSS);assert(r.slots_current==32||enc==0||r.slots_current==16);}
 // Rate limits, and only right after hearing a peer.
 uint64_t t0=p.rx_host_us;
 assert(iwx_awdl_tx_decide(&p,t0+IWX_AWDL_TX_WINDOW_US+1)==IWX_AWDL_TX_NONE);
 assert(iwx_awdl_tx_decide(&p,t0)==IWX_AWDL_TX_UNICAST);iwx_awdl_tx_note_queued(&p,IWX_AWDL_TX_UNICAST,t0);
 assert(iwx_awdl_tx_decide(&p,t0)==IWX_AWDL_TX_MIF);iwx_awdl_tx_note_queued(&p,IWX_AWDL_TX_MIF,t0);
 assert(iwx_awdl_tx_decide(&p,t0)==IWX_AWDL_TX_PSF);iwx_awdl_tx_note_queued(&p,IWX_AWDL_TX_PSF,t0);
 assert(iwx_awdl_tx_decide(&p,t0)==IWX_AWDL_TX_NONE&&p.tx.unicast_sent==1&&p.tx.mcast_sent==2);
 iwx_awdl_probe m=p;m.tx.mode=0;assert(iwx_awdl_tx_decide(&m,t0+5000000)==IWX_AWDL_TX_NONE);
 m=p;m.tx.tripped=1;m.sync.host_us=t0+5000000;assert(iwx_awdl_tx_decide(&m,t0+5000000)==IWX_AWDL_TX_NONE);
 iwx_awdl_tx_note_done(&p,true,true,1,2);iwx_awdl_tx_note_done(&p,true,false,0x82,15);iwx_awdl_tx_note_done(&p,false,true,1,0);iwx_awdl_tx_note_done(&p,false,false,0x83,0);
 assert(p.tx.unicast_ack==1&&p.tx.unicast_noack==1&&p.tx.unicast_retries==17&&p.tx.mcast_ok==1&&p.tx.mcast_fail==1&&p.tx.last_fail_status==0x83);
 // Cluster: stay on the reference until it has gone quiet.
 {iwx_awdl_probe q=fresh();auto a=peerframe(PEER,MASTER,30),b=peerframe(PEER2,MASTER2,40);iwx_awdl_probe_rx(&q,a.data(),a.size(),BSS);q.rx_host_us+=1000;iwx_awdl_probe_rx(&q,b.data(),b.size(),BSS);assert(!memcmp(q.sync.master,MASTER,6)&&q.sync.ttn==30);
  q.rx_host_us+=IWX_AWDL_SLOW_INTERVAL_US;iwx_awdl_probe_rx(&q,b.data(),b.size(),BSS);assert(!memcmp(q.sync.master,MASTER2,6)&&q.sync.ttn==40&&!memcmp(q.tx.peer,PEER2,6));}
 // Timing: steady boundaries land in the first bucket, an offset in the last, across GP2 wrap.
 {iwx_awdl_probe q=fresh();q.rx_gp2=0xffffff00u;auto a=peerframe(PEER,MASTER,30);iwx_awdl_probe_rx(&q,a.data(),a.size(),BSS);
  q.rx_gp2+=16*IWX_AWDL_TU_US;q.rx_host_us+=16*IWX_AWDL_TU_US;iwx_awdl_probe_rx(&q,a.data(),a.size(),BSS);assert(q.jitter[0]==1);
  q.rx_gp2+=5*IWX_AWDL_TU_US;q.rx_host_us+=5*IWX_AWDL_TU_US;iwx_awdl_probe_rx(&q,a.data(),a.size(),BSS);assert(q.jitter[3]==1);
  q.rx_gp2+=16*IWX_AWDL_TU_US;q.rx_host_us+=16*IWX_AWDL_TU_US+2000;iwx_awdl_probe_rx(&q,a.data(),a.size(),BSS);assert(q.host_jitter[2]==1);}
 // Bad zero period never divides; truncated TLVs stay in bounds.
 {iwx_awdl_probe q=fresh();auto a=peerframe(PEER,MASTER,30);a[24+16+3+5]=0;a[24+16+3+6]=0;iwx_awdl_probe_rx(&q,a.data(),a.size(),BSS);assert(!q.sync.valid&&q.parse_bad==1);}
 {auto a=peerframe(PEER,MASTER,30);for(size_t n=0;n<a.size();++n){iwx_awdl_probe q=fresh();iwx_awdl_probe_rx(&q,a.data(),n,BSS);}}
 uint32_t seed=7;auto r=[&]{seed=seed*1664525+1013904223;return seed>>9;};
 for(unsigned i=0;i<300000;++i){iwx_awdl_probe q=fresh();auto a=peerframe(PEER,MASTER,30);for(unsigned k=0;k<6;++k)a[24+r()%(a.size()-24)]=uint8_t(r());size_t n=24+r()%(a.size()-23);iwx_awdl_probe_rx(&q,a.data(),n,BSS);
  uint8_t x[IWX_AWDL_FRAME_MAX];size_t l=iwx_awdl_build(&q,BC,(i&1)?3:0,q.rx_host_us+r()%1000000,x,sizeof(x));assert(l<=IWX_AWDL_FRAME_MAX);if(l){iwx_awdl_tlvs t;assert(iwx_awdl_parse(x+24,l-24,&t));}}
 puts("PASS: sync parsed; PSF/MIF round-trip; low metric; counter wrap; rate limits; reference held; latch; 300000 mutated frames");
}
'''
with tempfile.TemporaryDirectory() as d:
    c = Path(d)/'t.cpp'; c.write_text(src)
    subprocess.run(['clang++','-std=c++17','-w','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(ROOT/'itlwm/hal_iwx'),str(c),'-o',d+'/t'],check=True)
    subprocess.run([d+'/t'],check=True)
s=(ROOT/'itlwm/hal_iwx/ItlIwx.cpp').read_text()
assert 'sc->sc_awdl_probe.tx.mode = awdlTx == 1 && sc->sc_awdl_probe.mode ? 1 : 0;' in s
i=s.index('iwx_awdl_tx_maybe(struct iwx_softc *sc)\n{');fn=s[i:s.index('#endif',i)]
for need in ['iwx_ap_port_open(ic, ni)','IWX_FLAG_MLD_TXQ_ACTIVE','IWX_FLAG_TXFLUSH','qfullmsk.empty()','ieee80211_ref_node(ni)','ieee80211_release_node(ic, ni)','mbuf_freem(m)']:
    assert need in fn,need
i=s.index('iwx_rx_tx_cmd_single(struct iwx_softc *sc');fn=s[i:s.index('iwx_clear_tx_desc',i)]
assert fn.index('txd->awdl_kind')<fn.index('iwx_toggle_tx_ant')
i=s.index('iwx_nic_error(struct iwx_softc *sc)\n{');assert 'tx.tripped = 1' in s[i:i+600]
h=s.index('iwx_awdl_tx_maybe(sc);');assert s.index('len = le16toh(desc->mpdu_len);')<h<s.index('memset(&rxi, 0, sizeof(rxi));',h)
print('PASS: transmit needs both boot arguments, an authorized link and a free queue; AWDL losses stay out of AP antenna state; firmware fault latches it off')
