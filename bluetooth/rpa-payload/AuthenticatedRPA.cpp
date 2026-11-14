// Sequoia experiment: route only a recently software-resolved identity.
// The original OS resolver performs IRK validation. No key is read or stored here.
// 2.7.13: the native addresses are parameters (port.py locates them in each bluetoothd build); the defaults are
// 24G824's, where they were first read.
#include <stdint.h>
#include <stddef.h>
#ifndef BE201_STATE
#define BE201_STATE 0x100a69f00      /* 232 bytes in __DATA's zero-fill tail */
#endif
#ifndef BE201_TIME_NOW
#define BE201_TIME_NOW 0x1000d5be3   /* OI_Time_Now(Time*) */
#endif
#ifndef BE201_LOG_IMPL
#define BE201_LOG_IMPL 0x1007e47a6   /* __stubs: _os_log_impl */
#endif
#ifndef BE201_LOG_DEFAULT
#define BE201_LOG_DEFAULT 0x1009db598 /* __got: __os_log_default */
#endif
#ifndef BE201_FORMAT
#define BE201_FORMAT 0x1008ee330     /* __oslogstring: "%{public}s" */
#endif
#ifndef BE201_RESOLVER
#define BE201_RESOLVER 0x1001f58d3   /* the native RPA resolver called from the scan report */
#endif
#ifndef BE201_BUILD_FILTER
#define BE201_BUILD_FILTER 0x10069214c /* set from an array (single-address filter path) */
#endif
#ifndef BE201_INSERT_MULTI
#define BE201_INSERT_MULTI 0x1002913fe /* set insert (multi-key filter path) */
#endif
extern "C" uint32_t BE201ResolveRPA(const uint8_t *,uint8_t *,uint8_t *);
__attribute__((noinline)) static uintptr_t slide() {
 uintptr_t current,preferred;
 __asm__("leaq _BE201ResolveRPA(%%rip), %0\n\tmovabsq $0xBE201BE201BE201B, %1":"=r"(current),"=r"(preferred));
 return current-preferred;
}
struct Time {uint32_t seconds;uint16_t millis;uint16_t pad;};
struct Entry {uint64_t identity,raw;Time time;};
struct State {uint64_t magic;uint32_t lock,next;uint32_t remembered,routed,expired,busy,reported;Entry entries[8];};
static_assert(sizeof(State)==232,"zero-fill tail reservation");
static constexpr uint64_t Magic=0x4254323031525041ULL;
static State *state() {return reinterpret_cast<State*>(uintptr_t(BE201_STATE)+slide());}
static uint64_t address(const uint8_t *a) {
 uint64_t v=a[0];for(unsigned i=1;i<7;i++)v=(v<<8)|a[i];return v;
}
static bool identity(uint64_t v) {
 if(v>>49 || !(v&0xffffffffffffULL) || (v&0xffffffffffffULL)==0xffffffffffffULL)return false;
 return !(v>>48) || ((v>>40)&0xc0)==0xc0;
}
static bool rpa(uint64_t v) {return v>>48==1 && ((v>>40)&0xc0)==0x40;}
static Time now() {
 Time t={};reinterpret_cast<void(*)(Time*)>(uintptr_t(BE201_TIME_NOW)+slide())(&t);return t;
}
static bool enter(State *p) {
 uint64_t expected=0;
 __atomic_compare_exchange_n(&p->magic,&expected,Magic,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE);
 if(__atomic_load_n(&p->magic,__ATOMIC_ACQUIRE)!=Magic)return false;
 if(__atomic_exchange_n(&p->lock,1,__ATOMIC_ACQUIRE)){__atomic_add_fetch(&p->busy,1,__ATOMIC_RELAXED);return false;}
 return true;
}
static void leave(State *p) {__atomic_store_n(&p->lock,0,__ATOMIC_RELEASE);}
// Use an existing native public-string format. Unified logging copies this
// fixed nonsecret string now; it must not defer decoding a new format offset.
static void report(unsigned stage) {
 volatile uint64_t message[3];
 message[0]=0x4150523130324542ULL;
 message[1]=0x303d656761747320ULL;
 message[2]=0x0ULL;
 reinterpret_cast<volatile char*>(message)[15]=char('0'+stage);
 struct __attribute__((packed)) {uint32_t header;const char *text;} buffer={0x08220102,reinterpret_cast<const char*>(const_cast<uint64_t*>(message))};
 uintptr_t s=slide();using Log=void(*)(void*,void*,unsigned,const char*,const void*,unsigned);
 reinterpret_cast<Log>(uintptr_t(BE201_LOG_IMPL)+s)(reinterpret_cast<void*>(uintptr_t(0x100000000)+s),
  *reinterpret_cast<void**>(uintptr_t(BE201_LOG_DEFAULT)+s),0,
  reinterpret_cast<const char*>(uintptr_t(BE201_FORMAT)+s),&buffer,12);
}
static bool first(State *p,unsigned stage) {uint32_t bit=1U<<stage;bool yes=!(p->reported&bit);p->reported|=bit;return yes;}
static void note(unsigned stage) {State *p=state();if(!enter(p))return;bool yes=first(p,stage);leave(p);if(yes)report(stage);}
static void remember(uint64_t stable,uint64_t raw) {
 Time t=now();if(t.millis>=1000)return;
 State *p=state();if(!enter(p))return;
 unsigned slot=p->next++%8;
 for(unsigned i=0;i<8;i++)if(p->entries[i].identity==stable){slot=i;break;}
 p->entries[slot]={stable,raw,t};++p->remembered;bool yes=first(p,1);leave(p);if(yes)report(1);
}
static uint64_t route(uint64_t stable) {
 if(!identity(stable))return stable;
 Time t=now();if(t.millis>=1000)return stable;
 State *p=state();if(!enter(p))return stable;
 uint64_t result=stable;unsigned stage=3;
 for(unsigned i=0;i<8;i++)if(p->entries[i].identity==stable) {
  const Entry &e=p->entries[i];
  // OI_Time_Now is monotonic seconds/milliseconds. Reject rollback/wrap and
  // entries older than 15s, including after a long sleep or controller restart.
  uint64_t cur=uint64_t(t.seconds)*1000+t.millis,old=uint64_t(e.time.seconds)*1000+e.time.millis;
  if(cur>=old && cur-old<=15000 && rpa(e.raw)){result=e.raw;++p->routed;stage=2;}
  else {++p->expired;stage=4;}
  break;
 }
 bool yes=first(p,stage);leave(p);if(yes)report(stage);return result;
}
extern "C" uint32_t BE201ResolveRPA(const uint8_t *raw,uint8_t *stable,uint8_t *found) {
 // Called at the native scan-report resolver call site, not every resolution.
 uint64_t input=raw?address(raw):0;
 uint32_t status=reinterpret_cast<uint32_t(*)(const uint8_t*,uint8_t*,uint8_t*)>(uintptr_t(BE201_RESOLVER)+slide())(raw,stable,found);
 if(status==0 && stable && found && *found==1 && rpa(input)) {
  uint64_t output=address(stable);if(identity(output) && input!=output)remember(output,input);
 } else if(raw && rpa(input)) {note(5);
 }
 return status;
}
// The single-address native path constructs a set from an array. The multi-key
// path inserts into that same set. Scope the two hooks to these call sites.
extern "C" void BE201BuildFilter(void *tree,const uint64_t *keys,size_t count,void *allocator) {
 using Build=void(*)(void*,const uint64_t*,size_t,void*);
 Build original=reinterpret_cast<Build>(uintptr_t(BE201_BUILD_FILTER)+slide());
 if(!keys || count>64){original(tree,keys,count,allocator);return;}
 uint64_t translated[64];for(size_t i=0;i<count;i++)translated[i]=route(keys[i]);
 original(tree,translated,count,allocator);
}
struct NativeInsertResult {void *node;uint64_t inserted;};
extern "C" NativeInsertResult BE201InsertMulti(void *tree,const uint64_t *key,const uint64_t *value) {
 using Insert=NativeInsertResult(*)(void*,const uint64_t*,const uint64_t*);
 Insert original=reinterpret_cast<Insert>(uintptr_t(BE201_INSERT_MULTI)+slide());
 if(!key || key!=value)return original(tree,key,value);
 uint64_t translated=route(*key);return original(tree,&translated,&translated);
}
