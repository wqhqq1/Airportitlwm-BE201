#pragma once
#include <libkern/c++/OSData.h>
#include <libkern/libkern.h>
struct FwDesc { const char *name; const unsigned char *var; const long int size; };
extern const FwDesc fwList[]; extern const int fwNumber;
static inline OSData *getFWDescByName(const char *name) {
 for(int i=0;i<fwNumber;i++)if(!strcmp(name,fwList[i].name))return OSData::withBytes(fwList[i].var,(unsigned int)fwList[i].size);
 return NULL;
}
