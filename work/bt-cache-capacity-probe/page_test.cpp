#include "PrivacyProbePatch.hpp"
#include <cassert>
#include <fstream>
#include <vector>
#include <cstdio>
static std::vector<uint8_t> read(const char *p){std::ifstream f(p,std::ios::binary);assert(f);return std::vector<uint8_t>((std::istreambuf_iterator<char>(f)),{});}
int main(int argc,char **argv){assert(argc==7);uint64_t off[]={1806336,10342400,0x6e7000};
 for(unsigned k=0;k<3;k++){auto original=read(argv[1+k*2]),expected=read(argv[2+k*2]),p=original;
  assert(be201PrivacyApply(p.data(),4096,off[k])==(1U<<k)&&p==expected);
  assert(be201PrivacyApply(p.data(),4096,off[k])==(128U|(1U<<k))&&p==expected);
  for(size_t i=0;i<4096;i++){p=original;p[i]^=1;auto copy=p;assert(!be201PrivacyApply(p.data(),4096,off[k])&&p==copy);}
  p=original;assert(!be201PrivacyApply(p.data(),4096,0)&&p==original);
 }
 puts("PASS: three page fingerprints, exact offsets, idempotence, 12288 single-byte mismatch rejections (ASan/UBSan).");
}
