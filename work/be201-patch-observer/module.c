#include <mach/mach_types.h>
#include <libkern/OSKextLib.h>
extern kern_return_t _start(kmod_info_t *, void *);
extern kern_return_t _stop(kmod_info_t *, void *);
extern kern_return_t BlueToolFixup_kern_start(kmod_info_t *, void *);
extern kern_return_t BlueToolFixup_kern_stop(kmod_info_t *, void *);
KMOD_EXPLICIT_DECL(as.acidanthera.BlueToolFixup,"2.7.6",_start,_stop)
__private_extern__ kmod_start_func_t *_realmain = BlueToolFixup_kern_start;
__private_extern__ kmod_stop_func_t *_antimain = BlueToolFixup_kern_stop;
__private_extern__ int _kext_apple_cc = __APPLE_CC__;
