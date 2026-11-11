// Numeric, read-only controller privacy capability observer. No addresses/keys.
// Command bit positions: BlueZ 5.79 monitor/packet.c (275..282).
// LL Privacy bit: Linux v6.12 include/net/bluetooth/hci.h (feature byte 0, 0x40).
#pragma once
#include "LECommandProbe.hpp"
namespace be201privacycap {
struct Stats {
 uint64_t sequence=0,commandsSeen=0,featuresSeen=0,capacitySeen=0;
 uint64_t commandMask=0,llPrivacy=0,capacity=0;
 uint64_t capacityRequests=0,capacityCompletions=0,capacityStatus=0;
 uint64_t malformed=0,controllerErrors=0,resetCount=0;
};
inline void clear(Stats &s) {
 be201probe::put(s.commandsSeen,0);be201probe::put(s.featuresSeen,0);be201probe::put(s.capacitySeen,0);
 be201probe::put(s.commandMask,0);be201probe::put(s.llPrivacy,0);be201probe::put(s.capacity,0);
 be201probe::increment(s.resetCount);be201probe::increment(s.sequence);
}
inline void submitted(Stats &s,const uint8_t *p,size_t n) {
 if(p&&n>=3&&p[0]==0x2a&&p[1]==0x20&&p[2]==0) {
  be201probe::increment(s.capacityRequests);be201probe::increment(s.sequence);
 }
}
inline size_t required(const uint8_t *p,size_t prefix,size_t total) {
 if(!p||prefix<6||total<6||p[0]!=0x0e)return 0;
 unsigned op=p[3]|unsigned(p[4])<<8;
 size_t n=op==0x1002?70:op==0x2003?14:op==0x202a?7:op==0x0c03?6:0;
 // Failed commands can legitimately omit the success-only return parameters.
 return n && p[5]!=0 && total==6 ? 6 : n;
}
inline void event(Stats &s,const uint8_t *p,size_t count,size_t total) {
 size_t n=required(p,count,total);if(!n)return;
 be201probe::increment(s.sequence);
 if(count!=n || total!=n || p[1]!=n-2) {be201probe::increment(s.malformed);return;}
 if((p[3]|unsigned(p[4])<<8)==0x202a) {
  be201probe::increment(s.capacityCompletions);be201probe::put(s.capacityStatus,p[5]);
 }
 if(p[5]){be201probe::increment(s.controllerErrors);return;}
 unsigned op=p[3]|unsigned(p[4])<<8;
 if(op==0x0c03){clear(s);return;}
 if(op==0x1002){
  unsigned mask=(p[6+34]>>3)|((p[6+35]&7)<<5);
  be201probe::put(s.commandMask,mask);be201probe::put(s.commandsSeen,1);
 } else if(op==0x2003){be201probe::put(s.llPrivacy,(p[6]&0x40)!=0);be201probe::put(s.featuresSeen,1);}
 else if(op==0x202a){be201probe::put(s.capacity,p[6]);be201probe::put(s.capacitySeen,1);}
}
}
