// Offline transaction core. Not hooked to USB or bluetoothd yet.
// A native adapter must supply real, owned HCI completions and serialize external
// scan/advertising requests. A return from command submission is not completion.
#pragma once
#include <stdint.h>

namespace be201privacy {
enum class Action { None, StopScan, StopAdvertising, SetAddress, StartAdvertising, StartScan };
enum class Phase { Idle, Busy, Restoring, Complete, Quarantined };
struct Request { Action action; uint64_t token; };
struct Rotation {
    Phase phase=Phase::Idle;
    Action pending=Action::None;
    uint64_t generation=0, serial=0, token=0, deadline=0;
    bool scan=false, adv=false, restoreScan=false, restoreAdv=false;
    bool addressApplied=false, failed=false;

    bool begin(bool scanOn,bool advOn,bool initiating,bool stateKnown,uint64_t now,uint64_t timeout) {
        if(phase!=Phase::Idle && phase!=Phase::Complete)return false;
        if(!stateKnown || initiating || !timeout || UINT64_MAX-now<timeout || generation==UINT64_MAX)return false;
        ++generation;phase=Phase::Busy;pending=Action::None;deadline=now+timeout;
        scan=scanOn;adv=advOn;restoreScan=restoreAdv=false;addressApplied=failed=false;
        return true;
    }
    Request next(uint64_t now) {
        if(phase!=Phase::Busy && phase!=Phase::Restoring)return {Action::None,0};
        if(now>=deadline) {
            // In-flight timeout leaves actual controller state unknown. Never
            // guess it, reuse its token, or continue with a new address.
            failed=true;phase=Phase::Quarantined;return {Action::None,0};
        }
        if(pending!=Action::None)return {Action::None,0};
        Action a=Action::None;
        if(phase==Phase::Busy) {
            if(scan)a=Action::StopScan;
            else if(adv)a=Action::StopAdvertising;
            else if(!addressApplied)a=Action::SetAddress;
            else phase=Phase::Restoring;
        }
        if(phase==Phase::Restoring) {
            if(restoreAdv)a=Action::StartAdvertising;
            else if(restoreScan)a=Action::StartScan;
            else phase=Phase::Complete;
        }
        if(a==Action::None)return {a,0};
        if(serial==UINT64_MAX) {phase=Phase::Quarantined;failed=true;return {Action::None,0};}
        pending=a;token=++serial;return {a,token};
    }
    bool completed(Request r,uint8_t hciStatus) {
        if((phase!=Phase::Busy && phase!=Phase::Restoring) ||
           r.action==Action::None || r.action!=pending || r.token!=token)return false;
        pending=Action::None;
        if(hciStatus) {
            failed=true;
            // Failure restoring a resource requires reconciliation, not retries
            // that may overwrite another native request or loop indefinitely.
            if(phase==Phase::Restoring)phase=Phase::Quarantined;
            else phase=Phase::Restoring;
            return true;
        }
        switch(r.action) {
        case Action::StopScan:scan=false;restoreScan=true;break;
        case Action::StopAdvertising:adv=false;restoreAdv=true;break;
        case Action::SetAddress:addressApplied=true;phase=Phase::Restoring;break;
        case Action::StartAdvertising:adv=true;restoreAdv=false;break;
        case Action::StartScan:scan=true;restoreScan=false;break;
        default:break;
        }
        return true;
    }
    void externalMutation() {
        if(phase==Phase::Busy || phase==Phase::Restoring) {
            failed=true;phase=Phase::Quarantined;
        }
    }
    // Only a native adapter that has reconciled/reset controller state may reset
    // quarantine. Keep serial monotonic to reject completions from older work.
    void reconciled() {phase=Phase::Idle;pending=Action::None;}
};
}
