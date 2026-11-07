// Non-instantiable declarations for 24G824's native management buffer pool.
// Buffer storage/ownership stays with the family's pool. No private fields are accessed.
#pragma once
class IO80211Buffer {
public:
    unsigned long getCapacity() const;
    unsigned long writeBytes(unsigned long, const void *, unsigned long);
    void setLength(unsigned long);
    void returnBuffer();
};
class IO80211BufferPool : public OSObject {
public:
    // OSObject has 35 slots; the native getBuffer is slot 35 / offset 0x118.
    virtual IO80211Buffer *getBuffer();
};
