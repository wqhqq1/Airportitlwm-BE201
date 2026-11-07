// Read-only Sequoia 24G824 native-stack diagnostic. No IRK/address arguments.
// Loaded by the opt-in paired kext page patch, not by dyld or a root filesystem edit.
#include "../bt-standard-privacy/NativeCommandQueue.hpp"
using namespace be201privacy;
extern "C" void BE201PrivacyProbe();
// Filled by the offline builder with this entry's final preferred VM address.
__attribute__((noinline)) static uintptr_t slide() {
    uintptr_t current,preferred;
    __asm__("leaq _BE201PrivacyProbe(%%rip), %0\n\tmovabsq $0xBE201BE201BE201B, %1"
            : "=r"(current),"=r"(preferred));
    return current-preferred;
}
struct State {
    uint64_t magic;
    uint32_t phase,submissionStatus,completionStatus,capacity,malformed,callbacks;
};
static_assert(sizeof(State)==32,"reserved zero-fill state extent");
static State *state() {return reinterpret_cast<State*>(uintptr_t(0x100a69ef0)+slide());}
static bool ready() {
    uintptr_t s=slide();
    return *reinterpret_cast<const uint32_t*>(uintptr_t(0x100a69478)+s)!=0 &&
        *reinterpret_cast<const uint8_t*>(uintptr_t(0x100a4e9d4)+s)==0 &&
        *reinterpret_cast<const uintptr_t*>(uintptr_t(0x100a69230)+s)!=0 &&
        *reinterpret_cast<const uintptr_t*>(uintptr_t(0x100a4e9d8)+s)!=0;
}
static void completed(OIStatus status,void *context,NativeByteStream *stream) {
    State *p=state();
    if(context!=p || p->magic!=0x4254323031505242ULL || (p->phase!=1&&p->phase!=2))return;
    CompletionResult result=decodeStandard(status,0x202a,stream);
    p->completionStatus=status;p->malformed=result.malformed;
    p->capacity=result.hasCapacity?result.capacity:0;++p->callbacks;p->phase=3;
}
extern "C" void BE201PrivacyProbe() {
    State *p=state();
    // Unused __DATA segment tail, outside every section/fixup; fail closed if
    // nonzero. Never borrow a native client callback/global variable for state.
    const uint8_t *bytes=reinterpret_cast<const uint8_t*>(p);
    for(unsigned i=0;i<sizeof(State);i++)if(bytes[i])return;
    p->magic=0x4254323031505242ULL;p->phase=1;
    uintptr_t s=slide();
    NativeQueueAPI api={ready,
        reinterpret_cast<void*(*)(size_t)>(uintptr_t(0x1000d6f6d)+s),
        reinterpret_cast<void(*)(void*)>(uintptr_t(0x1000d6fbe)+s),
        reinterpret_cast<OIStatus(*)(uint8_t*,uint16_t,const NativeRequest*)>(uintptr_t(0x1001529ba)+s)};
    ResolvingListCommand command;command.readCapacity();
    SubmitResult result=submitStandard(api,command,completed,p);
    p->submissionStatus=result.nativeStatus;
    if(result.result!=Submission::Accepted)p->phase=4;
    else if(p->phase==1)p->phase=2; // Preserve a genuine synchronous completion.
}
