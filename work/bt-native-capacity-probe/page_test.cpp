#include "PrivacyProbePatch.hpp"
#include <cassert>
#include <fstream>
#include <vector>
#include <cstdio>
#include <cstring>
static std::vector<uint8_t> read(const char *p){std::ifstream f(p,std::ios::binary);assert(f);return std::vector<uint8_t>((std::istreambuf_iterator<char>(f)),{});}
int main(int argc,char **argv){
 assert(argc==5);auto stub=read(argv[1]),stubPatched=read(argv[2]),payload=read(argv[3]),payloadPatched=read(argv[4]);
 auto a=stub,b=payload;assert(be201PrivacyApply(a.data(),a.size(),1806336)==1&&a==stubPatched);
 assert(be201PrivacyApply(b.data(),b.size(),10342400)==2&&b==payloadPatched);
 assert(be201PrivacyApply(a.data(),a.size(),1806336)==3&&be201PrivacyApply(b.data(),b.size(),10342400)==4);
 for(size_t i=0;i<4096;i++){
  a=stub;a[i]^=1;auto copy=a;assert(be201PrivacyApply(a.data(),a.size(),1806336)==0&&a==copy);
  b=payload;b[i]^=1;copy=b;assert(be201PrivacyApply(b.data(),b.size(),10342400)==0&&b==copy);
 }
 a=stub;b=payload;assert(!be201PrivacyApply(a.data(),4096,0)&&a==stub);assert(!be201PrivacyApply(b.data(),4096,1806336)&&b==payload);
 for(size_t n=0;n<4096;n++){assert(!be201PrivacyApply(a.data(),n,1806336)&&a==stub);}
 assert(!be201PrivacyApply(nullptr,4096,1806336));
 puts("PASS: exact page fingerprints/offsets, 8192 individual-byte rejection cases, truncated/invalid inputs, idempotence and only two permitted page diffs (ASan/UBSan).");
}
