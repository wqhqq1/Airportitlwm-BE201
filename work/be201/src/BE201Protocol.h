// Bounded protocol validation shared by the kernel uploader and offline tests.
#pragma once
#include <stdint.h>
#include <stddef.h>
static inline bool beDSBRParams(const uint8_t *data,size_t n,uint8_t out[2]) {
    out[0]=out[1]=0;
    if(!data || n!=5)return false;
    uint32_t raw=data[1]|((uint32_t)data[2]<<8)|((uint32_t)data[3]<<16)|((uint32_t)data[4]<<24);
    if(raw!=0 && raw!=0xf1 && raw!=0xb1)return false;
    out[0]=(uint8_t)(raw&1);out[1]=(uint8_t)((raw>>4)&15);return true;
}
static inline uint32_t beLE32(const uint8_t *p) {
    return p[0] | ((uint32_t)p[1]<<8) | ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static inline bool beTLVValid(const uint8_t *p, size_t n) {
    if (!p || !n || p[0]) return false;
    ++p; --n; uint32_t seen=0; uint8_t image=0;
    while(n) {
        if(n<2 || p[1]>n-2) return false;
        uint8_t t=p[0], l=p[1], expected=0;
        switch(t) {
            case 0x10: case 0x11: case 0x12: case 0x13: case 0x1f: case 0x32: expected=4;break;
            case 0x16: case 0x1d: expected=2;break;
            case 0x1c: case 0x1e: case 0x28: case 0x2a: case 0x2b: case 0x2c: case 0x2e: case 0x2f: expected=1;break;
            case 0x2d: expected=3;break;
            case 0x30: expected=6;break;
        }
        if(expected && l!=expected)return false;
        uint32_t bit=t==0x10?1:t==0x11?2:t==0x12?4:t==0x1c?8:t==0x2e?16:t==0x2f?32:0;
        if(bit && (seen&bit))return false;
        seen|=bit;
        if(t==0x1c)image=p[2];
        p+=2+l;n-=2+l;
    }
    return (seen&15)==15 && (image==3 || (image==1 && (seen&48)==48));
}
static inline bool beFirmwareValid(const uint8_t *b,size_t n,uint32_t *boot) {
    if(!b || n<964 || n>2*1024*1024 || beLE32(b+8)!=0x10000 || b[644]!=6 || beLE32(b+652)!=0x20000)return false;
    size_t off=964,group=0;bool found=false;
    while(off<n) {
        if(n-off<3 || b[off+2]>n-off-3)return false;
        size_t size=3+b[off+2];
        if(b[off]==0x0e && b[off+1]==0xfc) {
            if(found || b[off+2]!=7)return false;
            if(boot)*boot=beLE32(b+off+3);
            found=true;
        }
        off+=size;group+=size;
        if(!(group%4))group=0;
    }
    return found && group==0;
}
