// SPDX-License-Identifier: GPL-2.0-or-later
// Passive, exact public test-service observations. No packet/address/key export.
// Accept-list entries are transient private comparison state, wiped on reset.
#pragma once
#include <stdint.h>
#include <stddef.h>
namespace be201peer {
struct Stats {
    uint64_t reports=0, malformed=0, contention=0, overflow=0;
    uint64_t testReports=0, testEventType=255, testAddressType=255;
    uint64_t testConnectable=2, testListMatch=0, testListEntries=0, testListTypeMask=0;
    uint64_t comparisonKnown=0;
};
static inline void inc(uint64_t &v){__atomic_add_fetch(&v,1,__ATOMIC_RELAXED);}
static inline void set(uint64_t &v,uint64_t n){__atomic_store_n(&v,n,__ATOMIC_RELAXED);}
struct Observer {
    struct Entry {uint8_t address[6]={};uint8_t type=0;bool used=false;};
    Entry entries[32];uint32_t lock=0;
    uint8_t testAddress[6]={},testType=0;bool testKnown=false;
    bool enter(Stats &s){if(__atomic_exchange_n(&lock,1,__ATOMIC_ACQUIRE)){inc(s.contention);return false;}return true;}
    void leave(){__atomic_store_n(&lock,0,__ATOMIC_RELEASE);}
    void compare(Stats &s){
        unsigned count=0,mask=0;bool match=false;
        for(auto &e:entries)if(e.used){count++;if(e.type<8)mask|=1U<<e.type;match|=testKnown&&e.type==testType&&equal(e.address,testAddress);}
        set(s.testListEntries,count);set(s.testListTypeMask,mask);set(s.testListMatch,match?1:0);set(s.comparisonKnown,testKnown?1:0);
    }
    static bool equal(const uint8_t *a,const uint8_t *b){for(unsigned i=0;i<6;i++)if(a[i]!=b[i])return false;return true;}
    static bool testService(const uint8_t *p,size_t n){
        const uint8_t uuid[16]={0x4d,0x8e,0xa1,0xd0,0xbe,0x20,0x41,0x01,0x8e,0x12,0,0,0,0,0,3};
        for(size_t i=0;i<n;){
            size_t len=p[i++];if(!len)return false;if(len>n-i)return false;
            if((p[i]==6 || p[i]==7) && (len-1)%16==0) {
                for(size_t k=i+1;k+16<=i+len;k+=16){
                    bool forward=true,reverse=true;
                    for(unsigned j=0;j<16;j++){forward&=p[k+j]==uuid[j];reverse&=p[k+j]==uuid[15-j];}
                    if(forward||reverse)return true;
                }
            }
            i+=len;
        }
        return false;
    }
    void command(Stats &s,const uint8_t *p,size_t n){
        if(!p || n<3 || p[2]>n-3)return;
        unsigned op=p[0]|unsigned(p[1])<<8;unsigned len=p[2];
        if(!((op==0x0c03||op==0x2010)?len==0:(op==0x2011||op==0x2012)&&len==7))return;
        if(!enter(s))return;
        if(op==0x0c03||op==0x2010){for(auto &e:entries)e=Entry{};set(s.overflow,0);if(op==0x0c03){testKnown=false;for(auto &x:testAddress)x=0;}}
        else {
            Entry *free=nullptr,*found=nullptr;
            for(auto &e:entries){if(!e.used){if(!free)free=&e;}else if(e.type==p[3]&&equal(e.address,p+4))found=&e;}
            if(op==0x2012){if(found)*found=Entry{};}
            else if(!found){if(free){for(unsigned i=0;i<6;i++)free->address[i]=p[4+i];free->type=p[3];free->used=true;}else inc(s.overflow);}
        }
        compare(s);leave();
    }
    void event(Stats &s,const uint8_t *p,size_t n){
        if(!p || n<4 || p[0]!=0x3e || p[2]!=2)return;
        if(p[1]>n-2){inc(s.malformed);return;}
        const size_t end=2+p[1];size_t at=4;
        // Validate the full multi-report event before consuming any report.
        for(unsigned i=0;i<p[3];i++){
            if(at>end || end-at<10){inc(s.malformed);return;}
            size_t size=10+p[at+8];if(size>end-at){inc(s.malformed);return;}at+=size;
        }
        if(at!=end){inc(s.malformed);return;}
        at=4;
        for(unsigned i=0;i<p[3];i++){
            const size_t len=p[at+8];inc(s.reports);
            if(testService(p+at+9,len)){
                inc(s.testReports);set(s.testEventType,p[at]);set(s.testAddressType,p[at+1]);
                set(s.testConnectable,p[at]<=1?1:p[at]<=3?0:2);
                if(enter(s)){
                    for(unsigned j=0;j<6;j++)testAddress[j]=p[at+2+j];testType=p[at+1];testKnown=true;compare(s);leave();
                }
            }
            at+=10+len;
        }
    }
};
}
