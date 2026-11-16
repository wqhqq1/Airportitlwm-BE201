// Non-instantiable declarations for the native management buffer pool.
// Buffer storage/ownership stays with the family's pool. No private fields are accessed.
#pragma once
#if __IO80211_TARGET == __MAC_26_0
/*
 * 1.4.2, 25G342: IO80211Buffer is a virtual interface (slots 35-53 after OSObject's 35), and the management frame
 * pool is an IO80211MallocBufferPool (IO80211Controller::allocFramePool passes true to withOptions) whose
 * IO80211MallocBuffer overrides every one of them. 1.4.1 called the base implementations directly, as on 24G824,
 * and IO80211Buffer::getCapacity followed base-class internals the malloc buffer does not have: page fault at 0x10
 * in AirportItlwmAWDLInterface::inputActionFrame on the first AWDL action frame (Kernel-2026-11-15-080618.panic;
 * also why 1.4.0, which armed AWDL at boot, never finished booting). Calls now go through the vtable.
 * Order and slots from the 25G342 boot KC __ZTV13IO80211Buffer / __ZTV19IO80211MallocBuffer.
 */
class IO80211Buffer : public OSObject {
public:
    virtual void returnBuffer();                                            // 35
    virtual void _abi_zero();                                               // 36 zero()
    virtual void _abi_isZero();                                             // 37 isZero() const
    virtual unsigned long getLength() const;                                // 38
    virtual void setLength(unsigned long);                                  // 39
    virtual unsigned long getCapacity() const;                              // 40
    virtual void _abi_getCursor();                                          // 41
    virtual void _abi_getCursorConst();                                     // 42
    virtual void _abi_getBytesNoCopy();                                     // 43
    virtual void _abi_getBytesNoCopyRange();                                // 44
    virtual void _abi_getBytesNoCopyConst();                                // 45
    virtual void _abi_getBytesNoCopyRangeConst();                           // 46
    virtual unsigned long writeBytes(unsigned long, const void *, unsigned long);  // 47
};
#else
class IO80211Buffer {
public:
    unsigned long getCapacity() const;
    unsigned long writeBytes(unsigned long, const void *, unsigned long);
    void setLength(unsigned long);
    void returnBuffer();
};
#endif
class IO80211BufferPool : public OSObject {
public:
    // OSObject has 35 slots; the native getBuffer is slot 35 / offset 0x118.
    virtual IO80211Buffer *getBuffer();
};
