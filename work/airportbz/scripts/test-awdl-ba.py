#!/usr/bin/env python3
"""Offline checks for AWDL block ack answers and transmit flow control (1.1.41)."""
from pathlib import Path
import subprocess, tempfile
ROOT = Path(__file__).resolve().parent.parent
src = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <vector>
#include "iwx_awdl_probe.h"
typedef std::vector<uint8_t> V;
static const uint8_t SELF[6]={2,1,1,1,1,1},PEER[6]={2,2,2,2,2,1},OTHER[6]={2,3,3,3,3,3};
static V action(const uint8_t*to,const uint8_t*bss,V body){
 V f(24,0);f[0]=0xd0;memcpy(&f[4],to,6);memcpy(&f[10],PEER,6);memcpy(&f[16],bss,6);f.insert(f.end(),body.begin(),body.end());return f;}
int main(){
 /* The request this phone really sent, from ItlwmAwdlNativeRxLastBad on 1.1.40, completed with a sequence. */
 V real={3,0,0x75,0x03,0x10,0x90,0xe2,0x80,0x12};
 struct iwx_awdl_ba_req r;
 V f=action(SELF,iwx_awdl_bssid,real);
 assert(iwx_awdl_ba_parse(SELF,f.data(),f.size(),&r));
 assert(!r.del&&r.tid==0&&r.win==64&&r.dialog==0x75&&r.param==0x1003&&r.timeout==0xe290);
 assert(r.ssn==(0x1280>>4));assert(!memcmp(r.peer,PEER,6));
 /* Not for this interface, not this BSS, not block ack, too short. */
 V g=action(OTHER,iwx_awdl_bssid,real);assert(!iwx_awdl_ba_parse(SELF,g.data(),g.size(),&r));
 g=action(SELF,OTHER,real);assert(!iwx_awdl_ba_parse(SELF,g.data(),g.size(),&r));
 V a=real;a[0]=127;g=action(SELF,iwx_awdl_bssid,a);assert(!iwx_awdl_ba_parse(SELF,g.data(),g.size(),&r));
 a=real;a.resize(7);g=action(SELF,iwx_awdl_bssid,a);assert(!iwx_awdl_ba_parse(SELF,g.data(),g.size(),&r));
 /* A window of 0 or above 64 becomes what this side answers with. */
 a=real;a[3]=0x02;a[4]=0x00;g=action(SELF,iwx_awdl_bssid,a);assert(iwx_awdl_ba_parse(SELF,g.data(),g.size(),&r)&&r.win==64);
 a=real;a[3]=0x02;a[4]=0x40;g=action(SELF,iwx_awdl_bssid,a);assert(iwx_awdl_ba_parse(SELF,g.data(),g.size(),&r)&&r.win==64);
 /* TID 8 and up are not QoS data. */
 a=real;a[3]=0x22;a[4]=0x10;g=action(SELF,iwx_awdl_bssid,a);assert(!iwx_awdl_ba_parse(SELF,g.data(),g.size(),&r));
 /* TID 5, window 32. */
 a=real;a[3]=uint8_t(0x02|(5<<2));a[4]=0x08;g=action(SELF,iwx_awdl_bssid,a);
 assert(iwx_awdl_ba_parse(SELF,g.data(),g.size(),&r)&&r.tid==5&&r.win==32);
 /* The answer: no A-MSDU even though the request allowed it. */
 assert(iwx_awdl_ba_parse(SELF,f.data(),f.size(),&r));
 uint8_t out[64];
 assert(!iwx_awdl_ba_build_resp(SELF,&r,0,out,32));
 size_t n=iwx_awdl_ba_build_resp(SELF,&r,IWX_AWDL_BA_STATUS_OK,out,sizeof(out));
 assert(n==33&&out[0]==0xd0&&!memcmp(out+4,PEER,6)&&!memcmp(out+10,SELF,6)&&!memcmp(out+16,iwx_awdl_bssid,6));
 assert(out[24]==3&&out[25]==1&&out[26]==0x75&&out[27]==0&&out[28]==0);
 uint16_t bp=iwx_awdl_le16(out+29);assert(!(bp&1)&&(bp&2)&&((bp>>2)&15)==0&&(bp>>6)==64);
 assert(iwx_awdl_le16(out+31)==0xe290);
 n=iwx_awdl_ba_build_resp(SELF,&r,IWX_AWDL_BA_STATUS_REFUSED,out,sizeof(out));assert(iwx_awdl_le16(out+27)==37);
 /* DELBA: only a session the peer started. */
 V del={3,2,0x00,0x08,0x25,0x00};f=action(SELF,iwx_awdl_bssid,del);
 assert(iwx_awdl_ba_parse(SELF,f.data(),f.size(),&r)&&r.del&&r.tid==0);
 del={3,2,0x00,0x58,0x25,0x00};f=action(SELF,iwx_awdl_bssid,del);assert(iwx_awdl_ba_parse(SELF,f.data(),f.size(),&r)&&r.del&&r.tid==5);
 del={3,2,0x00,0x00,0x25,0x00};f=action(SELF,iwx_awdl_bssid,del);assert(!iwx_awdl_ba_parse(SELF,f.data(),f.size(),&r));
 /* Note and bookkeeping. */
 static struct iwx_awdl_probe p;memcpy(p.tx.self,SELF,6);
 f=action(SELF,iwx_awdl_bssid,real);
 assert(iwx_awdl_ba_note(&p,f.data(),f.size())&&p.ba_pending_valid&&p.ba_heard==1&&p.ba_sample[2]==0x75);
 g=action(OTHER,iwx_awdl_bssid,real);assert(!iwx_awdl_ba_note(&p,g.data(),g.size())&&p.ba_heard==1);
 assert(iwx_awdl_peer_index(&p,PEER)==-1);
 memcpy(p.peer_addr[0],OTHER,6);memcpy(p.peer_addr[1],PEER,6);p.peer_added=1;assert(iwx_awdl_peer_index(&p,PEER)==-1);
 p.peer_added=2;assert(iwx_awdl_peer_index(&p,PEER)==1);
 assert(!iwx_awdl_ba_find(&p,PEER,0));
 for(unsigned i=0;i<IWX_AWDL_BA_MAX;++i){auto*s=iwx_awdl_ba_free(&p);assert(s);s->active=1;s->tid=uint8_t(i);memcpy(s->peer,PEER,6);}
 assert(!iwx_awdl_ba_free(&p));assert(iwx_awdl_ba_find(&p,PEER,2)&&!iwx_awdl_ba_find(&p,OTHER,2));
 /* The schedule: the phone's real sequence from 1.1.41, on 36, with presence mode 4. */
 static struct iwx_awdl_probe q;memcpy(q.tx.self,SELF,6);
 static const uint8_t SEQ[16]={36,0,149,0,0,149,36,36,6,0,149,0,0,149,36,36};
 auto*s=&q.sync;s->valid=1;s->seq_valid=1;memcpy(s->seq,SEQ,16);memcpy(s->reference,PEER,6);s->aw_period=16;s->presence=4;s->host_us=1000000;
 auto at=[&](uint16_t slot,uint8_t chan,const uint8_t*d=PEER){s->aw_seq=uint16_t((slot-1)*4);s->ttn=10;return iwx_awdl_peer_away(&q,d,1000000,chan);};
 /* next = aw_seq + presence, so the current slot number is the one given here. */
 s->aw_seq=uint16_t(0*4);s->ttn=10;assert(iwx_awdl_peer_away(&q,PEER,1000000,36)==(SEQ[0]!=36));
 s->aw_seq=uint16_t(2*4);assert(iwx_awdl_peer_away(&q,PEER,1000000,36)==true);assert(iwx_awdl_peer_away(&q,PEER,1000000,149)==false);
 s->aw_seq=uint16_t(6*4);assert(!iwx_awdl_peer_away(&q,PEER,1000000,36));
 (void)at;
 /* Elsewhere and unknown never hold: another peer, a channel it never visits, stale or no schedule. */
 s->aw_seq=uint16_t(2*4);assert(!iwx_awdl_peer_away(&q,OTHER,1000000,36));assert(!iwx_awdl_peer_away(&q,PEER,1000000,44));assert(!iwx_awdl_peer_away(&q,PEER,1000000,0));
 assert(!iwx_awdl_peer_away(&q,PEER,4000000,36));
 s->seq_valid=0;assert(!iwx_awdl_peer_away(&q,PEER,1000000,36));s->seq_valid=1;
 /* A failure while away neither lowers the rate nor resets progress; it is counted apart. */
 q.tx.peer_away=1;q.tx.rate_step=0;q.tx.rate_ok=5;for(int i=0;i<20;++i)iwx_awdl_tx_note_done(&q,true,false,131,14);
 assert(q.tx.rate_step==0&&q.tx.rate_ok==5&&q.tx.fail_away==20&&q.tx.fail_here==0&&q.tx.unicast_noack==20);
 q.tx.peer_away=0;iwx_awdl_tx_note_done(&q,true,false,131,14);iwx_awdl_tx_note_done(&q,true,false,131,14);assert(q.tx.rate_step==1&&q.tx.fail_here==2);
 iwx_awdl_tx_note_done(&q,true,true,1,0);assert(q.tx.ok_here==1);q.tx.peer_away=1;iwx_awdl_tx_note_done(&q,true,true,1,0);assert(q.tx.ok_away==1);
 /* A-MSDU: two packets, one with an odd length so the padding shows. */
 static struct iwx_awdl_probe u;memcpy(u.tx.self,SELF,6);u.tx.seq=100;
 V e1(14+61,0x11),e2(14+40,0x22);memcpy(e1.data(),PEER,6);memcpy(e2.data(),PEER,6);memcpy(e1.data()+6,SELF,6);memcpy(e2.data()+6,SELF,6);e1[12]=e2[12]=0x08;e1[13]=e2[13]=0;
 const uint8_t*es[2]={e1.data(),e2.data()};size_t ls[2]={e1.size(),e2.size()};uint8_t ab[4000];
 size_t an=iwx_awdl_amsdu_build(&u,es,ls,2,ab,sizeof(ab));
 assert(ab[0]==0x88&&ab[1]==0&&!memcmp(ab+4,PEER,6)&&!memcmp(ab+10,SELF,6)&&!memcmp(ab+16,iwx_awdl_bssid,6));
 assert(iwx_awdl_le16(ab+22)==uint16_t(100<<4)&&ab[24]==0x80&&ab[25]==0);
 const uint8_t*sf=ab+26;assert(!memcmp(sf,PEER,6)&&!memcmp(sf+6,SELF,6)&&sf[12]==0&&sf[13]==16+61);
 static const uint8_t LLC[10]={0xaa,0xaa,0x03,0x00,0x17,0xf2,0x08,0x00,0x03,0x04};assert(!memcmp(sf+14,LLC,10)&&iwx_awdl_le16(sf+24)==100&&sf[28]==0x08&&sf[29]==0&&sf[30]==0x11);
 size_t first=14+16+61,padded=(first+3)&~size_t(3);const uint8_t*sf2=sf+padded;assert(padded==92&&sf[first]==0);
 assert(!memcmp(sf2,PEER,6)&&sf2[13]==16+40&&iwx_awdl_le16(sf2+24)==101&&sf2[30]==0x22);
 assert(an==26+padded+14+16+40);assert(u.tx.seq==102);
 /* Each subframe is what the receive side of this driver reads as one AWDL data frame. */
 V rf(24,0);rf[0]=0x08;memcpy(&rf[4],SELF,6);memcpy(&rf[10],PEER,6);memcpy(&rf[16],iwx_awdl_bssid,6);rf.insert(rf.end(),sf+14,sf+14+16+61);
 /* Refused: one packet, too many, mixed peers, group address, too small a buffer, short packet. */
 assert(!iwx_awdl_amsdu_build(&u,es,ls,1,ab,sizeof(ab))&&!iwx_awdl_amsdu_build(&u,es,ls,6,ab,sizeof(ab))&&!iwx_awdl_amsdu_build(&u,es,ls,2,ab,100));
 V e3=e2;memcpy(e3.data(),OTHER,6);const uint8_t*em[2]={e1.data(),e3.data()};assert(!iwx_awdl_amsdu_build(&u,em,ls,2,ab,sizeof(ab)));
 V e4=e1,e5=e2;e4[0]=0x33;e5[0]=0x33;const uint8_t*eg[2]={e4.data(),e5.data()};assert(!iwx_awdl_amsdu_build(&u,eg,ls,2,ab,sizeof(ab)));
 size_t lb[2]={13,ls[1]};assert(!iwx_awdl_amsdu_build(&u,es,lb,2,ab,sizeof(ab)));assert(u.tx.seq==102);
 /* Five full packets fit the limit. */
 V full(1514,1);memcpy(full.data(),PEER,6);const uint8_t*ef[5]={full.data(),full.data(),full.data(),full.data(),full.data()};size_t lf[5]={1514,1514,1514,1514,1514};
 assert(iwx_awdl_amsdu_build(&u,ef,lf,5,u.tx.amsdu_buf,sizeof(u.tx.amsdu_buf))>7000);
 /* Ready only when on, at a VHT step, for a peer with block ack; gives up on all failures. */
 assert(!iwx_awdl_amsdu_ready(&u,PEER));u.tx.amsdu=1;assert(!iwx_awdl_amsdu_ready(&u,PEER));u.tx.rate_step=-1;assert(!iwx_awdl_amsdu_ready(&u,PEER));
 u.ba[1].active=1;memcpy(u.ba[1].peer,PEER,6);assert(iwx_awdl_amsdu_ready(&u,PEER)&&!iwx_awdl_amsdu_ready(&u,OTHER));u.tx.rate_step=0;assert(!iwx_awdl_amsdu_ready(&u,PEER));u.tx.rate_step=-3;
 for(unsigned i=0;i<IWX_AWDL_AMSDU_GIVE_UP-1;++i)iwx_awdl_amsdu_note_done(&u,false);assert(!u.tx.amsdu_gave_up);
 iwx_awdl_amsdu_note_done(&u,true);for(int i=0;i<100;++i)iwx_awdl_amsdu_note_done(&u,false);assert(!u.tx.amsdu_gave_up&&u.tx.amsdu_ok==1);
 u.tx.amsdu_ok=0;u.tx.amsdu_fail=0;for(unsigned i=0;i<IWX_AWDL_AMSDU_GIVE_UP;++i)iwx_awdl_amsdu_note_done(&u,false);assert(u.tx.amsdu_gave_up&&!iwx_awdl_amsdu_ready(&u,PEER));
 /* Second channel windows: mode 1 once a second; mode 2 only in the peer's slots on that channel, every other slot at most. */
 {static struct iwx_awdl_probe w;memcpy(w.tx.self,SELF,6);static const uint8_t WS[16]={149,149,149,149,36,36,36,36,149,149,149,149,6,6,6,6};
  auto*ss=&w.sync;ss->valid=1;ss->seq_valid=1;memcpy(ss->seq,WS,16);memcpy(ss->reference,PEER,6);ss->aw_period=16;ss->presence=4;ss->host_us=1000000;ss->ttn=10;
  ss->aw_seq=uint16_t(0*4);assert(iwx_awdl_peer_slot_chan(&w,1000000)==149);
  ss->aw_seq=uint16_t(4*4);assert(iwx_awdl_peer_slot_chan(&w,1000000)==36);
  assert(iwx_awdl_te_due(&w,1,149,5000000,3000000)==IWX_AWDL_TE_DURATION_TU&&!iwx_awdl_te_due(&w,1,149,3500000,3000000));
  assert(!iwx_awdl_te_due(&w,2,149,1000000,0));
  ss->aw_seq=0;assert(iwx_awdl_te_due(&w,2,149,1000000,0)==IWX_AWDL_TE_SLOT_TU&&!iwx_awdl_te_due(&w,2,149,1000000,1000000-IWX_AWDL_TE_SLOT_GAP_US+1));
  assert(!iwx_awdl_te_due(&w,0,149,1000000,0)&&!iwx_awdl_te_due(&w,2,0,1000000,0)&&!iwx_awdl_te_due(&w,3,149,1000000,0));
  ss->seq_valid=0;assert(!iwx_awdl_peer_slot_chan(&w,1000000)&&!iwx_awdl_te_due(&w,2,149,1000000,0));}
 /* QoS form for the aggregating own queue: same body as plain data, behind a 26-byte header with TID 0. */
 {static struct iwx_awdl_probe q2;memcpy(q2.tx.self,SELF,6);q2.tx.seq=9;V eq(14+20,0x5a);memcpy(eq.data(),PEER,6);memcpy(eq.data()+6,SELF,6);eq[12]=0x08;eq[13]=0;
  uint8_t dq[200],dp[200];size_t nq=iwx_awdl_ether_to_qos(&q2,eq.data(),eq.size(),dq,sizeof(dq));q2.tx.seq=9;size_t np=iwx_awdl_ether_to_data(&q2,eq.data(),eq.size(),dp,sizeof(dp));
  assert(nq==np+2&&dq[0]==0x88&&dp[0]==0x08&&!memcmp(dq+4,PEER,6)&&!memcmp(dq+10,SELF,6)&&!memcmp(dq+16,iwx_awdl_bssid,6)&&dq[24]==0&&dq[25]==0&&!memcmp(dq+26,dp+24,np-24)&&!memcmp(dq+22,dp+22,2));
  assert(!iwx_awdl_ether_to_qos(&q2,eq.data(),13,dq,sizeof(dq))&&!iwx_awdl_ether_to_qos(&q2,eq.data(),eq.size(),dq,30));
  /* Where data goes: unicast only. */
  V mc=eq;mc[0]=0x33;iwx_awdl_note_dest(&q2,mc.data());assert(!q2.tx.last_dest_valid);iwx_awdl_note_dest(&q2,eq.data());assert(q2.tx.last_dest_valid&&!memcmp(q2.tx.last_dest,PEER,6));}
 /* UMI: the family's TLVs behind our header, to one peer; only clean TLVs, never a group address. */
 static struct iwx_awdl_probe um;memcpy(um.tx.self,SELF,6);um.tx.seq=7;um.sync.valid=1;um.sync.encoding=3;um.sync.aw_period=16;um.sync.presence=4;um.sync.ttn=10;um.sync.host_us=1000000;um.rx_chan=149;
 static const uint8_t UTL[8]={4,2,0,0xaa,0xbb,9,0,0};uint8_t uf[IWX_AWDL_NATIVE_FRAME_MAX];
 size_t un=iwx_awdl_build_umi(&um,PEER,UTL,sizeof(UTL),1000000,uf,sizeof(uf));
 assert(un>sizeof(UTL)&&uf[0]==0xd0&&!memcmp(uf+4,PEER,6)&&!memcmp(uf+10,SELF,6)&&!memcmp(uf+16,iwx_awdl_bssid,6)&&iwx_awdl_le16(uf+22)==uint16_t(7<<4)&&uf[24]==127&&uf[24+5]==um.sync.action_version&&uf[24+6]==3&&!memcmp(uf+un-sizeof(UTL),UTL,sizeof(UTL))&&um.tx.seq==8);
 static const uint8_t BTL[4]={4,200,0,1};assert(!iwx_awdl_build_umi(&um,PEER,BTL,sizeof(BTL),1000000,uf,sizeof(uf)));
 static const uint8_t GROUP[6]={0xff,0xff,0xff,0xff,0xff,0xff};assert(!iwx_awdl_build_umi(&um,GROUP,UTL,sizeof(UTL),1000000,uf,sizeof(uf)));assert(!iwx_awdl_build_umi(&um,PEER,UTL,0,1000000,uf,sizeof(uf)));assert(!iwx_awdl_build_umi(&um,PEER,UTL,sizeof(UTL),1000000,uf,10));
 /* Results keep their order, and a full list loses the oldest. */
 iwx_awdl_umi_note(&um,PEER,true);iwx_awdl_umi_note(&um,OTHER,false);assert(um.umi_ok==1&&um.umi_fail==1&&um.umi_done_count==2&&!memcmp(um.umi_done[0].mac,PEER,6)&&um.umi_done[0].status==0&&um.umi_done[1].status==1);
 for(unsigned i=0;i<IWX_AWDL_UMI_DONE_MAX;++i)iwx_awdl_umi_note(&um,OTHER,true);assert(um.umi_done_count==IWX_AWDL_UMI_DONE_MAX&&um.umi_dropped==2);
 /* llw0 routing: ports it sent from come back to it; the table wraps; v4 and short frames stay on awdl0. */
 static struct iwx_awdl_llw_ports lp;uint8_t ue[14+40+8]={};ue[12]=0x86;ue[13]=0xdd;ue[14+6]=17;ue[14+40]=0x12;ue[14+41]=0x34;ue[14+42]=0x56;ue[14+43]=0x78;
 uint8_t ui[14+40+8];memcpy(ui,ue,sizeof(ue));ui[14+40]=0x56;ui[14+41]=0x78;ui[14+42]=0x12;ui[14+43]=0x34;
 assert(iwx_awdl_llw_input(&lp,ui,sizeof(ui))==IWX_AWDL_ROUTE_AWDL);iwx_awdl_llw_learn(&lp,ue,sizeof(ue));iwx_awdl_llw_learn(&lp,ue,sizeof(ue));assert(lp.next==1);assert(iwx_awdl_llw_input(&lp,ui,sizeof(ui))==IWX_AWDL_ROUTE_LLW);
 ui[14+6]=6;assert(iwx_awdl_llw_input(&lp,ui,sizeof(ui))==IWX_AWDL_ROUTE_AWDL);ui[14+6]=58;assert(iwx_awdl_llw_input(&lp,ui,sizeof(ui))==IWX_AWDL_ROUTE_BOTH);ui[14+6]=17;
 assert(iwx_awdl_llw_input(&lp,ui,20)==IWX_AWDL_ROUTE_AWDL);ui[12]=0x08;ui[13]=0;assert(iwx_awdl_llw_input(&lp,ui,sizeof(ui))==IWX_AWDL_ROUTE_AWDL);ui[12]=0x86;ui[13]=0xdd;ui[0]=0x33;assert(iwx_awdl_llw_input(&lp,ui,sizeof(ui))==IWX_AWDL_ROUTE_AWDL);ui[0]=0;
 for(unsigned i=0;i<IWX_AWDL_LLW_PORTS;++i){ue[14+40]=0x20;ue[14+41]=uint8_t(i);iwx_awdl_llw_learn(&lp,ue,sizeof(ue));}assert(iwx_awdl_llw_input(&lp,ui,sizeof(ui))==IWX_AWDL_ROUTE_AWDL);
 /* Peer cache: a request becomes a station slot, once; delete only for a known peer; full gets no answer. */
 static struct iwx_awdl_probe c;c.assoc_rx=1;
 static const uint8_t M1[6]={2,9,9,9,9,1},M2[6]={2,9,9,9,9,2},M3[6]={2,9,9,9,9,3},M4[6]={2,9,9,9,9,4},M5[6]={2,9,9,9,9,5},MC[6]={3,9,9,9,9,1};
 assert(!iwx_awdl_cache_request(&c,M1,IWX_AWDL_CACHE_REQ_DELETE)&&!c.peer_count);
 assert(iwx_awdl_cache_request(&c,M1,0)&&c.peer_count==1&&c.cache_add_wait==1);
 assert(iwx_awdl_cache_request(&c,M1,6)&&c.peer_count==1&&c.cache_add_wait==1);
 assert(!iwx_awdl_cache_request(&c,MC,0)&&!iwx_awdl_cache_request(&c,nullptr,0)&&c.peer_count==1);
 assert(iwx_awdl_cache_request(&c,M2,0)&&c.cache_add_wait==3);
 assert(iwx_awdl_cache_request(&c,M1,IWX_AWDL_CACHE_REQ_DELETE)&&c.cache_del_wait==1&&c.peer_count==2);
 assert(iwx_awdl_cache_request(&c,M3,0)&&iwx_awdl_cache_request(&c,M4,0)&&c.peer_count==4);
 assert(!iwx_awdl_cache_request(&c,M5,0)&&c.cache_full==1&&c.peer_count==4);
 c.peer_failed=1;assert(!iwx_awdl_cache_request(&c,M1,0));c.peer_failed=0;c.assoc_rx=0;assert(!iwx_awdl_cache_request(&c,M1,0));
 assert(!memcmp(c.peer_addr[2],M3,6));
 /* 1.1.54 mode 3: a window at the first slot of this Mac's own run on the second channel, at most two slots. */
 {const uint64_t t0=10000000;
  assert(iwx_awdl_te_own_due(149,1,149,t0,t0+500,0)==IWX_AWDL_OWN_SLOT_TU);
  assert(iwx_awdl_te_own_due(149,3,149,t0,t0,0)==IWX_AWDL_OWN_SLOT_RUN_MAX*IWX_AWDL_OWN_SLOT_TU);
  assert(!iwx_awdl_te_own_due(149,0,149,t0,t0,0));            /* inside a run: the first slot's window covers it */
  assert(!iwx_awdl_te_own_due(36,1,149,t0,t0,0)&&!iwx_awdl_te_own_due(0,1,149,t0,t0,0)&&!iwx_awdl_te_own_due(149,1,0,t0,t0,0));
  assert(!iwx_awdl_te_own_due(149,1,149,t0,t0,t0+1));         /* an earlier window still runs */
  assert(iwx_awdl_te_own_due(149,1,149,t0,t0+16*IWX_AWDL_TU_US,0)&&!iwx_awdl_te_own_due(149,1,149,t0,t0+16*IWX_AWDL_TU_US+1,0)); /* late tick */
  /* Automatic channel: the sequence's 5 GHz channel, never the AP's own, never 2.4 GHz or none. */
  assert(iwx_awdl_phy2_auto(149,36)==149&&!iwx_awdl_phy2_auto(149,149)&&!iwx_awdl_phy2_auto(6,36)&&!iwx_awdl_phy2_auto(0,36)&&iwx_awdl_phy2_auto(44,149)==44);
  /* 1.1.58: the router case, 36 first in the sequence, then 149. */
  assert(iwx_awdl_phy2_auto(36|(149<<8),36)==149&&iwx_awdl_phy2_auto(149|(36<<8),36)==149&&!iwx_awdl_phy2_auto(149|(149<<8),149));
  /* 1.1.60 mode 4: 149 ahead of its slots, the AP's channel ahead of slot 0, nothing without a candidate. */
  assert(iwx_awdl_phy2_follow(149,149)==149&&!iwx_awdl_phy2_follow(149,36)&&!iwx_awdl_phy2_follow(0,149)&&!iwx_awdl_phy2_follow(149,0));
  /* 1.1.64: modes 4 to 6 follow the sequence, 5 and 6 keep the own queue. */
  assert(!iwx_awdl_te_follows(3)&&iwx_awdl_te_follows(4)&&iwx_awdl_te_follows(7)&&!iwx_awdl_te_follows(8)&&!iwx_awdl_te_keeps_own(4)&&iwx_awdl_te_keeps_own(5)&&iwx_awdl_te_keeps_own(7)&&!iwx_awdl_te_keeps_own(8));
  /* 1.1.65: link 1's queue in 6 to 8, windows only up to 6. */
  assert(!iwx_awdl_te_phy2q(5)&&iwx_awdl_te_phy2q(6)&&iwx_awdl_te_phy2q(8)&&!iwx_awdl_te_phy2q(9)&&iwx_awdl_te_windows(1)&&iwx_awdl_te_windows(6)&&!iwx_awdl_te_windows(7)&&!iwx_awdl_te_windows(8)&&!iwx_awdl_te_windows(0));}
 puts("awdl block ack checks passed");return 0;}
'''
with tempfile.TemporaryDirectory() as d:
    c = Path(d)/'t.cpp'; c.write_text(src); exe = Path(d)/'t'
    subprocess.run(['clang++','-std=c++17','-Wall','-Werror','-Wno-unused-function','-I',str(ROOT/'itlwm/hal_iwx'),str(c),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
cpp = (ROOT/'itlwm/hal_iwx/ItlIwx.cpp').read_text(); iface = (ROOT/'AirportItlwm/AirportItlwmAWDLInterface.cpp').read_text(); v2 = (ROOT/'AirportItlwm/AirportItlwmV2.cpp').read_text()
transmit = iface[iface.index('UInt32 AirportItlwmAWDLInterface::transmit'):iface.index('void AirportItlwmAWDLInterface::inputDataFrame')]
assert 'kIOReturnBusy' in transmit and 'return taken;' in transmit and 'be201TxCompEnqueue(queues[1], packets, taken, 0)' in transmit, 'Busy keeps the rest of the ring and completes only what was taken'
assert 'be201TxSubRequestDequeue(queues[0], nullptr, 1)' in transmit, 'Wake with the signal-only option: a completion may not run the queue inline'
assert 'dataTxCalls & 63' in transmit, 'No registry write per call on the transmit path'
send = cpp[cpp.index('IOReturn ItlIwx::iwx_awdl_data_gate'):cpp.index('IOReturn ItlIwx::iwx_awdl_data_enqueue')]
assert send.index('kIOReturnNotReady') < send.index('kIOReturnBusy'), 'A dead context must drop, not wait forever'
assert 'ieee80211_has_qos(wh) && awdlKind != 4' in cpp and 'IWX_TX_CMD_OFFLD_AMSDU' in cpp, 'A-MSDU stays off the AP data queues and tells the firmware'
ctx = cpp[cpp.index('iwx_awdl_ctx_remove(struct iwx_softc *sc)\n{'):]
assert 'iwx_mld_disable_txq(sc, c->own_sta, c->own_tid)' in ctx[:ctx.index('IWX_STA_REMOVE_CMD')] and 'iwx_mld_disable_txq(sc, c->own_sta, IWX_MGMT_TID)' not in cpp, 'Teardown disables the own queue on the TID it was made on (1.1.57)'
assert ctx.index('iwx_awdl_ba_cmd') < ctx.index('IWX_STA_REMOVE_CMD') and ctx.index('iwx_mld_disable_txq(sc, c->own_sta') < ctx.index('IWX_STA_REMOVE_CMD'), 'Block ack and queues go before their station'
assert 'static int be201AwdlOwnQueueValue;' in v2 and 'be201_awdl_own_queue' not in (ROOT/'scripts/build-sequoia-macos.sh').read_text(), 'Own queue stays a RAM switch, off at boot'
ph=cpp[cpp.index('void ItlIwx::iwx_awdl_phy2_task'):cpp.index('void ItlIwx::setAwdlOwnQueue')]
assert ph.index('IWX_LINK_CONTEXT_MODIFY_ACTIVE, 0') < ph.index('link_no_phy = 1') < ph.index('iwx_phy_ctxt_update') < ph.index('c->phy2_chan = want') < ph.index('IWX_FW_CTXT_ACTION_MODIFY, 0, 0) ?: err;', ph.index('c->phy2_chan = want')) < ph.index('IWX_LINK_CONTEXT_MODIFY_RATES_INFO, 1'), 'Inactive, no context, new context, mask 0, active'
assert 'IEEE80211_IS_CHAN_5GHZ' in ph and 'tripped = 1' in ph, 'Only 5 GHz, and any failure ends it for this boot'
assert 'sc_phyctxt[1].id' in cpp[cpp.index('iwx_awdl_ctx_link_cmd(struct iwx_softc *sc, struct iwx_node *in'):], 'The link names the second context'
for oid in ['be201_awdl_tx_hold','be201_awdl_phy2','be201_awdl_phy2_te']:
    assert 'static int be201AwdlTxHoldValue' in v2 and oid in v2 and oid not in (ROOT/'scripts/build-sequoia-macos.sh').read_text()
au=v2[v2.index('void AirportItlwm::startAWDLAuto'):v2.index('bool AirportItlwm::awdlLastBootPanicked')]
assert 'be201_awdl_auto' in au and 'awdlLastBootPanicked()' in au and au.index('awdlLastBootPanicked()')<au.index('be201AwdlVifArm'), 'Off without the flag, and not after a panic'
for gate in ['AcceptSets','Link','Aw','Radio','Rx','Tx','Data']:
    assert f'be201AwdlVif{gate}Value, 1' in au, gate
for test in ['TxHold','Phy2','Phy2Te','Amsdu','CacheOn']:
    assert f'be201Awdl{test}Value' not in au, 'Test switches stay off: '+test
task=cpp[cpp.index('void ItlIwx::iwx_awdl_peer_task'):cpp.index('void ItlIwx::awdlPeerCache')]
assert task.index('iwx_send_cmd_pdu')<task.index('awdlPeerCacheDone') and 'i < p->peer_added' in task, 'Answer only for a station really in the firmware'
assert 'AirportItlwm::awdlCacheOn()' in iface and 'be201AwdlCacheOnValue, 0' in v2, 'Peer cache answers stay off unless a test turns them on'
assert 'AirportItlwm::awdlUmiOn()' in iface and 'be201AwdlUmiValue, 0' not in v2.replace('be201AwdlUmiValue, 0, ""','') and 'AirportItlwm::awdlLlwOn()' in iface, 'UMI and llw0 stay off unless a test turns them on'
for test in ['Umi','Llw']:
    assert f'be201Awdl{test}Value' not in au, 'Test switches stay off: '+test
ph2=cpp[cpp.index('void ItlIwx::iwx_awdl_phy2_task'):cpp.index('void ItlIwx::setAwdlOwnQueue')]
rel=cpp[cpp.index('int ItlIwx::iwx_awdl_own_release'):cpp.index('void ItlIwx::iwx_awdl_ownq_task')]
assert rel.index('iwx_flush_sta_tids') < rel.index('iwx_mld_disable_txq(sc, c->own_sta, c->own_tid)') < rel.index('iwx_reset_tx_ring'), 'Release flushes, then disables the queue it made'
assert ph2.index('IWX_FW_CTXT_ACTION_REMOVE') < ph2.index('iwx_awdl_own_release(sc)') < ph2.index('IWX_LINK_CONTEXT_MODIFY_ACTIVE, 0'), 'Leaving the second channel: window and own queue go before the link moves'
assert 'if (c->phy2_chan) {' in ph2 and 'c->phy2_chan && c->te_want' not in ph2, 'The window ends whatever the switch says'
rt=cpp[cpp.index('void ItlIwx::setAwdlRadioTest'):cpp.index('void ItlIwx::iwx_awdl_phy2_task')]
assert rt.index('c->te_want && !te && ready') < rt.index('c->te_want = uint8_t(te)'), 'Windows going off end the one running'
own=cpp[cpp.index('void ItlIwx::setAwdlOwnQueue'):cpp.index('void ItlIwx::iwx_awdl_ba_send_resp')]
assert own.index('iwx_awdl_peer_index(p, p->tx.last_dest)') < own.index('iwx_tvqm_enable_txq'), 'The own queue follows the data destination'
assert own.index('iwx_awdl_own_release(sc)') < own.index('iwx_tvqm_enable_txq') and 'own_retargets' in own, 'Moving frees the old queue first'
assert own.index('iwx_awdl_peer_agg') < own.index('iwx_tvqm_enable_txq') and 'tid = IWX_MGMT_TID;' in own, 'Aggregation set up before the TID 0 queue, management TID if it fails'
assert 'IWX_STA_DISABLE_TX_CMD' in own and 'IWX_FW_CMD_VER_UNKNOWN' in own, 'Transmit allowed only where the firmware knows the command'
ba=cpp[cpp.index('iwx_rx_tx_ba_notif(struct iwx_softc *sc, struct iwx_rx_packet *pkt'):cpp.index('iwx_ampdu_txq_advance(struct iwx_softc *sc, struct iwx_tx_ring *ring, int idx)')]
assert 'ba_res->sta_id != IWX_STATION_ID && !ownAgg' in ba and 'awdlCtx->own_ok += done' in ba, 'Aggregates for the own peer are reclaimed and count as progress'
assert 'ieee80211_has_qos(wh) && awdlKind != 4 && awdlKind != 3' in cpp, 'The own queue keeps its qid for QoS frames'
assert 'awdlKind == 3 && sc->sc_awdl_probe.ctx.own_agg' in cpp and 'flags &= ~IWX_TX_FLAGS_CMD_RATE' in cpp, 'Firmware rate only on the aggregating own queue'
assert 'be201AwdlTxAggValue, 0' not in v2.replace('be201AwdlTxAggValue, 0, ""','') and 'be201AwdlTxAggValue, 1' in au, 'Aggregation on with automatic start (1.1.54)'
assert own.index('IWX_MAC_PM_POWER_TABLE') < own.index('iwx_tvqm_enable_txq') and own.index('IWX_LINK_CONTEXT_MODIFY_QOS_PARAMS | IWX_LINK_CONTEXT_MODIFY_BEACON_TIMING') < own.index('iwx_tvqm_enable_txq'), 'Fixes go in before the queue is made'
assert 'c->own_held = 0;' in own and 'c->own_redo' in own, 'A changed setting retries a held queue'
assert 'be201AwdlOwnFixValue, 3' in au and 'be201AwdlOwnQueueValue, 1' in au, 'Own queue and both fixes on with automatic start (1.1.54)'
assert au.index('awdlLastBootPanicked()') < au.index('be201AwdlOwnQueueValue, 1'), 'Not after a panic either'
assert 'IWX_AWDL_OWN_QUIET_US' in own and own.index('own_busy_us = now_us') < own.index('const bool moved'), 'Moving waits until the current peer is quiet'
assert own.index('own_recover_fails < IWX_AWDL_OWN_RECOVER_MAX') < own.index('IWX_AWDL_OWN_RECOVER_US') < own.index('c->own_redo = 1;\n                c->own_want = on;'), 'A held queue is rebuilt after a pause, a bounded number of times'
assert 'c->own_recover_fails = 0;' in own and 'c->own_ok == c->own_recover_ok_mark' in own, 'Rebuilds that carry frames keep the budget'
retry = own[own.index('IWX_AWDL_OWN_RETRY_US') - 400:own.index('IWX_AWDL_OWN_RETRY_US') + 200]
assert 'c->own_want && !c->own_active && !c->own_held && !c->own_err' in retry and 'p->peer_added' in retry and 'awdl_ownq_task' in retry, 'A wanted queue never made is tried again (1.1.56)'
assert own.index('IWX_AWDL_OWN_RETRY_US') < own.index('if (!!c->own_want == on && !moved'), 'The retry comes before the no-change return'
rt3=cpp[cpp.index('void ItlIwx::setAwdlSlot'):cpp.index('void ItlIwx::iwx_awdl_phy2_task')]
assert rt3.index('void ItlIwx::setAwdlSlot') < rt3.index('void ItlIwx::setAwdlRadioTest'), 'Slot input sits before the radio switches'
assert 'iwx_awdl_phy2_auto(c->seq_chan5, home)' in rt3 and 'IWX_AWDL_PHY2_AUTO_STABLE_US' in rt3, 'Automatic channel holds before the link moves'
assert 'iwx_awdl_probe_publish(&com)' in rt3[:rt3.index('void ItlIwx::setAwdlRadioTest')], 'Counters are published from the AW tick too (1.1.58)'
assert 'if (iwx_awdl_te_follows(te))' in rt3 and 'iwx_awdl_phy2_follow(cand, c->slot_next5)' in rt3 and 'te == 3 || iwx_awdl_te_follows(te) ?' in rt3, 'Modes 4 and 5: the link follows the own sequence and opens own-slot windows (1.1.60)'
assert 'c->slot_next5 = uint8_t((run >> 8) & 0xff)' in rt3 and 'run | (next5 << 8)' in iface, 'The next 5 GHz slot channel goes to the HAL'
assert 'mode >= 1 && mode <= 8 && (kind == 0 || kind == 2)' in v2 and 'if (!iwx_awdl_te_windows(te) || !ready' in cpp and 'mode | (kind << 8)' in v2, 'Modes 1 to 5 with protection kind 0 or 2 only (1.1.63: kind 1 asserted)'
rt4 = cpp[cpp.index('void ItlIwx::setAwdlRadioTest'):cpp.index('void ItlIwx::iwx_awdl_phy2_task')]
assert rt4.index('te &= 0xff;') < rt4.index('if (phy2 == 1)') and 'now_us >= c->te_end_us && conf < IWX_SESSION_PROTECT_CONF_MAX_ID' in rt4, 'The kind changes only between windows'
assert 'IWX_FW_CTXT_ACTION_ADD, duration, c->te_conf' in rt4 and 'IWX_FW_CTXT_ACTION_REMOVE, 0, c->te_conf' in rt4 and 'IWX_FW_CTXT_ACTION_REMOVE, 0, c->te_conf' in ph2, 'Adds and removes use the latched kind'
assert '!phy2 && !te && (c->phy2_want || c->te_want)' in rt4 and 'c->own_recover_fails = 0;' in rt4, 'Turning the second channel off gives the own queue a fresh start (1.1.62)'
assert 'iwx_awdl_peer_agg(sc, uint32_t(index))' in ph2[ph2.index('++c->phy2_switches;'):] and 'own_refreshes' in ph2, 'Mode 5 refreshes the kept peer after a move'
q6 = ph2[ph2.index('++c->phy2_switches;'):]
assert 'iwx_awdl_te_phy2q(c->te_want) && c->phy2_chan && c->phy2_qid <= 0' in q6 and 'IWX_AWDL_STA_ID)' in q6, 'Mode 6 makes a queue on the AWDL station once on the second channel (1.1.64)'
tx6 = cpp[cpp.index('bool awdlPhy2q = false;'):cpp.index('data->awdl_phy2q = awdlPhy2q;')]
assert 'c->mode == 6 && c->phy2_qid > 0 && (c->solo || (iwx_awdl_te_phy2q(c->te_want) && c->phy2_chan))' in tx6 and tx6.index('IWX_AWDL_TX_MAX_QUEUED') < tx6.index('qid = c->phy2_qid;'), 'Mode 6 frames use it while link 1 is on the second channel, bounded'
assert tx6.index('qid = c->phy2_qid;') < tx6.index('qid = sc->sc_awdl_probe.ctx.own_qid;') and 'awdlPhy2q = false;' in tx6, 'The own queue still wins for its peer'
rm6 = cpp[cpp.index('iwx_awdl_ctx_remove(struct iwx_softc *sc)\n{'):]
assert rm6.index('c->mode == 6 && c->phy2_qid > 0') < rm6.index('struct iwx_sta_remove_cmd cmd = { .sta_id = htole32(IWX_AWDL_STA_ID) }'), 'Its queue goes before the AWDL station'
assert 'sc->sc_awdl_probe.ctx.phy2_qid > 0 &&' in cpp and cpp.count('ctx.phy2_qid = -1;') >= 2, 'Watchdog and resets know it'
# 1.1.66: AWDL on its own without an infrastructure network.
so = cpp[cpp.index('iwx_awdl_solo_add(struct iwx_softc *sc)\n{'):cpp.index('iwx_awdl_ctx_add(struct iwx_softc *sc, struct iwx_node *in)\n{')]
assert so.index('iwx_awdl_solo_idle(sc)') < so.index('iwx_phy_ctxt_update(sc, &sc->sc_phyctxt[1]') < so.index('c->phy2_chan = chan;') < so.index('IWX_FW_CTXT_ACTION_ADD, p->tx.self, true, false') < so.index('IWX_FW_CTXT_ACTION_ADD, 0, 0)') < so.index('IWX_LINK_CONTEXT_MODIFY_ACTIVE | IWX_LINK_CONTEXT_MODIFY_RATES_INFO, 1') < so.index('IWX_STA_CONFIG_CMD') < so.index('IWX_AWDL_STA_ID);') < so.index('IWX_FW_CTXT_ACTION_MODIFY, p->tx.self, true, true'), 'Solo: second PHY on the AWDL channel, MAC, link, active, station, its queue, association'
assert 'c->solo_failed = 1;' in so and 'tx.tripped = 1' not in so and 'iwx_awdl_ctx_remove(sc);' in so, 'A solo failure stops solo for the boot without tripping AWDL'
assert '!iwx_awdl_solo_idle(sc)) { iwx_awdl_ctx_remove(sc);' in so, 'Leaving idle mid-way removes what was made'
au = cpp[cpp.index('iwx_mld_auth(struct iwx_softc *sc, struct iwx_node *in)\n{'):]
assert au.index('if (sc->sc_awdl_probe.ctx.solo) {') < au.index('iwx_awdl_ctx_remove(sc);') < au.index('IWX_MLD_STEP_MAC_ADD'), 'A join removes solo before the station MAC'
idle = cpp[cpp.index('static bool iwx_awdl_solo_idle'):cpp.index('void ItlIwx::setAwdlSlot')]
assert 'IEEE80211_S_INIT' in idle and 'IEEE80211_S_SCAN' in idle and 'IWX_FLAG_STA_ACTIVE' in idle, 'Idle: no association and none starting'
sl = cpp[cpp.index('void ItlIwx::setAwdlSlot'):cpp.index('void ItlIwx::setAwdlRadioTest')]
assert 'IWX_AWDL_SOLO_IDLE_US' in sl and '!c->solo_failed' in sl and 'awdl_solo_task' in sl, 'The AW tick starts solo after the idle time'
rtx = cpp[cpp.index('void ItlIwx::setAwdlRadioTest'):cpp.index('void ItlIwx::iwx_awdl_phy2_task')]
assert rtx.index('if (c->solo) {') < rtx.index('if (phy2 == 1)'), 'No second channel moves while solo'
assert 'sc->sc_awdl_probe.ctx.solo && sc->sc_awdl_probe.ctx.phy2_qid > 0 && !memcmp(wh->i_addr3, iwx_awdl_bssid, 6)' in cpp, 'Solo AWDL frames pass the no-AP-queue drop'
assert 'awdlSolo && min_ridx < iwx_rval2ridx(12)' in cpp and '!awdlSolo &&' in cpp, 'Solo AWDL frames never use CCK or the AP-width fixed rates'
lk = cpp[cpp.index('iwx_awdl_ctx_link_cmd(struct iwx_softc *sc, struct iwx_node *in, uint32_t action,'):cpp.index('void ItlIwx::iwx_awdl_solo_task')]
assert 'sc->sc_awdl_probe.ctx.solo ? sc->sc_awdl_probe.ctx.phy2_chan != 0 : in && in->in_phyctxt' in lk and 'cmd.bi = htole32(100);' in lk, 'Solo link: second PHY, fixed rates, beacon timing and EDCA'
rm = cpp[cpp.index('iwx_awdl_ctx_remove(struct iwx_softc *sc)\n{'):]
rm = rm[:rm.index('\n}\n')]
assert rm.index('IWX_FW_CTXT_ACTION_REMOVE, 0, 0)') < rm.index('c->phy2_chan = 0;') and rm.index('IWX_FW_CTXT_ACTION_REMOVE, nullptr') < rm.index('c->solo = 0;'), 'The link keeps naming its real PHY context until it is removed'
assert 'p->ctx.solo ? !iwx_awdl_solo_idle(sc)' in cpp and '(ic->ic_state == IEEE80211_S_RUN || sc->sc_awdl_probe.ctx.solo)' in cpp, 'Peers and receive work while solo'
m5 = ph2[ph2.index('iwx_awdl_te_keeps_own(c->te_want) && c->own_active'):ph2.index('IWX_LINK_CONTEXT_MODIFY_ACTIVE, 0')]
assert 'iwx_flush_sta_tids(sc, c->own_sta, 0xffff)' in m5 and 'own_kept_moves' in m5 and m5.index('own_kept_moves') < m5.index('iwx_awdl_own_release(sc)'), 'Mode 5 flushes and keeps the own queue; other modes still release it (1.1.61)'
assert 'seq5 |= c5 << 8' in iface and 'c5 == (seq5 & 0xff)' in iface, 'Two different 5 GHz channels go to the HAL'
assert 'te == 3 || iwx_awdl_te_follows(te) ?' in rt3 and 'iwx_awdl_te_own_due' in rt3 and 'c->slot_run = 0;' in rt3 and 'c->te_end_us' in rt3, 'Mode 3: own slots, one window per slot start'
aw=iface[iface.index('void AirportItlwmAWDLInterface::awTimerFired'):]
aw=aw[:aw.index('\n}\n')]
assert aw.index('const uint32_t slot =') < aw.index('setAWDLSlot') < aw.index('setAWDLRadioTest'), 'Slot first, then the switches, on every tick'
assert 'self->awChannels[(slot + 15) % 16] != chan' in aw, 'A run starts where the previous slot had another channel'
assert 'iwx_add_task(sc, systq, &sc->awdl_umi_task)' in cpp and 'controller->awdlUmiDone' in cpp[cpp.index('void ItlIwx::iwx_awdl_umi_task'):cpp.index('void ItlIwx::sendAwdlUmi')], 'Results leave from a task: the status path can send again'
assert 'data->awdl_umi = 0;' in cpp and 'if (txd->awdl_umi)' in cpp, 'Only a frame marked at queueing reports a result'
st=v2[v2.index('void AirportItlwm::stopAWDLInterface'):]
assert st.index('lowLatency->terminate') < st.index('interface->terminate'), 'llw0 stops before the parent whose peer manager it borrows'
print('awdl block ack source checks passed')
