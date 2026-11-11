#include "BtIntel.h"
#include "FwData.h"
OSData *BtIntel::firmwareConvertion(OSData *original) { return OSData::withData(original); }
OSData *BtIntel::requestFirmwareData(const char *name, bool noWarn) {
    (void)noWarn; return getFWDescByName(name);
}
