// Standard HCI command encoder, offline only until a native callback/credit
// adapter is implemented. Keys/identity must come from the same trusted OS
// request. Never infer that binding from a name, service UUID, or nearby packet.
// All address/key inputs must already use HCI wire byte order. The native
// bluetoothd callback's address buffer is not automatically in that order.
#pragma once
#include <stdint.h>
#include <stddef.h>
namespace be201privacy {
struct Span {const uint8_t *data;size_t size;};
class ResolvingListCommand {
    uint8_t bytes_[42]={};size_t size_=0;
    static bool identity(uint8_t type,Span address) {
        if(type>1 || !address.data || address.size!=6)return false;
        bool zero=true,ones=true;
        for(unsigned i=0;i<6;i++){zero&=address.data[i]==0;ones&=address.data[i]==255;}
        if(zero||ones)return false;
        if(type==1) {
            if((address.data[5]&0xc0)!=0xc0)return false;
            bool randomZero=(address.data[5]&0x3f)==0,randomOnes=(address.data[5]&0x3f)==0x3f;
            for(unsigned i=0;i<5;i++){randomZero&=address.data[i]==0;randomOnes&=address.data[i]==255;}
            if(randomZero||randomOnes)return false;
        }
        return true;
    }
    void header(uint16_t opcode,uint8_t length){bytes_[0]=uint8_t(opcode);bytes_[1]=uint8_t(opcode>>8);bytes_[2]=length;size_=3+length;}
public:
    ResolvingListCommand()=default;
    ResolvingListCommand(const ResolvingListCommand&)=delete;
    ResolvingListCommand&operator=(const ResolvingListCommand&)=delete;
    ~ResolvingListCommand(){clear();}
    void clear(){volatile uint8_t *p=bytes_;for(size_t i=0;i<sizeof bytes_;i++)p[i]=0;size_=0;}
    const uint8_t *data()const{return bytes_;}
    size_t size()const{return size_;}
    bool add(uint8_t type,Span address,Span peerIRK,Span localIRK) {
        clear();
        if(!identity(type,address)||!peerIRK.data||peerIRK.size!=16||!localIRK.data||localIRK.size!=16)return false;
        header(0x2027,39);bytes_[3]=type;
        for(unsigned i=0;i<6;i++)bytes_[4+i]=address.data[i];
        for(unsigned i=0;i<16;i++){bytes_[10+i]=peerIRK.data[i];bytes_[26+i]=localIRK.data[i];}
        return true;
    }
    bool remove(uint8_t type,Span address) {
        clear();if(!identity(type,address))return false;header(0x2028,7);bytes_[3]=type;
        for(unsigned i=0;i<6;i++)bytes_[4+i]=address.data[i];return true;
    }
    void readCapacity(){clear();header(0x202a,0);}
    void resolution(bool enable){clear();header(0x202d,1);bytes_[3]=enable?1:0;}
};
}
