#pragma once
#include <Headers/kern_util.hpp>

// Since BlueToolFixup 2.7.12 / IntelBTPatcher 2.5.10 the BE201 switches this machine used are on without boot
// arguments: -btlfxa2dpcheck -be201identity -be201leadv -be201addrpause -be201lebaseline -be201nativeaddr
// -be201btprobe -be201rparoute. -be201btstock turns all of them off; naming one with it turns that one back on.
// The other switches (-be201privacyprobe, -be201peeraddr, -btlfx*) still need their boot argument.
static inline bool be201Switch(const char *name) {
    return checkKernelArgument(name) || !checkKernelArgument("-be201btstock");
}
