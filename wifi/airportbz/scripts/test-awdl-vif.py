#!/usr/bin/env python3
"""Exercise actual registration lifecycle with allocation failures. No native runtime emulation claim."""
from pathlib import Path
import json,re,subprocess,tempfile
R=Path(__file__).resolve().parents[1]
meta=json.loads((R/'tests/abi/sequoia-24G824-awdl.json').read_text())
h=(R/'AirportItlwm/AirportItlwmAWDLInterface.hpp').read_text()
s=(R/'AirportItlwm/AirportItlwmAWDLInterface.cpp').read_text()
f=(R/'AirportItlwm/BE201SkywalkFactories.hpp').read_text()
# Keep actual functions/class, replace only kernel headers/meta constructor declarations for host execution.
h='\n'.join(l for l in h.splitlines() if not l.startswith('#include') and not l.startswith('#pragma') and 'OSDeclareDefaultStructors' not in l).replace(' override','').replace('private:','public:')
f='\n'.join(l for l in f.splitlines() if not l.startswith('#pragma'))
s=re.sub(r'^#include.*\n','',s,flags=re.M)
s=re.sub(r'^OSDefineMetaClassAndStructors.*\n','',s,flags=re.M)
s=re.sub(r'^#(?:ifn?def|define|endif).*\n','',s,flags=re.M)
types='\n'.join('struct '+t+' { uint32_t version=0, unk1=0, enabled=0, state=0; };' for t in sorted({m['type'] for m in meta['methods']}))
pre=r'''
#include "iwx_awdl_rx.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <vector>
#include <string>
#include <cstdio>
#include <map>
#include <functional>
#include <algorithm>
#include <type_traits>
using UInt=unsigned;using UInt16=uint16_t;using UInt32=uint32_t;using IOOptionBits=unsigned;using IOReturn=int;using SInt32=int;
constexpr int kIOReturnSuccess=0,kIOReturnUnsupported=-1,kIOReturnBadArgument=-2,kIOReturnNotReady=-3,kIOReturnBusy=-4,kIOReturnNoMemory=-5,kIOReturnError=-6,THREAD_UNINT=0;
constexpr unsigned APPLE80211_ADDR_LEN=6;
struct apple80211_virt_if_create_data {uint32_t version=0;uint8_t mac[6]={2,1,2,3,4,5};uint16_t unk1=0;uint32_t role=6;uint8_t bsd_name[16]={};};
size_t strlcpy(char *d,const char *s,size_t n){auto z=strlen(s);if(n){auto k=std::min(z,n-1);memcpy(d,s,k);d[k]=0;}return z;}
constexpr int APPLE80211_VERSION=1, APPLE80211_VIF_AWDL=6,kIOServiceRequired=1,kIOServiceSynchronous=2;
void clock_get_uptime(uint64_t *t){*t=5000000;}void absolutetime_to_nanoseconds(uint64_t a,uint64_t *n){*n=a;}uint64_t mach_absolute_time(){return 5000000;}
class IOSkywalkPacket;
struct MockPacket {uint8_t data[2048];unsigned offset=0;unsigned length=0;bool prepared=true;bool stamped=false;};
inline MockPacket *mp(const IOSkywalkPacket *p){return reinterpret_cast<MockPacket*>(const_cast<IOSkywalkPacket*>(p));}
unsigned txEnabled=0,txCompEnabled=0,rxCompEnabled=0,txDeq=0,txCompleted=0,rxEnqueued=0,poolLive=0;int poolResult=0,rxEnqueueResult=0,prepareResult=0,setLengthResult=0;std::vector<MockPacket*> rxSeen;
constexpr unsigned IFF_RUNNING=0x40;constexpr unsigned IFF_UP=0x1;unsigned ifRunning=0,ifFlags=0,ifIoctls=0;bool ifIoctlRuns=true;using ifnet_t=void*;int ifnet_set_flags(ifnet_t,unsigned v,unsigned m){ifRunning=v;ifFlags=(ifFlags&~m)|(v&m);return 0;}unsigned ifnet_flags(ifnet_t){return ifFlags;}struct ifreq{char ifr_name[16];short ifr_flags;};constexpr unsigned long SIOCSIFFLAGS=0x80206910;int ifnet_ioctl(ifnet_t,int,unsigned long c,void *a){assert(c==SIOCSIFFLAGS&&a&&(ifFlags&IFF_UP)&&(static_cast<ifreq*>(a)->ifr_flags&IFF_UP));++ifIoctls;if(ifIoctlRuns)ifFlags|=IFF_RUNNING;return 0;}extern "C" int be201UpdateInterfaceDataStats(void*,void*) __asm__("__ZN23IO80211SkywalkInterface24updateInterfaceDataStatsEP36apple80211_data_path_interface_stats");unsigned statsCalls=0,statsTx=0,statsRx=0;int be201UpdateInterfaceDataStats(void*,void*b){++statsCalls;memcpy(&statsTx,(char*)b+8,4);memcpy(&statsRx,(char*)b+0x18,4);return 0;}using ifnet_offload_t=unsigned;unsigned offloadCalls=0;int ifnet_set_offload(ifnet_t,ifnet_offload_t v){assert(!v);++offloadCalls;return 0;}
enum IO80211LinkState { kIO80211NetworkLinkUndefined,kIO80211NetworkLinkDown,kIO80211NetworkLinkUp };
struct ether_addr { uint8_t octet[6]; };
unsigned lastPoolFlags=99;
int failAt=0, step=0, blocks=0, pools=0, queuesLive=0, openControllers=0;
std::vector<std::string> sequence;
bool fail(){return ++step==failAt;}
void *IOMalloc(size_t n){ if(fail())return nullptr;auto p=std::malloc(n);++blocks;return p; }
void releaseBlock(void *p){if(p){--blocks;std::free(p);}}
void IOLog(const char*,...){}
void IOSleep(unsigned){}
class OSObject {public: int rc=1; virtual ~OSObject()=default; virtual void free(){}; void retain(){++rc;} void release(){assert(rc>0);if(--rc==0){free();delete this;}} };
int inGate=0, loopAdds=0;
std::vector<std::function<void()>> pendingTerminations;
void drainTerminations(){auto w=pendingTerminations;pendingTerminations.clear();for(auto &f:w)f();}
class IOEventSource:public OSObject {};
class IOTimerEventSource;
using IOTimerAction=void(*)(OSObject*,IOTimerEventSource*);
class IOWorkLoop:public OSObject {public: bool inGate(){return ::inGate != 0;} std::vector<IOEventSource*> sources;
 int addEventSource(IOEventSource *e){if(fail())return -6;sources.push_back(e);++loopAdds;return 0;}
 int removeEventSource(IOEventSource *e){auto i=std::find(sources.begin(),sources.end(),e);assert(i!=sources.end());sources.erase(i);sequence.push_back("queue-remove");return 0;}
};
IOWorkLoop *testLoop=nullptr;
class IOTimerEventSource:public IOEventSource {public:OSObject *owner=nullptr;IOTimerAction action=nullptr;bool armed=false;unsigned arms=0;
 static IOTimerEventSource *timerEventSource(OSObject *o,IOTimerAction a){if(fail())return nullptr;auto t=new IOTimerEventSource;t->owner=o;t->action=a;return t;}
 int setTimeoutMS(unsigned){armed=true;++arms;return 0;}int setTimeoutUS(unsigned){armed=true;++arms;return 0;}void cancelTimeout(){armed=false;}
 void fire(){assert(armed);armed=false;action(owner,this);}
};
struct sysctl_oid {};
int oidRegistered=0;
void sysctl_register_oid(sysctl_oid*){++oidRegistered;}
void sysctl_unregister_oid(sysctl_oid*){--oidRegistered;}
#define SYSCTL_DECL(x)
#define SYSCTL_INT(parent,nbr,name,access,ptr,val,descr) sysctl_oid sysctl_##parent##_##name
class OSNumber:public OSObject {public:unsigned value=0;unsigned unsigned32BitValue(){return value;}};
class IOService:public OSObject { public: std::map<std::string,unsigned> properties;
 void setProperty(const char*n,unsigned v,int){properties[n]=v;}void setProperty(const char*n,bool v){properties[n]=v;}void setProperty(const char*n,const char*v){lastStep=v;strings[n]=v;}std::string lastStep;std::map<std::string,std::string> strings;
 std::map<std::string,unsigned> blobs;std::vector<uint16_t> requestLogCopy;void setProperty(const char*n,const void*p,unsigned len){if(strcmp(n,"ItlwmAwdlRequestLog")){blobs[n]=len;return;}assert(len%2==0);auto q=static_cast<const uint16_t*>(p);requestLogCopy.assign(q,q+len/2);}
 OSObject *getProperty(const char*n){static OSNumber v;if(!properties.count(n))return nullptr;v.value=properties[n];return &v;}
 int published=0;void registerService(){sequence.push_back("publish");++published;}
};
#define OSDynamicCast(T,x) dynamic_cast<T*>(x)
class IO80211VirtualInterface;
class IO80211SkywalkInterface;
class IO80211Controller:public IOService {public: unsigned capabilityLoads=0;void loadCardCapabilities(IO80211SkywalkInterface*){++capabilityLoads;} IO80211VirtualInterface *awdlPointer=nullptr;IOWorkLoop *getWorkLoop(){return testLoop;}
 IO80211VirtualInterface *getAwdlInterface(){return awdlPointer;} void setAwdlInterface(IO80211VirtualInterface *p){awdlPointer=p;}};
class AirportItlwmAWDLInterface;
class AirportItlwmLowLatencyInterface;
static const void *const gIODTPlane=nullptr;struct IORegistryEntry{static IORegistryEntry *fromPath(const char*,const void*){return nullptr;}OSObject *copyProperty(const char*){return nullptr;}void release(){}};
class AirportItlwm:public IO80211Controller {public:
 IO80211SkywalkInterface *fNetIf=reinterpret_cast<IO80211SkywalkInterface*>(8);uint8_t capabilityCopy[0x18]={};const uint8_t *nativeCapabilityCache() const {return capabilityCopy;}void reloadAWDLCapabilities();
 AirportItlwmAWDLInterface *awdlInterface=nullptr;bool awdlCreating=false,awdlStopping=false,awdlArmRegistered=false,awdlFailed=false;uint32_t awdlUnarmedRefusals=0,awdlAttempts=0,awdlLateAdopted=0;
 void registerAWDLArmControl();static bool awdlVifCapabilityArmed();static uint32_t awdlVifPoolFlags();static bool awdlVifAcceptSets();static bool awdlVifLinkAllowed();static bool awdlVifAwAllowed();
 static bool awdlUmiOn();static bool awdlLlwOn();void sendAWDLUmi(const uint8_t*p,const uint8_t*t,size_t n){memcpy(umiPeer,p,6);umiTlvs=t;umiLen=n;++umiSends;}uint8_t umiPeer[6]={};const uint8_t*umiTlvs=nullptr;size_t umiLen=0;unsigned umiSends=0;void awdlUmiDone(const uint8_t*,bool);
 IOReturn createLowLatencyInterface(AirportItlwmAWDLInterface*,const ether_addr&,char*,size_t);static IOReturn createLowLatencyInterfaceGated(OSObject*,void*,void*,void*,void*);AirportItlwmLowLatencyInterface *llwInterface=nullptr;bool llwCreating=false,llwFailed=false;
 void awdlTxRoom();void setAWDLPause(bool){}static bool awdlPauseWanted();void awdlPeerCache(const uint8_t*,uint32_t){}void awdlPeerCacheDone(const uint8_t*,bool);static bool awdlCacheOn();static bool awdlCacheRtgOn();void startAWDLAuto();static bool awdlLastBootPanicked();static bool awdlOwnQueueWanted();static bool awdlTxAggWanted();static uint32_t awdlOwnFixWanted();void setAWDLOwnQueue(bool,bool,uint32_t){} static void awdlRadioTest(bool*,uint32_t*,uint32_t*,bool*);void setAWDLSlot(uint32_t,uint32_t,uint32_t){}void setAWDLSequence(const uint8_t*,uint32_t){}void setAWDLRadioTest(bool,uint32_t,uint32_t,bool){}static uint32_t awdlRocWanted();uint32_t rocSet=0;void setAWDLRoc(uint32_t v){rocSet=v;} bool amsduReadyMock=false;unsigned amsduCalls=0,amsduLast=0;IOReturn amsduResult=0;bool awdlAmsduReady(const uint8_t*){return amsduReadyMock;}size_t awdlAmsduMaxBytes(){return 7900;}IOReturn sendAWDLAmsdu(const uint8_t*const*,const size_t*,unsigned n){++amsduCalls;amsduLast=n;return amsduResult;} static bool awdlVifRadioAllowed();static bool awdlVifRxAllowed();static bool awdlVifTxAllowed();static bool awdlVifDataAllowed();IOReturn sendAWDLData(const uint8_t*,size_t);IOReturn setAWDLTemplate(bool,const uint8_t*,size_t);IOReturn enableAWDLTransmit();
 void inputAWDLActionFrame(const uint8_t *,size_t,uint8_t,int,uint32_t);
 IOReturn requestAWDLMonitor(const ether_addr &);
 bool awdlSyncNext(uint16_t*,uint32_t*){return false;}
 struct MonitorHAL {unsigned templates=0,enables=0;size_t lastTemplate=0;bool lastMif=false;IOReturn setAwdlNativeTemplate(bool m,const uint8_t*,size_t n){++templates;lastMif=m;lastTemplate=n;return 0;}IOReturn enableAwdlNativeTx(){++enables;return 0;}unsigned sent=0;size_t lastSent=0;int sendResult=0;IOReturn sendAwdlData(const uint8_t*,size_t n){++sent;lastSent=n;return sendResult;}unsigned calls=0;uint8_t last[6]={};IOReturn requestAwdlMonitor(const uint8_t *a){++calls;memcpy(last,a,6);return kIOReturnSuccess;}} mockHAL;
 MonitorHAL *fHalService=&mockHAL;
 IOReturn createAWDLInterface(apple80211_virt_if_create_data*);
 static IOReturn createAWDLInterfaceGated(OSObject*,void*,void*,void*,void*);
 static IOReturn takeAWDLInterfaceGated(OSObject*,void*,void*,void*,void*);
 void stopAWDLInterface();
};
class Gate {public:OSObject *owner;unsigned wakes=0;
 int runAction(int (*fn)(OSObject*,void*,void*,void*,void*),void *arg){++inGate;int r=fn(owner,arg,nullptr,nullptr,nullptr);--inGate;return r;}
 void commandWakeup(void*){++wakes;}
 std::function<void()> whileSleeping;unsigned sleeps=0;
 // A deadline sleep gives up the gate; the BSD client attaches from another thread meanwhile.
 void commandSleep(void*,uint64_t,int){++sleeps;int held=inGate;inGate=0;if(whileSleeping)whileSleeping();inGate=held;}
 void commandSleep(void*,int){assert(false&&"Unexpected synchronous mock wait");}
};
Gate *_fCommandGate=nullptr;
using AbsoluteTime=uint64_t;constexpr int kMillisecondScale=1000;
void clock_interval_to_deadline(unsigned,unsigned,AbsoluteTime *d){*d=0;}
bool ItlDiagnosticFlag(const char*){return true;}
bool ItlDefaultOnFlag(const char*,bool=true){return true;}
bool ItlAwdlFlag(const char*){return true;}
bool ItlAwdlLayoutVerified(){return true;}
std::function<void()> duringRegister;
class IOSkywalkPacketQueue:public IOEventSource {public: IOSkywalkPacketQueue(){++queuesLive;} void free(){--queuesLive;sequence.push_back("queue-release");}};
class IOSkywalkPacketBufferPool:public OSObject {public:
 struct PoolOptions {uint32_t packetCount=0,bufferCount=0,bufferSize=0,maxBuffersPerPacket=0,memorySegmentSize=0,poolFlags=0;uint64_t pad=0;};
 static IOSkywalkPacketBufferPool *withName(const char*,OSObject*,unsigned type,const PoolOptions *po){assert(type==1&&po->packetCount==64&&po->bufferSize==2048&&po->maxBuffersPerPacket==1);lastPoolFlags=po->poolFlags;if(fail())return nullptr;++pools;return new IOSkywalkPacketBufferPool;}
 void free(){--pools;sequence.push_back("pool-release");}
};
class IOSkywalkNetworkInterface:public IOService {public:
 struct RegistrationInfo {uint8_t bytes[0x130];};
 struct ExpansionData {RegistrationInfo *fRegistrationInfo=nullptr;void *fBSDInterface=nullptr;};
 ExpansionData *mExpansionData=nullptr;
};
class IOSkywalkEthernetInterface:public IOSkywalkNetworkInterface {public:
 struct RegistrationInfo {uint8_t bytes[0x130];};
 struct ExpansionData {RegistrationInfo *fRegistrationInfo=nullptr;void *fBSDInterface=nullptr;};
 ExpansionData *mExpansionData2=nullptr;
};
struct ifnet_init_eparams{uint32_t ver,len,flags,reserved;const void *uniqueid;uint32_t uniqueid_len;uint8_t rest[200];};struct sockaddr_dl;
class IO80211SkywalkInterface:public IOSkywalkEthernetInterface {public: virtual UInt32 getFeatureFlags(){return 0x10000;} virtual int initBSDInterfaceParameters(ifnet_init_eparams *p,sockaddr_dl**){static const uint8_t mac[6]={1,2,3,4,5,6};p->uniqueid=mac;p->uniqueid_len=6;return 0;}
 virtual const char *getBSDNamePrefix(){return "en";}
 virtual bool setLinkState(IO80211LinkState,unsigned,bool,unsigned){return true;}
};
int bufferFailure=0,bufferGets=0,bufferReturns=0,bufferSubmits=0;bool poolPresent=true;std::function<void()> duringNativeInput;
class IO80211Buffer {public: size_t length=0;uint8_t data[2048]={};
 unsigned long getCapacity()const{return bufferFailure==2?0:sizeof(data);}
 unsigned long writeBytes(unsigned long off,const void *p,unsigned long n){assert(off+n<=sizeof(data));if(bufferFailure==3)return 0;memcpy(data+off,p,n);return n;}
 void setLength(unsigned long n){length=n;}void returnBuffer(){++bufferReturns;}
} testBuffer;
class IO80211BufferPool {public:IO80211Buffer *getBuffer(){++bufferGets;return bufferFailure==1?nullptr:&testBuffer;}} testBufferPool;
class IO80211VirtualInterface;extern IO80211VirtualInterface *lastCreated,*lastLlw;
class IO80211VirtualInterface:public IO80211SkywalkInterface {public: virtual UInt32 getFeatureFlags() override {return IO80211SkywalkInterface::getFeatureFlags()|0x10000000;}
 IO80211BufferPool *getMgmtFramePool(){return poolPresent?&testBufferPool:nullptr;}
 void bpfTapInput(IO80211Buffer *b,unsigned d,void *h,unsigned long len){assert(b==&testBuffer&&d==12&&h&&len==72);++bufferSubmits;if(duringNativeInput)duringNativeInput();}
 bool nativeStarted=false,nativeAttached=false,nativeOpen=false;ether_addr mockMac={};IO80211Controller *nativeController=nullptr;bool bsdAttached=false;
 virtual IO80211Controller *getController(){return nullptr;}
 bool hasNativeVirtualState() const {return nativeOpen;}
 unsigned mockRole=0,mockId=0;bool mockLowLatency=false;IO80211VirtualInterface *mockParent=nullptr,*mockCompanion=nullptr;unsigned mockCompanionId=0;
 void setLowLatencyEnabled(bool b){mockLowLatency=b;}void setParentInterface(IO80211VirtualInterface *p){mockParent=p;}void setCompanionLowLatencySkywalkInterface(IO80211SkywalkInterface *p){mockCompanion=reinterpret_cast<IO80211VirtualInterface*>(p);}void setCompanionInterfaceId(unsigned i){mockCompanionId=i;}unsigned getInterfaceId(){return mockId;}
 bool init(IO80211Controller *c,ether_addr *m,unsigned role,const char *name){assert((role==6&&!strcmp(name,"awdl"))||(role==2&&!strcmp(name,"llw")));mockRole=role;mockMac=*m;nativeController=c;if(role==6)lastCreated=this;else lastLlw=this;if(fail())return false;mExpansionData=new IOSkywalkNetworkInterface::ExpansionData;mExpansionData2=new IOSkywalkEthernetInterface::ExpansionData;++openControllers;nativeOpen=true;return !fail();}
 virtual bool attach(IOService*){return nativeAttached=!fail();}
 virtual void detach(IOService*){nativeAttached=false;}
 virtual bool start(IOService*){assert(!mExpansionData->fRegistrationInfo&&!mExpansionData2->fRegistrationInfo);if(mockRole==6)nativeController->setAwdlInterface(this);return nativeStarted=!fail();}
 virtual void stop(IOService*){assert(nativeStarted);sequence.push_back("native-stop");nativeStarted=false;if(mExpansionData)mExpansionData->fBSDInterface=nullptr;}
 virtual bool terminate(unsigned options){assert(getController());
  // A synchronous wait under the command gate is the deadlock this models.
  if(options&kIOServiceSynchronous)assert(!inGate);
  if(nativeOpen){--openControllers;nativeOpen=false;}
  retain();auto finish=[this]{stop(nullptr);if(nativeAttached)detach(nullptr);release();};
  if(options&kIOServiceSynchronous)finish();else pendingTerminations.push_back(finish);
  return true;}
 const char *getBSDName(){return mExpansionData&&mExpansionData->fBSDInterface?(mockRole==2?"llw0":"awdl0"):"";}
 void *getBSDInterface(){return mExpansionData?mExpansionData->fBSDInterface:nullptr;}
 ether_addr getSelfMacAddr(){return mockMac;}
 void setInterfaceId(unsigned id){assert(id==2||id==9);mockId=id;}
 bool initRegistrationInfo(IOSkywalkEthernetInterface::RegistrationInfo*,unsigned,size_t n){assert(n==0x130);return !fail();}
 int registerEthernetInterface(IOSkywalkEthernetInterface::RegistrationInfo *p,IOSkywalkPacketQueue**,unsigned n,IOSkywalkPacketBufferPool*,IOSkywalkPacketBufferPool*,unsigned){assert(n==4);assert(testLoop->sources.size()>=5);
  auto copy=[&](auto *&slot){using T=std::remove_reference_t<decltype(*slot)>;slot=static_cast<T*>(std::malloc(sizeof(T)));++blocks;memcpy(slot,p,sizeof(T));};
  copy(mExpansionData->fRegistrationInfo);copy(mExpansionData2->fRegistrationInfo);uint32_t mtu;std::memcpy(&mtu,p->bytes+0x48,4);assert(mtu==1428);if(fail())return -3;if(duringRegister)duringRegister();return 0;}
 // Models IOSkywalkNetworkBSDClient: the BSD interface appears only after publishing.
 void attachBSD(){if(published)mExpansionData->fBSDInterface=this;}
 virtual int setRunningState(bool b){assert(getBSDInterface());nativeRunning=b;return 0;}
 IO80211LinkState nativeLink=kIO80211NetworkLinkDown;unsigned interfaceEnables=0;
 virtual IO80211LinkState linkState(){return nativeLink;}
 virtual bool setLinkState(IO80211LinkState s,unsigned){nativeLink=s;return true;}
 // Models the native base: enabling brings the link up through the virtual setLinkState.
 std::vector<std::vector<uint8_t>> posted;std::vector<unsigned> postedIds;
 virtual void postMessage(unsigned id,void *d,unsigned long n,bool){postedIds.push_back(id);auto q=static_cast<uint8_t*>(d);posted.emplace_back(q,q+n);}
 unsigned linkStatus=0;void reportLinkStatus(unsigned a,unsigned){linkStatus=a;}unsigned nativeRunning=0;
 virtual int setInterfaceEnable(bool b){++interfaceEnables;setLinkState(b?kIO80211NetworkLinkUp:kIO80211NetworkLinkDown,1);return 0;}
 void free(){assert(!nativeStarted&&!nativeAttached&&!nativeOpen);if(mExpansionData){releaseBlock(mExpansionData->fRegistrationInfo);delete mExpansionData;mExpansionData=nullptr;}if(mExpansionData2){releaseBlock(mExpansionData2->fRegistrationInfo);delete mExpansionData2;mExpansionData2=nullptr;}}
};
IO80211VirtualInterface *lastCreated=nullptr,*lastLlw=nullptr;
class IO80211AWDLProtocol:public IO80211VirtualInterface {};
#define OSSafeReleaseNULL(x) do {if(x)(x)->release();(x)=nullptr;}while(0)
'''
factory='struct OSMetaClassBase { const OSMetaClassBase *metaCast(const char *n) const { return n && !strcmp(n, "IOSkywalkNetworkPacket") ? this : nullptr; } };\n'
for n in ['TxSubmission','TxCompletion','RxSubmission','RxCompletion']:
 t='IOSkywalkPacket *const *' if 'Submission' in n else 'IOSkywalkPacket **'
 extra='UInt32, ' if n=='RxSubmission' else ''
 factory+=f'''IOSkywalk{n}Queue *IOSkywalk{n}Queue::withPool(IOSkywalkPacketBufferPool*,UInt32,UInt32,{extra}OSObject*,UInt32 (*)(OSObject*,IOSkywalk{n}Queue*,{t},UInt32,void*),void*,IOOptionBits) {{ if(fail())return nullptr;return reinterpret_cast<IOSkywalk{n}Queue *>(new IOSkywalkPacketQueue); }}\n'''
main=r'''
uint8_t *be201PacketBase(const IOSkywalkPacket *p){assert(mp(p)->prepared);return mp(p)->data;}
UInt16 be201PacketOffset(const IOSkywalkPacket *p){return mp(p)->offset;}
UInt32 be201PacketLength(const IOSkywalkPacket *p){return mp(p)->length;}
IOReturn be201PacketSetLength(IOSkywalkPacket *p,UInt32 n){assert(mp(p)->prepared);if(setLengthResult)return setLengthResult;mp(p)->length=n;return 0;}
IOReturn be201PacketPrepare(IOSkywalkPacket *p,void *q,UInt32 d,UInt32 o){assert(!q&&d==2&&!o&&!mp(p)->prepared);if(prepareResult)return prepareResult;mp(p)->prepared=true;return 0;}
IOReturn be201PoolAllocate(IOSkywalkPacketBufferPool*,IOSkywalkPacket **o,UInt32 options){assert(options==1);if(poolResult)return poolResult;auto m=new MockPacket;m->prepared=false;++poolLive;*o=reinterpret_cast<IOSkywalkPacket*>(m);return 0;}
void be201PoolDeallocate(IOSkywalkPacketBufferPool*,IOSkywalkPacket *p){delete mp(p);--poolLive;}
IOReturn be201TxCompEnqueue(void*,IOSkywalkPacket *const*,UInt32 n,UInt32){txCompleted+=n;return 0;}
static unsigned rxStampCalls;IOReturn be201NetPacketSetTimestamp(IOSkywalkPacket *p,uint64_t t){assert(mp(p)->prepared&&t);mp(p)->stamped=true;++rxStampCalls;return 0;}
IOReturn be201RxCompEnqueue(void*,IOSkywalkPacket *const *p,UInt32 n,UInt32){assert(mp(p[0])->prepared);assert(mp(p[0])->stamped||(AirportItlwm::awdlRocWanted()&0x100000)); /* 1.2.24: off by default (presence A/B) */if(rxEnqueueResult)return rxEnqueueResult;rxEnqueued+=n;rxSeen.push_back(mp(p[0]));return 0;}
void be201TxSubEnable(void*){++txEnabled;}void be201TxCompEnable(void*){++txCompEnabled;}void be201RxCompEnable(void*){++rxCompEnabled;}
IOReturn be201TxSubRequestDequeue(void*,void*,UInt32){++txDeq;return 0;}
int main(){
 AirportItlwm controller;unsigned cases=0;
 IOWorkLoop loop;loop.rc=1000;testLoop=&loop;
 for(int repeat=0;repeat<64;++repeat)for(int fault=0;fault<=22;++fault){
  failAt=fault;step=0;sequence.clear();controller.awdlPointer=nullptr;auto v=new AirportItlwmAWDLInterface;
  ether_addr mac={{2,1,2,3,4,5}};
  bool ok=v->initForController(&controller,mac)&&v->attach(&controller)&&v->start(&controller);
  if(ok){assert(!v->getBSDInterface());v->attachBSD();assert(v->getBSDInterface());v->markDown();
   assert(!strcmp(v->getBSDNamePrefix(),"awdl"));assert(v->linkState()==kIO80211NetworkLinkDown);assert(!v->setLinkState(kIO80211NetworkLinkUp,0));assert(!v->setLinkState(kIO80211NetworkLinkUp,0,false,0));assert(v->enable(0)==kIOReturnUnsupported);assert(v->setInterfaceEnable(true)==kIOReturnUnsupported);assert(v->setRunningState(true)==kIOReturnUnsupported);assert(!v->start(&controller));apple80211_awdl_sync_enabled enabled{};assert(!v->getAWDL_SYNC_ENABLED(&enabled)&&!enabled.enabled);}
  if(v->holdsNativeState())v->terminate(kIOServiceRequired|kIOServiceSynchronous);
  v->release();drainTerminations();
  assert(!pools&&!queuesLive&&!openControllers&&loop.sources.empty()&&!controller.awdlPointer);
  auto ns=std::find(sequence.begin(),sequence.end(),"native-stop");auto qm=std::find(sequence.begin(),sequence.end(),"queue-remove");auto qr=std::find(sequence.begin(),sequence.end(),"queue-release");
  if(qm!=sequence.end())assert(ns!=sequence.end()&&ns<qm&&qm<qr);
  if(qr!=sequence.end())assert(ns!=sequence.end()&&ns<qr&&sequence.back()=="pool-release");
  ++cases;
 }
 {
  // Set requests: refused unless the test turned acceptance on; every request is logged in order, bounded.
  failAt=0;step=0;auto v=new AirportItlwmAWDLInterface;ether_addr mac={{2,1,2,3,4,5}};
  assert(v->initForController(&controller,mac)&&v->attach(&controller)&&v->start(&controller));
  apple80211_awdl_sync_enabled set{};
  assert(v->setAWDL_SYNC_ENABLED(&set)==kIOReturnUnsupported);
  be201AwdlVifAcceptSetsValue=1;
  assert(v->setAWDL_SYNC_ENABLED(&set)==kIOReturnSuccess&&v->getSSID(nullptr)==kIOReturnUnsupported&&v->setCOMPANION_SKYWALK_IF_CREATE(nullptr)==kIOReturnUnsupported&&v->setRunningState(true)==kIOReturnUnsupported);
  assert((v->requestLogCopy==std::vector<uint16_t>{530,530,500,555,1002}));
  // The name is bounded and the peer address never copied.
  uint8_t raw[0x100]={};uint32_t len=24;memcpy(raw+0xc,&len,4);memcpy(raw+0x10,"wifid-assisted-discovery",24);memset(raw+4,0xaa,8);
  auto reg=reinterpret_cast<apple80211_awdl_peer_traffic_registration*>(raw);
  assert(v->setAWDL_PEER_TRAFFIC_REGISTRATION(reg)==kIOReturnSuccess&&v->strings["ItlwmAwdlTrafficRegistrationName"]=="wifid-assisted-discovery");
  len=0xffff;memcpy(raw+0xc,&len,4);v->strings.clear();assert(v->setAWDL_PEER_TRAFFIC_REGISTRATION(reg)==kIOReturnSuccess&&v->strings.empty());
  assert(v->setAWDL_PEER_TRAFFIC_REGISTRATION(nullptr)==kIOReturnSuccess);
  for(int i=0;i<400;++i)v->setAWDL_SYNC_ENABLED(&set);
  assert(v->requestLogCopy.size()==256);
  be201AwdlVifAcceptSetsValue=0;
  v->terminate(kIOServiceRequired|kIOServiceSynchronous);v->release();drainTerminations();
  assert(!queuesLive&&!pools&&!openControllers&&!controller.awdlPointer);
 }
 assert(AirportItlwmAWDLInterface::txSubmitAction(nullptr,nullptr,nullptr,4,nullptr)==0&&rxSubmit(nullptr,nullptr,nullptr,4,nullptr)==0);
 // Execute the actual controller factory on success, duplicate, malformed request and re-entry.
 Gate gate;gate.owner=&controller;_fCommandGate=&gate;
 auto bsdAttaches=[&]{gate.whileSleeping=[&]{if(lastCreated)lastCreated->attachBSD();};};
 auto bsdNever=[&]{gate.whileSleeping={};};
 bsdAttaches();
 failAt=0;step=0;controller.awdlStopping=false;
 apple80211_virt_if_create_data req;
 // Unarmed, as on every boot: refused before anything is allocated, and no capability advertised.
 assert(!AirportItlwm::awdlVifCapabilityArmed());
 assert(controller.createAWDLInterface(&req)==kIOReturnUnsupported&&!controller.awdlInterface&&step==0&&controller.awdlUnarmedRefusals==1);
 controller.registerAWDLArmControl();controller.registerAWDLArmControl();assert(oidRegistered==22); /* 1.2.24: be201_awdl_pause */
 assert(AirportItlwm::awdlVifPoolFlags()==0);be201AwdlVifPoolFlagsValue=3;assert(AirportItlwm::awdlVifPoolFlags()==1);be201AwdlVifPoolFlagsValue=0;
 be201AwdlVifArm=1;assert(AirportItlwm::awdlVifCapabilityArmed());
 assert(controller.createAWDLInterface(&req)==0&&lastPoolFlags==0&&be201AwdlVifArm==0&&controller.awdlAttempts==1&&AirportItlwm::awdlVifCapabilityArmed()&&controller.awdlInterface&&!strcmp(reinterpret_cast<char*>(req.bsd_name),"awdl0"));
 auto old=controller.awdlInterface;auto oldSteps=step;
 assert(controller.createAWDLInterface(&req)==0&&controller.awdlInterface==old&&step==oldSteps);
 req.mac[1]++;assert(controller.createAWDLInterface(&req)==kIOReturnBusy);req.mac[1]--;
 req.role=7;assert(controller.createAWDLInterface(&req)==kIOReturnUnsupported);req.role=6;
 req.version=99;assert(controller.createAWDLInterface(&req)==kIOReturnUnsupported);req.version=0;
 req.mac[0]=1;assert(controller.createAWDLInterface(&req)==kIOReturnBadArgument);req.mac[0]=2;
 controller.stopAWDLInterface();controller.stopAWDLInterface();drainTerminations();assert(oidRegistered==0&&!controller.awdlInterface&&!queuesLive&&!pools&&!openControllers&&loop.sources.empty());
 // A failed attempt consumes the arm and keeps the object: the controller's AWDL pointer stays valid
 // until stop, later requests are refused without allocating, and the arm cannot retry it.
 for(int fault=1;fault<=8;++fault){
  controller.awdlStopping=false;failAt=fault;step=0;be201AwdlVifArm=1;
  int result=controller.createAWDLInterface(&req);assert(result!=0&&be201AwdlVifArm==0);
  assert(!controller.awdlPointer||controller.awdlPointer==reinterpret_cast<IO80211VirtualInterface*>(controller.awdlInterface));
  if(controller.awdlInterface){assert(controller.awdlFailed);auto steps=step;be201AwdlVifArm=1;
   assert(controller.createAWDLInterface(&req)==kIOReturnNotReady&&step==steps&&be201AwdlVifArm==1);be201AwdlVifArm=0;}
  controller.stopAWDLInterface();drainTerminations();controller.awdlFailed=false;
  assert(!controller.awdlPointer&&!queuesLive&&!pools&&!openControllers&&loop.sources.empty());
 }
 failAt=0;
 // The BSD client never attaches: bounded wait, failure, object kept.
 controller.awdlStopping=false;step=0;be201AwdlVifArm=1;bsdNever();gate.sleeps=0;
 assert(controller.createAWDLInterface(&req)==kIOReturnNotReady&&gate.sleeps==300&&controller.awdlFailed&&controller.awdlInterface&&controller.awdlPointer);
 // 1.1.58: the BSD client attaches after the wait gave up; the next request takes the kept object, without the arm.
 {auto steps=step;assert(be201AwdlVifArm==0);
  assert(controller.createAWDLInterface(&req)==kIOReturnNotReady&&controller.awdlFailed); // still not attached
  lastCreated->attachBSD();req.mac[1]^=1;assert(controller.createAWDLInterface(&req)==kIOReturnBusy&&controller.awdlFailed);req.mac[1]^=1;
  assert(controller.createAWDLInterface(&req)==kIOReturnSuccess&&!controller.awdlFailed&&controller.awdlLateAdopted==1&&step==steps);
  assert(!strcmp(reinterpret_cast<const char*>(req.bsd_name),"awdl0"));
  assert(controller.createAWDLInterface(&req)==kIOReturnSuccess&&controller.awdlLateAdopted==1);} // later requests: the normal path
 controller.stopAWDLInterface();drainTerminations();controller.awdlFailed=false;assert(!controller.awdlPointer&&!queuesLive);
 bsdAttaches();
 for(int mode=0;mode<2;++mode){
  controller.awdlStopping=false;be201AwdlVifArm=1;duringRegister=[&]{
   if(mode==0)assert(controller.createAWDLInterface(&req)==kIOReturnNotReady);
   else controller.awdlStopping=true; // Models a stop request while native registration yields the gate.
  };
  int result=controller.createAWDLInterface(&req);duringRegister={};
  if(mode==0)assert(result==0);else assert(result==kIOReturnNotReady&&controller.awdlInterface&&controller.awdlFailed);
  controller.stopAWDLInterface();drainTerminations();controller.awdlFailed=false;assert(!controller.awdlPointer&&!queuesLive&&!pools&&!openControllers&&loop.sources.empty());
 }

 {
  auto v=new AirportItlwmAWDLInterface;uint8_t frame[40]={0xd0};memcpy(frame+16,iwx_awdl_bssid,6);
  frame[10]=2;const uint8_t body[16]={127,0,0x17,0xf2,8,0x10,3};memcpy(frame+24,body,16);
  v->started=true;v->registered=true;v->linkActive=true;v->queueLoop=&loop;loop.retain();
  controller.awdlStopping=false;controller.awdlCreating=false;controller.awdlInterface=v;
  be201AwdlVifRxValue=0;inGate=1;controller.inputAWDLActionFrame(frame,40,149,-40,123);assert(!bufferGets);
  be201AwdlVifRxValue=1;
  for(unsigned fault=0;fault<8;++fault){
   bufferFailure=0;poolPresent=true;v->started=v->registered=v->linkActive=true;inGate=1;
   controller.awdlStopping=false;controller.awdlCreating=false;
   if(fault==0)inGate=0;else if(fault==1)controller.awdlStopping=true;else if(fault==2)controller.awdlCreating=true;
   else if(fault==3)v->started=false;else if(fault==4)v->registered=false;else if(fault==5)v->linkActive=false;
   else if(fault==6)poolPresent=false;else bufferFailure=1;
   controller.inputAWDLActionFrame(frame,40,149,-40,123);assert(!bufferSubmits&&!bufferReturns);
  }
  bufferFailure=0;poolPresent=true;inGate=1;v->started=v->registered=v->linkActive=true;
  for(unsigned fault=2;fault<=3;++fault){bufferFailure=fault;controller.inputAWDLActionFrame(frame,40,149,-40,123);assert(bufferReturns==int(fault-1)&&!bufferSubmits);}
  bufferFailure=0;controller.inputAWDLActionFrame(frame,40,149,-40,123);assert(bufferSubmits==1&&bufferReturns==2&&testBuffer.length==16);
  assert(!memcmp(testBuffer.data,body,16)&&v->nativeRxSubmitted==1);
  frame[24]=0;controller.inputAWDLActionFrame(frame,40,149,-40,123);assert(v->nativeRxInvalid==1&&bufferSubmits==1);
  // A torn-down/null controller child is never dereferenced.
  controller.awdlInterface=nullptr;controller.inputAWDLActionFrame(frame,40,149,-40,123);assert(bufferSubmits==1);
  controller.awdlInterface=v;frame[24]=127;
  duringNativeInput=[&]{assert(v->rc==2);v->started=v->registered=false;controller.awdlInterface=nullptr;v->release();};
  // Drop the owner's last reference inside native input: ASan verifies post-call property access.
  controller.inputAWDLActionFrame(frame,40,149,-40,123);duringNativeInput={};assert(bufferSubmits==2&&!controller.awdlInterface);
  inGate=0;be201AwdlVifRxValue=0;
 }
 {
  // Link up: off by default, once only, from the timer, and never success to the BSD client (no IFF_RUNNING).
  failAt=0;step=0;auto v=new AirportItlwmAWDLInterface;ether_addr mac={{2,1,2,3,4,5}};
  assert(v->initForController(&controller,mac)&&v->attach(&controller)&&v->start(&controller));
  v->attachBSD();v->markDown();
  assert(v->setRunningState(true)==kIOReturnUnsupported&&!v->linkTimer->armed&&v->linkState()==kIO80211NetworkLinkDown&&!v->setLinkState(kIO80211NetworkLinkUp,0));
  be201AwdlVifLinkValue=1;
  assert(v->setRunningState(true)==kIOReturnUnsupported&&v->linkTimer->armed&&v->interfaceEnables==0);
  assert(v->linkState()==kIO80211NetworkLinkDown);
  const unsigned loads=controller.capabilityLoads;
  v->linkTimer->fire();
  assert(controller.capabilityLoads==loads+1&&controller.blobs["ItlwmAwdlCapabilityCache"]==0x18);
  assert(v->interfaceEnables==1&&v->linkState()==kIO80211NetworkLinkUp&&v->properties["ItlwmAwdlLinkState"]==kIO80211NetworkLinkUp&&v->properties["ItlwmAwdlLinkResult"]==0);
  assert(v->setRunningState(true)==kIOReturnUnsupported&&!v->linkTimer->armed&&v->linkTimer->arms==1);
  // What the AWDL manager asks for is kept, bounded, only when accepted.
  be201AwdlVifAcceptSetsValue=1;
  apple80211_awdl_sync_enabled en{};uint8_t tpl[0x240]={};
  assert(v->setAWDL_SYNC_ENABLED(&en)==kIOReturnSuccess&&v->blobs["ItlwmAwdlPayload530"]==sizeof(en));
  uint8_t blob[0x40]={};uint32_t tplLen=sizeof(blob);const uint8_t *tplPtr=blob;memcpy(tpl+4,&tplLen,4);memcpy(tpl+8,&tplPtr,8);
  assert(v->setAWDL_SYNC_FRAME_TEMPLATE(reinterpret_cast<apple80211_awdl_sync_frame_template*>(tpl))==kIOReturnSuccess&&v->blobs["ItlwmAwdlTemplatePsf"]==0x40);
  // A bad length is counted and never read through.
  tplLen=4096;memcpy(tpl+4,&tplLen,4);assert(v->setAWDL_SYNC_FRAME_TEMPLATE(reinterpret_cast<apple80211_awdl_sync_frame_template*>(tpl))==kIOReturnSuccess&&v->properties["ItlwmAwdlTemplateBad"]==1);
  assert(v->blobs["ItlwmAwdlRequestCounts"]==4096);
  be201AwdlVifAcceptSetsValue=0;be201AwdlVifLinkValue=0;
  v->terminate(kIOServiceRequired|kIOServiceSynchronous);v->release();drainTerminations();
  assert(loop.sources.empty()&&!pools&&!queuesLive);
 }
 {
  // A timer still pending at stop is cancelled, and link down is always allowed.
  failAt=0;step=0;auto v=new AirportItlwmAWDLInterface;ether_addr mac={{2,1,2,3,4,5}};
  assert(v->initForController(&controller,mac)&&v->attach(&controller)&&v->start(&controller));
  v->attachBSD();v->markDown();assert(v->setLinkState(kIO80211NetworkLinkDown,0));
  be201AwdlVifLinkValue=1;assert(v->setRunningState(true)==kIOReturnUnsupported&&v->linkTimer->armed);
  auto *t=v->linkTimer;v->terminate(kIOServiceRequired|kIOServiceSynchronous);assert(v->interfaceEnables==0);v->release();drainTerminations();(void)t;
  be201AwdlVifLinkValue=0;
 }

 {
  // AW start events: only with the second permission, in order, from the programmed sequence, none after stop.
  failAt=0;step=0;auto v=new AirportItlwmAWDLInterface;ether_addr mac={{2,1,2,3,4,5}};
  assert(v->initForController(&controller,mac)&&v->attach(&controller)&&v->start(&controller));
  v->attachBSD();v->markDown();be201AwdlVifLinkValue=1;be201AwdlVifAcceptSetsValue=1;
  auto monitorCalls=controller.mockHAL.calls;
  v->setRunningState(true);v->linkTimer->fire();assert(!v->awTimer->armed&&controller.mockHAL.calls==monitorCalls);
  v->terminate(kIOServiceRequired|kIOServiceSynchronous);v->release();drainTerminations();
  v=new AirportItlwmAWDLInterface;step=0;
  assert(v->initForController(&controller,mac)&&v->attach(&controller)&&v->start(&controller));
  v->attachBSD();v->markDown();be201AwdlVifAwValue=1;
  uint8_t seq[0x190]={};uint32_t one=1,six=6,ten=10;memcpy(seq+12,&one,4);memcpy(seq+16,&six,4);memcpy(seq+20,&ten,4);
  assert(v->setAWDL_SYNCHRONIZATION_CHANNEL_SEQUENCE(reinterpret_cast<apple80211_awdl_sync_channel_sequence*>(seq))==kIOReturnSuccess);
  v->setRunningState(true);v->linkTimer->fire();assert(v->awTimer->armed&&v->posted.empty());
  v->awTimer->fire();v->awTimer->fire();
  assert(v->posted.size()==2&&v->postedIds[0]==41&&v->posted[0].size()==0x28&&v->awTimer->armed);
  uint32_t n0,n1,ch0,ch1;memcpy(&n0,v->posted[0].data(),4);memcpy(&n1,v->posted[1].data(),4);memcpy(&ch0,v->posted[0].data()+0x1c,4);memcpy(&ch1,v->posted[1].data()+0x1c,4);
  assert(n0==0&&n1==1&&ch0==6&&ch1==0&&!memcmp(v->posted[0].data()+0x0e,mac.octet,6));
  // Reading back what was programmed, and nothing before that.
  {apple80211_awdl_master_channel m{};assert(v->getAWDL_MASTER_CHANNEL(&m)==kIOReturnUnsupported);m.version=7;
   assert(v->setAWDL_MASTER_CHANNEL(&m)==kIOReturnSuccess);apple80211_awdl_master_channel g{};assert(v->getAWDL_MASTER_CHANNEL(&g)==kIOReturnSuccess&&g.version==7);}
  // Four AWs per channel slot: the number advances by four and the channel by one slot.
  seq[7]=3;memcpy(seq+24,&one,4);memcpy(seq+28,&six,4);
  assert(v->setAWDL_SYNCHRONIZATION_CHANNEL_SEQUENCE(reinterpret_cast<apple80211_awdl_sync_channel_sequence*>(seq))==kIOReturnSuccess);
  v->awNumber=0;v->posted.clear();v->awTimer->fire();v->awTimer->fire();v->awTimer->fire();
  memcpy(&n0,v->posted[1].data(),4);memcpy(&ch0,v->posted[1].data()+0x1c,4);assert(n0==4&&ch0==6);memcpy(&n1,v->posted[2].data(),4);memcpy(&ch1,v->posted[2].data()+0x1c,4);assert(n1==8&&ch1==0);
  v->terminate(kIOServiceRequired|kIOServiceSynchronous);v->release();drainTerminations();
  be201AwdlVifAwValue=0;
  v=new AirportItlwmAWDLInterface;step=0;
  assert(v->initForController(&controller,mac)&&v->attach(&controller)&&v->start(&controller));
  v->attachBSD();v->markDown();be201AwdlVifRadioValue=1;
  v->setRunningState(true);v->linkTimer->fire();
  assert(controller.mockHAL.calls==monitorCalls+1&&!memcmp(controller.mockHAL.last,mac.octet,6)&&!v->awTimer->armed);
  assert(v->properties["ItlwmAwdlNativeMonitorQueueResult"]==0);
  v->terminate(kIOServiceRequired|kIOServiceSynchronous);v->release();drainTerminations();
  // Transmit: templates reach the HAL only with its permission and inside the gate; enabled once after the monitor.
  {auto *t=new AirportItlwmAWDLInterface;step=0;assert(t->initForController(&controller,mac)&&t->attach(&controller)&&t->start(&controller));
   t->attachBSD();t->markDown();
   uint8_t req[0x40]={},body[9]={21,2,0,0x93,1,6,1,0,9};uint32_t l=sizeof(body);const uint8_t *q=body;memcpy(req+0x28,&l,4);memcpy(req+0x30,&q,8);
   auto *r=reinterpret_cast<apple80211_awdl_oob_request*>(req);const unsigned t0=controller.mockHAL.templates;
   inGate=1;assert(t->setAWDL_OOB_AUTO_REQUEST(r)==kIOReturnSuccess&&controller.mockHAL.templates==t0&&t->blobs["ItlwmAwdlTemplateMif"]==sizeof(body));
   be201AwdlVifTxValue=1;inGate=0;t->setAWDL_OOB_AUTO_REQUEST(r);assert(controller.mockHAL.templates==t0);
   inGate=1;t->setAWDL_OOB_AUTO_REQUEST(r);assert(controller.mockHAL.templates==t0+1&&controller.mockHAL.lastMif&&controller.mockHAL.lastTemplate==sizeof(body));inGate=0;
   const unsigned e0=controller.mockHAL.enables;be201AwdlVifRadioValue=1;
   t->setRunningState(true);t->linkTimer->fire();assert(controller.mockHAL.enables==e0+1);
   be201AwdlVifTxValue=0;
   t->terminate(kIOServiceRequired|kIOServiceSynchronous);t->release();drainTerminations();}
  // Data path: refused without its permission; after it, RUNNING, queues on, frames both ways.
  {auto *t=new AirportItlwmAWDLInterface;step=0;assert(t->initForController(&controller,mac)&&t->attach(&controller)&&t->start(&controller));
   t->attachBSD();t->markDown();
   MockPacket eth;eth.length=60;memset(eth.data,0x11,60);auto *ep=reinterpret_cast<IOSkywalkPacket*>(&eth);IOSkywalkPacket *const list[1]={ep};
   assert(!AirportItlwmAWDLInterface::txSubmitAction(t,nullptr,list,1,nullptr)&&!controller.mockHAL.sent);
   assert(t->setRunningState(true)==kIOReturnUnsupported);
   t->linkTimer->fire();assert(!t->dataActive&&!txEnabled&&t->setRunningState(true)==kIOReturnUnsupported);
   t->terminate(kIOServiceRequired|kIOServiceSynchronous);t->release();drainTerminations();
   t=new AirportItlwmAWDLInterface;step=0;assert(t->initForController(&controller,mac)&&t->attach(&controller)&&t->start(&controller));
   t->attachBSD();t->markDown();be201AwdlVifDataValue=1;
   t->setRunningState(true);t->linkTimer->fire();
   assert(t->dataActive&&txEnabled==1&&txCompEnabled==1&&rxCompEnabled==1&&txDeq==1&&t->linkStatus==3&&ifRunning==IFF_RUNNING&&t->nativeRunning==1);
   assert(t->setRunningState(true)==0);
   /* Wi-Fi off and on clears RUNNING while awdl0 stays up: link up restores it; down or not up leaves it (1.1.74). */
   ifnet_set_flags(nullptr,0,IFF_RUNNING);t->nativeRunning=0;ifnet_set_flags(nullptr,0,IFF_UP);t->restoreRunning();assert(!(ifFlags&IFF_RUNNING)&&!t->properties.count("ItlwmAwdlRunningRestores"));
   ifnet_set_flags(nullptr,IFF_UP,IFF_UP);t->setLinkState(kIO80211NetworkLinkDown,0);t->restoreRunning();assert(!(ifFlags&IFF_RUNNING));
   assert(t->setLinkState(kIO80211NetworkLinkUp,0)&&(ifFlags&IFF_RUNNING)&&t->nativeRunning==1&&t->linkStatus==3&&t->properties["ItlwmAwdlRunningRestores"]==1);
   t->restoreRunning();assert(t->properties["ItlwmAwdlRunningRestores"]==1);
   // Every submitted packet is completed, sent or dropped, and counted once.
   assert(AirportItlwmAWDLInterface::txSubmitAction(t,nullptr,list,1,nullptr)==1&&controller.mockHAL.sent==1&&controller.mockHAL.lastSent==60&&txCompleted==1&&t->dataTx==1);
   controller.mockHAL.sendResult=-1;assert(AirportItlwmAWDLInterface::txSubmitAction(t,nullptr,list,1,nullptr)==1&&txCompleted==2&&t->dataTxDropped==1);
   /* A full queue keeps the packet: nothing completed, nothing dropped, and one wake per wait. */
   controller.mockHAL.sendResult=kIOReturnBusy;{unsigned d=txDeq;assert(AirportItlwmAWDLInterface::txSubmitAction(t,nullptr,list,1,nullptr)==0&&txCompleted==2&&t->dataTxDropped==1&&t->txWaiting);t->txRoom();assert(txDeq==d+1&&!t->txWaiting);t->txRoom();assert(txDeq==d+1);}controller.mockHAL.sendResult=-1;
  controller.mockHAL.sendResult=0;
   /* 1.1.78: what went out and came in since the last report reaches the family; nothing new, no report. */
   {unsigned c0=statsCalls;t->reportDataStats();assert(statsCalls==c0+1&&statsTx==t->dataTx&&statsRx==t->dataRx);t->reportDataStats();assert(statsCalls==c0+1);
    assert(AirportItlwmAWDLInterface::txSubmitAction(t,nullptr,list,1,nullptr)==1);t->reportDataStats();assert(statsCalls==c0+2&&statsTx==1&&statsRx==0);}
   // Peer data for this address reaches the stack as Ethernet; others and unknown formats do not.
   uint8_t f[80]={};f[0]=0x08;memcpy(f+4,mac.octet,6);f[10]=2;f[15]=7;memcpy(f+16,iwx_awdl_bssid,6);const uint8_t l_[10]={0xaa,0xaa,3,0,0x17,0xf2,8,0,3,4};memcpy(f+24,l_,10);f[38]=0x86;f[39]=0xdd;memset(f+40,0x55,40);
   controller.awdlInterface=t;controller.awdlStopping=false;controller.awdlCreating=false;
   be201AwdlVifRxValue=1;inGate=1;controller.inputAWDLActionFrame(f,80,149,-40,0);
   assert(rxEnqueued==1&&t->properties["ItlwmAwdlDataRx"]==1&&rxSeen[0]->length==54&&!memcmp(rxSeen[0]->data,mac.octet,6)&&rxSeen[0]->data[12]==0x86&&rxSeen[0]->data[13]==0xdd&&rxSeen[0]->data[14]==0x55);
   f[4]^=2;controller.inputAWDLActionFrame(f,80,149,-40,0);assert(rxEnqueued==1);f[4]^=2;
   f[0]=0x48;controller.inputAWDLActionFrame(f,80,149,-40,0);assert(rxEnqueued==1);f[0]=0x08;
   f[24]=0;controller.inputAWDLActionFrame(f,80,149,-40,0);assert(rxEnqueued==1);f[24]=0xaa;
   poolResult=-1;controller.inputAWDLActionFrame(f,80,149,-40,0);assert(t->properties["ItlwmAwdlDataRxDropped"]==1);poolResult=0;
   const unsigned live=poolLive;rxEnqueueResult=-1;controller.inputAWDLActionFrame(f,80,149,-40,0);assert(poolLive==live&&t->properties["ItlwmAwdlDataRxDropped"]==2);rxEnqueueResult=0;
   prepareResult=-1;controller.inputAWDLActionFrame(f,80,149,-40,0);assert(poolLive==live&&t->properties["ItlwmAwdlDataRxDropped"]==3);prepareResult=0;
   setLengthResult=-1;controller.inputAWDLActionFrame(f,80,149,-40,0);assert(poolLive==live&&t->properties["ItlwmAwdlDataRxDropped"]==4);setLengthResult=0;
   for(auto *m:rxSeen){delete m;--poolLive;}rxSeen.clear();assert(!poolLive);
   // UMI: off by default, then the address and the manager's own buffer reach the radio; the result goes back as event 69.
   {uint8_t oob[0x38+8]={};const uint8_t tl[4]={1,1,0,9};uint16_t oobLen=4;const uint8_t *oobPtr=tl;const uint8_t umiPeer[6]={2,9,9,9,9,9};
    memcpy(oob+4,umiPeer,6);memcpy(oob+0x28,&oobLen,2);memcpy(oob+0x30,&oobPtr,8);
    be201AwdlVifAcceptSetsValue=1;
    assert(t->setAWDL_OOB_REQUEST(reinterpret_cast<apple80211_awdl_oob_request*>(oob))==0&&controller.umiSends==0);
    be201AwdlUmiValue=1;
    assert(t->setAWDL_OOB_REQUEST(reinterpret_cast<apple80211_awdl_oob_request*>(oob))==0&&controller.umiSends==1&&!memcmp(controller.umiPeer,umiPeer,6)&&controller.umiTlvs==tl&&controller.umiLen==4);
    be201AwdlUmiValue=0;
    size_t before=t->postedIds.size();controller.awdlUmiDone(umiPeer,true);assert(t->postedIds.size()==before+1&&t->postedIds.back()==69&&t->posted.back().size()==64&&!memcmp(t->posted.back().data(),umiPeer,6)&&t->posted.back()[6]==0);
    controller.awdlUmiDone(umiPeer,false);assert(t->posted.back()[6]==1);}
   // llw0: refused while the switch is off, as before; then a role 2 child of awdl0 that never takes the controller's AWDL pointer.
   {uint8_t creq[0x40]={};const uint32_t createOp=1;memcpy(creq+4,&createOp,4);
    auto *companionArg=reinterpret_cast<apple80211_companion_skywalk_if_create*>(creq);
    assert(t->setCOMPANION_SKYWALK_IF_CREATE(companionArg)==kIOReturnUnsupported&&!controller.llwInterface);
    be201AwdlLlwValue=1;Gate llwGate;llwGate.owner=&controller;auto *savedGate=_fCommandGate;_fCommandGate=&llwGate;
    llwGate.whileSleeping=[&]{if(lastLlw)lastLlw->attachBSD();};
    auto *pointerBefore=controller.awdlPointer;const int savedGateFlag=inGate;
    // Answered at once, before the BSD interface exists: waiting here never saw it attach on 1.1.47.
    const unsigned sleepsBefore=llwGate.sleeps;
    assert(t->setCOMPANION_SKYWALK_IF_CREATE(companionArg)==0&&controller.llwInterface&&!strcmp(reinterpret_cast<char*>(creq+8),"llw0")&&llwGate.sleeps==sleepsBefore);
    auto *l=controller.llwInterface;
    assert(controller.awdlPointer==pointerBefore&&l->mockRole==2&&l->mockId==9&&l->mockLowLatency&&l->mockParent==t&&t->mockCompanion==l&&!t->companion&&controller.properties["ItlwmAwdlLlwStage"]==4);
    // Asked again before the attach it gives the same name; a delete keeps it.
    creq[8]=0;assert(t->setCOMPANION_SKYWALK_IF_CREATE(companionArg)==0&&controller.llwInterface==l&&!strcmp(reinterpret_cast<char*>(creq+8),"llw0"));
    const uint32_t deleteOp=0;memcpy(creq+4,&deleteOp,4);assert(t->setCOMPANION_SKYWALK_IF_CREATE(companionArg)==0&&controller.llwInterface==l);
    // The timer waits for the attach, then joins awdl0 and brings data up.
    assert(l->linkTimer->armed);l->linkTimer->fire();assert(!l->dataActive&&controller.properties["ItlwmAwdlLlwPolls"]==1&&!t->companion);
    assert(l->setRunningState(true)!=0);
    // Native flags: low latency without the virtual base's on-demand bit.
    assert(l->getFeatureFlags()==0x10000&&t->getFeatureFlags()==0x10010000&&controller.properties["ItlwmAwdlLlwFeatureFlags"]==0x10000);
    // Its own unique id, not the address awdl0 already uses.
    {ifnet_init_eparams ep={};assert(l->initBSDInterfaceParameters(&ep,nullptr)==0&&ep.uniqueid_len==8&&*static_cast<const void*const*>(ep.uniqueid)==l&&controller.properties["ItlwmAwdlLlwUniqueId"]==1);}
    lastLlw->attachBSD();l->linkTimer->fire();
    assert(l->dataActive&&l->nativeRunning==0&&ifIoctls==1&&(ifFlags&IFF_RUNNING)&&!controller.properties.count("ItlwmAwdlLlwUpFallback")&&l->linkStatus==3&&t->companion==l&&l->mockCompanionId==t->getInterfaceId()&&controller.properties["ItlwmAwdlLlwStage"]==6);
    // What llw0 sends from, it receives on. Neighbor discovery reaches both; the rest stays on awdl0.
    uint8_t rx[120]={};rx[0]=0x08;memcpy(rx+4,mac.octet,6);rx[10]=2;rx[15]=7;memcpy(rx+16,iwx_awdl_bssid,6);memcpy(rx+24,l_,10);rx[38]=0x86;rx[39]=0xdd;rx[40]=0x60;rx[40+6]=17;
    rx[40+42]=0xc1;rx[40+43]=0x10;
    const unsigned awdlBefore=t->dataRx,llwBefore=l->dataRx;
    controller.inputAWDLActionFrame(rx,120,149,-40,0);assert(t->dataRx==awdlBefore+1&&l->dataRx==llwBefore);
    uint8_t eth[14+40+8]={};memcpy(eth,mac.octet,6);eth[0]^=2;eth[12]=0x86;eth[13]=0xdd;eth[14+6]=17;eth[14+40]=0xc1;eth[14+41]=0x10;iwx_awdl_llw_learn(&l->ports,eth,sizeof(eth));
    controller.inputAWDLActionFrame(rx,120,149,-40,0);assert(t->dataRx==awdlBefore+1&&l->dataRx==llwBefore+1);
    rx[40+6]=58;controller.inputAWDLActionFrame(rx,120,149,-40,0);assert(t->dataRx==awdlBefore+2&&l->dataRx==llwBefore+2);
    for(auto *m:rxSeen){delete m;--poolLive;}rxSeen.clear();assert(!poolLive);
    // Multicast leaves llw0 only for neighbor discovery.
    assert(iwx_awdl_llw_output_allowed(eth,sizeof(eth)));eth[0]=0x33;assert(!iwx_awdl_llw_output_allowed(eth,sizeof(eth)));eth[14+6]=58;assert(iwx_awdl_llw_output_allowed(eth,sizeof(eth)));
    be201AwdlLlwValue=0;_fCommandGate=savedGate;(void)savedGateFlag;
    controller.llwInterface=nullptr;t->setCompanion(nullptr);inGate=0;l->terminate(kIOServiceRequired|kIOServiceSynchronous);l->release();drainTerminations();inGate=1;
    lastLlw=nullptr;}
   controller.awdlInterface=nullptr;
   inGate=0;be201AwdlVifRxValue=0;be201AwdlVifDataValue=0;
   t->terminate(kIOServiceRequired|kIOServiceSynchronous);assert(!t->dataActive);t->release();drainTerminations();}
  be201AwdlVifRadioValue=0;be201AwdlVifLinkValue=0;be201AwdlVifAcceptSetsValue=0;
  assert(loop.sources.empty());
 }
 printf("PASS: %u actual lifecycle schedules, allocation/base-start/registration failures, kept object on failure, no dangling AWDL pointer, publish before BSD wait, arm gate, work loop and queue ordering, DOWN-only link and no packet consumption, set acceptance gate, bounded request log\n",cases);
}
'''
controller_source=(R/'AirportItlwm/AirportItlwmV2.cpp').read_text()
assert 'be201AwdlVifPromisc' not in controller_source
a=controller_source.index('static int be201AwdlVifArm;')
assert controller_source.index('addEventSource')>=0
iface=(R/'AirportItlwm/AirportItlwmAWDLInterface.cpp').read_text()
assert iface.index('addEventSource')<iface.index('registerEthernetInterface(&info'),'queues must be on the work loop before registration'
assert 'kIOServiceSynchronous' not in iface,'the failure path runs under the command gate'
assert iface.index('registerService()')>iface.index('registerEthernetInterface(&info'),'the BSD client needs the published service'
ctl=controller_source[a:]

assert 'interface->release()' in ctl and ctl.index('holdsNativeState()')<ctl.index('interface->release()'),'objects with native state must not be freed on failure'
assert 'IOMalloc' not in iface,'native registration owns the registration info copies'
controller_source=controller_source[a:controller_source.rindex('#endif')]
with tempfile.TemporaryDirectory() as td:
 p=Path(td);src=p/'test.cpp';src.write_text('#include <algorithm>\n'+pre+types+'\n'+h+'\n'+f+'\n'+factory+'\n#define super IO80211AWDLProtocol\n'+s+'\n'+controller_source+'\n'+main)
 subprocess.run(['clang++','-I',str(R/'itlwm/hal_iwx'),'-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-O1','-g',str(src),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
