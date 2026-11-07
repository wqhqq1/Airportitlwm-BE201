#include "ResolvingListCommand.hpp"
#include <cassert>
#include <cstring>
#include <cstdio>
#include <random>
using namespace be201privacy;
int main(){
 uint8_t address[6]={1,2,3,4,5,6},peer[16],local[16];
 for(unsigned i=0;i<16;i++){peer[i]=i;local[i]=0xa0+i;}
 ResolvingListCommand c;assert(c.add(0,{address,6},{peer,16},{local,16}));assert(c.size()==42);
 assert(c.data()[0]==0x27 && c.data()[1]==0x20 && c.data()[2]==39 && c.data()[3]==0);
 assert(!memcmp(c.data()+4,address,6)&&!memcmp(c.data()+10,peer,16)&&!memcmp(c.data()+26,local,16));
 for(unsigned n=0;n<35;n++)if(n!=16){assert(!c.add(0,{address,6},{peer,n},{local,16}));assert(c.size()==0);for(unsigned i=0;i<42;i++)assert(c.data()[i]==0);}
 assert(!c.add(0,{nullptr,6},{peer,16},{local,16}));assert(!c.add(0,{address,7},{peer,16},{local,16}));
 assert(!c.add(1,{address,6},{peer,16},{local,16}));address[5]=0xc6;assert(c.add(1,{address,6},{peer,16},{local,16}));
 assert(c.remove(1,{address,6})&&c.size()==10&&c.data()[0]==0x28);for(unsigned i=10;i<42;i++)assert(c.data()[i]==0);
 c.resolution(true);assert(c.size()==4&&c.data()[0]==0x2d&&c.data()[3]==1);c.resolution(false);assert(c.data()[3]==0);
 c.readCapacity();assert(c.size()==3&&c.data()[0]==0x2a);c.clear();for(unsigned i=0;i<42;i++)assert(c.data()[i]==0);
 std::mt19937 rng(201);for(unsigned n=0;n<100000;n++){
  for(auto &v:address)v=rng();for(auto &v:peer)v=rng();for(auto &v:local)v=rng();
  uint8_t p[16],l[16],a[6];memcpy(p,peer,16);memcpy(l,local,16);memcpy(a,address,6);
  const unsigned type=rng()%4;bool ok=c.add(type,{address,6},{peer,16},{local,16});
  if(ok){assert(type<2&&c.size()==42);assert(!memcmp(c.data()+10,peer,16));}
  assert(!memcmp(p,peer,16)&&!memcmp(l,local,16)&&!memcmp(a,address,6));c.clear();for(unsigned i=0;i<42;i++)assert(c.data()[i]==0);
 }
 puts("PASS: standard 0x2027/28/2A/2D wire ABI, 39-byte add payload, public/static identity validation, key field separation, zeroization and immutable input; 100000 cases (ASan/UBSan; offline only).");
}
