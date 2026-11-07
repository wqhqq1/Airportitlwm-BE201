#include "PrivacyRotation.hpp"
#include <cassert>
#include <cstdio>
#include <random>
using namespace be201privacy;
int main() {
    for(bool scan:{false,true})for(bool adv:{false,true}) {
        Rotation s;assert(s.begin(scan,adv,false,true,10,100));
        bool seenAddress=false;
        for(unsigned n=0;n<8 && s.phase!=Phase::Complete;n++) {
            auto r=s.next(11+n);
            if(r.action==Action::None)continue;
            assert(s.next(11+n).action==Action::None);
            assert(!s.completed({r.action,r.token+1},0));
            if(r.action==Action::SetAddress) {assert(!s.scan && !s.adv);seenAddress=true;}
            assert(s.completed(r,0));assert(!s.completed(r,0));
        }
        assert(seenAddress && s.addressApplied && !s.failed && s.phase==Phase::Complete);
        assert(s.scan==scan && s.adv==adv);
    }
    // Scan stop success, advertising stop failure: restore only the scan.
    Rotation s;assert(s.begin(true,true,false,true,0,100));auto a=s.next(1);
    assert(a.action==Action::StopScan);assert(s.completed(a,0));auto b=s.next(2);
    assert(b.action==Action::StopAdvertising);assert(s.completed(b,0x0c));
    auto c=s.next(3);assert(c.action==Action::StartScan);assert(s.completed(c,0));s.next(4);
    assert(!s.addressApplied && s.failed && s.scan && s.adv && s.phase==Phase::Complete);
    // Timeout and outside mutation never apply an address or auto-resume.
    assert(s.begin(true,false,false,true,0,10));a=s.next(1);s.next(10);
    assert(s.phase==Phase::Quarantined && !s.completed(a,0) && !s.begin(false,false,false,true,11,10));
    s.reconciled();assert(s.begin(true,false,false,true,11,10));b=s.next(12);
    assert(b.token!=a.token && !s.completed(a,0));s.externalMutation();assert(!s.completed(b,0));
    s.reconciled();assert(!s.begin(false,false,true,true,0,10));assert(!s.begin(false,false,false,false,0,10));
    assert(!s.begin(false,false,false,true,UINT64_MAX,10));
    // Adversarial callbacks, errors and stale tokens preserve the core invariant.
    std::mt19937 rng(201);unsigned addresses=0;
    for(unsigned i=0;i<20000;i++) {
        Rotation q;assert(q.begin(rng()%2,rng()%2,false,true,0,20));
        for(unsigned t=1;t<25;t++) {
            auto r=q.next(t);
            if(r.action==Action::SetAddress){assert(!q.scan && !q.adv);addresses++;}
            if(r.action==Action::None)continue;
            if(rng()%13==0)q.externalMutation();
            else if(rng()%7)q.completed(r,rng()%11?0:0x0c);
            else assert(!q.completed({r.action,r.token+999},0));
        }
    }
    assert(addresses>0);
    puts("PASS: completion-gated stop/rotate/restore, errors, timeout quarantine, stale callbacks, external mutation, 20000 adversarial schedules (offline core; native adapter not integrated).");
}
