#include "NativeCommandQueue.hpp"
// Freestanding native-stack payload entry. No absolute Apple addresses and no
// transport access. The future verified binding supplies all four native hooks.
extern "C" be201privacy::SubmitResult BE201SubmitStandard(
    const be201privacy::NativeQueueAPI *api,
    const be201privacy::ResolvingListCommand *command,
    be201privacy::NativeCompletion callback,void *context) {
    if(!api||!command)return {be201privacy::Submission::Invalid,0};
    return be201privacy::submitStandard(*api,*command,callback,context);
}
extern "C" be201privacy::CompletionResult BE201DecodeStandard(
    be201privacy::OIStatus status,uint16_t opcode,
    const be201privacy::NativeByteStream *stream) {
    return be201privacy::decodeStandard(status,opcode,stream);
}
