// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// IOUSBHostCompletion is copied by deviceRequest. The context contains no
// request buffer, Bluetooth address, or key. The original completion is invoked
// with exactly the original owner, parameter, status and byte count.
struct BE201AddressCompletion {
    uint32_t references = 2; // submitting caller and future completion
    uint32_t claimed = 0;
    IOUSBHostCompletion original;
    uint64_t ticket;
    void (*finished)(uint64_t, IOReturn, uint32_t, bool);
    void release() {
        if (__atomic_sub_fetch(&references, 1, __ATOMIC_ACQ_REL) == 0) delete this;
    }
    static void complete(void *owner, void *parameter, IOReturn status, uint32_t bytes) {
        auto *self = static_cast<BE201AddressCompletion *>(owner);
        if (__atomic_exchange_n(&self->claimed, 1, __ATOMIC_ACQ_REL)) return;
        self->finished(self->ticket, status, bytes, true);
        self->original.action(self->original.owner, parameter, status, bytes);
        self->release();
    }
    IOUSBHostCompletion wrapped() {
        IOUSBHostCompletion result = original;
        result.owner = this; result.action = complete;
        return result;
    }
    void submitted(IOReturn result) {
        // Apple API: success schedules a completion; error schedules none.
        // The caller reference also covers a completion before the call returns.
        if (result != 0 && !__atomic_exchange_n(&claimed, 1, __ATOMIC_ACQ_REL)) {
            finished(ticket, result, 0, false); release();
        }
        release();
    }
};
