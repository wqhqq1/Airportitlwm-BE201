"""Compile the production request handler with fake properties and boot flags."""
from pathlib import Path
import re,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'AirportItlwm/AirportItlwmSkywalkInterface.cpp').read_text()
def body(text,signature):
 start=text.index(signature);brace=text.index('{',start);depth=1;end=brace+1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
method=body(s,'IOReturn AirportItlwmSkywalkInterface::unsupportedContinuityRequest(unsigned id)')
flag=body((root/'include/ItlStartupDiagnostics.hpp').read_text(),'inline bool ItlDiagnosticFlag(const char *name)')
harness=r'''
#include <cstdint>
#include <cstring>
#include <cassert>
#include <map>
#include <string>
#include <cstdio>
#define AIRPORT_WCL 1
using IOReturn=int;
constexpr IOReturn kIOReturnUnsupported=0x1234;
std::map<std::string,int> flags;
bool PE_parse_boot_argn(const char *name,void *data,int length) {
 assert(length==sizeof(int));auto i=flags.find(name);if(i==flags.end())return false;
 memcpy(data,&i->second,sizeof(int));return true;
}
struct Controller { std::map<std::string,uint32_t> values;
 void setProperty(const char *key,uint32_t count,unsigned bits) { assert(bits==32);values[key]=count; }
};
struct AirportItlwmSkywalkInterface {
 Controller *instance=nullptr;
 uint32_t be201ContinuityRequests[7]={};
 IOReturn unsupportedContinuityRequest(unsigned);
};
'''+flag+'\n'+method+r'''
int main() {
 Controller controller;AirportItlwmSkywalkInterface api;api.instance=&controller;
 for(unsigned i=0;i<10;++i)assert(api.unsupportedContinuityRequest(i)==kIOReturnUnsupported);
 assert(controller.values.empty());
 flags["be201_awdl_diag"]=1;
 for(unsigned i=0;i<7;++i)assert(api.unsupportedContinuityRequest(i)==kIOReturnUnsupported);
 assert(controller.values.size()==1 && api.be201ContinuityRequests[6]==1);
 flags["be201_awdl_diag"]=0;flags["be201_ranging_diag"]=1;
 for(unsigned i=0;i<7;++i)assert(api.unsupportedContinuityRequest(i)==kIOReturnUnsupported);
 assert(controller.values.size()==7 && api.be201ContinuityRequests[6]==1);
 for(unsigned i=0;i<6;++i)assert(api.be201ContinuityRequests[i]==1);
 api.instance=nullptr;
 for(unsigned i=0;i<7;++i)assert(api.unsupportedContinuityRequest(i)==kIOReturnUnsupported);
 assert(controller.values.size()==7);
 puts("PASS: production unsupported handler, default-off/no-controller cases, independent AWDL/ranging flags and all seven request IDs; no success/capability fabricated.");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.cpp').write_text(harness)
 subprocess.run(['clang++','-std=c++14','-fsanitize=address,undefined','-Wall','-Wextra','-Werror',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
