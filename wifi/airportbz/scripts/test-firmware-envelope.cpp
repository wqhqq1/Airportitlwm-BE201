#include "../include/ItlFirmwareEnvelope.hpp"
#include <cassert>
#include <fstream>
#include <iterator>
#include <vector>
#include <random>
#include <cstdio>
int main() {
    for (const char *name : {"firmware-bz92/iwlwifi-bz-b0-fm-c0-92.ucode", "firmware-bz92/iwlwifi-bz-b0-fm-c0.pnvm"}) {
        std::ifstream f(name,std::ios::binary);
        std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(f)),{});
        size_t prefix=bytes.size()>1000000?88:0;
        assert(bytes.size()>prefix+8);
        assert(ItlFirmwareEnvelopeValid(bytes.data()+prefix,bytes.size()-prefix));
        // Every incomplete header, oversized payload and missing final pad is rejected.
        for (size_t offset=prefix;offset<bytes.size();) {
            const size_t length=ItlReadLE32(bytes.data()+offset+4);
            const size_t total=8+length+((4-(length&3))&3);
            for (size_t n=1;n<8;++n)assert(!ItlFirmwareEnvelopeValid(bytes.data()+offset,n));
            if (length)assert(!ItlFirmwareEnvelopeValid(bytes.data()+offset,8+length-1));
            auto damaged=std::vector<uint8_t>(bytes.begin()+offset,bytes.begin()+offset+total);
            for(unsigned j=4;j<8;++j)damaged[j]=255;
            assert(!ItlFirmwareEnvelopeValid(damaged.data(),damaged.size()));
            offset+=total;
        }
    }
    uint8_t padded[12]={1,0,0,0,1,0,0,0,42,0,0,0};
    assert(ItlFirmwareEnvelopeValid(padded,12));
    for(size_t n=8;n<12;++n)assert(!ItlFirmwareEnvelopeValid(padded,n));
    assert(!ItlFirmwareEnvelopeValid(nullptr,12));
    std::mt19937 rng(201);
    std::vector<uint8_t> fuzz(4096);
    for(unsigned i=0;i<100000;++i) {
        size_t n=rng()%fuzz.size();
        for(size_t j=0;j<n;++j)fuzz[j]=rng();
        (void)ItlFirmwareEnvelopeValid(fuzz.data(),n);
    }
    puts("PASS: real BE201 API92 firmware/PNVM, truncated headers/payloads, oversized lengths, missing padding, null input and 100000 ASan/UBSan random buffers.");
}
