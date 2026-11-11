from pathlib import Path
import re,plistlib
w=Path(__file__).resolve().parent;s=w/'src'
def edit(n,f):
 p=s/n;p.write_text(f(p.read_text()))
edit('IntelBluetoothFirmware.cpp',lambda t:t.replace('#include <libkern/OSTypes.h>','#include <libkern/OSTypes.h>\n#include <pexpert/pexpert.h>').replace('    XYLog("Driver Probe()\\n");','    int disabled=0;\n    if (PE_parse_boot_argn("-be201off", &disabled, sizeof(disabled))) return NULL;\n    XYLog("Driver Probe()\\n");').replace('productID == 0x0036 || productID == 0x0038','productID == 0x0036 || productID == 0x0037 || productID == 0x0038').replace('stop(this);','PMstop();\n        super::stop(provider);').replace('setProperty("fw_name", OSString::withCString(fwName));','setProperty("fw_name", fwName);'))
def gen3(t):
 t=t.replace('#include "linux.h"','#include "linux.h"\n#include "BE201Protocol.h"')
 t=t.replace('actLen - 5 <= 0 || actLen - 5 > CMD_BUF_MAX_SIZE','actLen <= 5 || actLen > CMD_BUF_MAX_SIZE || resp->evt.evt != 0x0e || OSSwapLittleToHostInt16(resp->opcode) != 0xfc05')
 # This build matches only BE201, with its exact measured platform and firmware name.
 a=t.index('    /* For Legacy device, check');b=t.index('    /* memset ver_tlv',a)
 t=t[:a]+t[b:]
 a=t.index('    if (INTEL_HW_PLATFORM(verTLV.cnvi_bt)');b=t.index('    return true;\n}',a)
 t=t[:a]+'''    char expected[64];
    getFirmware(&verTLV, expected, sizeof(expected), "sfi");
    if (INTEL_HW_PLATFORM(verTLV.cnvi_bt) != 0x37 ||
        INTEL_HW_VARIANT(verTLV.cnvi_bt) != 0x1d ||
        strcmp(expected, "ibt-0093-0291.sfi") || !versionInfoTLV(&verTLV)) {
        XYLog("BE201 hardware/firmware guard refused device\\n");
        return false;
    }
    if (!bootloaderSetupTLV(&verTLV)) return false;
'''+t[b:]
 t=t.replace('case 0x1c:    /* Gale Peak (GaP) */','case 0x1c:    /* Gale Peak (GaP) */\n        case 0x1d:    /* BlazarU / BE201 */')
 t=t.replace('    versionInfoTLV(&newVerTLV);','    if (newVerTLV.img_type != 3 || !versionInfoTLV(&newVerTLV)) return false;')
 # Do not downgrade operational firmware or repeatedly reset failed hardware.
 t=t.replace('    getFirmware(ver, fwname, sizeof(fwname), "sfi");','    getFirmware(ver, fwname, sizeof(fwname), "sfi");\n    if (firmwareMode) { strlcpy(loadedFirmwareName, fwname, sizeof(loadedFirmwareName)); return true; }')
 t=t.replace('        resetToBootloader();\n        goto done;','        ret = false;\n        goto done;').replace('        resetToBootloader();\n        ret = false;','        ret = false;')
 t=t.replace('if (fwData->getLength() < 644)', 'if (!beFirmwareValid((const uint8_t *)fwData->getBytesNoCopy(), fwData->getLength(), bootParams))')
 t=t.replace('if (resp->evt.evt == 0xff && resp->numCommands == 0x06)', 'if (actSize >= 7 && resp->evt.evt == 0xff && resp->evt.len + 2 == actSize && resp->numCommands == 0x06 && ((uint8_t *)resp)[3] == 0 && ((uint8_t *)resp)[6] == 0)')
 t=t.replace('    IntelTLV *tlv;','    IntelTLV *tlv;\n    if (len <= 0 || !beTLVValid(versionDataPtr, (size_t)len)) return false;')
 t=t.replace('memcpy(&version->otp_bd_addr, tlv->val, tlv->len);','memcpy(&version->otp_bd_addr, tlv->val, sizeof(version->otp_bd_addr));')
 t=t.replace('    parseVersionTLV(version, versionDataPtr, len);\n    \n    return true;','    return parseVersionTLV(version, versionDataPtr, len);')
 return t
edit('IntelBluetoothOpsGen3.cpp',gen3)
def gen2(t):
 t=t.replace('#include "linux.h"','#include "linux.h"\n#include "BE201Protocol.h"')
 a=t.index('    XYLog("send firmware payload');b=t.index('\nbool IntelBluetoothOpsGen2::\nshutdown()',a)
 t=t[:a]+'''    const uint8_t *bytes=(const uint8_t *)fwData->getBytesNoCopy();
    size_t total=fwData->getLength(), cursor=offset, group=offset;
    uint32_t boot=0;
    if (offset!=964 || !beFirmwareValid(bytes,total,&boot)) return false;
    while(cursor<total) {
        cursor+=3+bytes[cursor+2];
        if (!((cursor-group)%4)) {
            if (!securedSend(1,(uint32_t)(cursor-group),bytes+group)) return false;
            group=cursor;
        }
    }
    return group==total;
}

bool IntelBluetoothOpsGen2::
firmwareVersion(uint8_t num, uint8_t ww, uint8_t yy, OSData *fwData, uint32_t *bootAddr)
{
    const uint8_t *b=(const uint8_t *)fwData->getBytesNoCopy();
    if(!beFirmwareValid(b,fwData->getLength(),bootAddr))return false;
    for(size_t off=964;off<fwData->getLength();off+=3+b[off+2]) {
        if(b[off]==0x0e && b[off+1]==0xfc)
            return b[off+7]==num && b[off+8]==ww && b[off+9]==yy;
    }
    return false;
}
'''+t[b:]
 return t
edit('IntelBluetoothOpsGen2.cpp',gen2)
edit('BtIntelFw.cpp',lambda t:'''#include "BtIntel.h"
#include "FwData.h"
OSData *BtIntel::firmwareConvertion(OSData *original) { return OSData::withData(original); }
OSData *BtIntel::requestFirmwareData(const char *name, bool noWarn) {
    (void)noWarn; return getFWDescByName(name);
}
''')
edit('FwData.h',lambda t:'''#pragma once
#include <libkern/c++/OSData.h>
#include <libkern/libkern.h>
struct FwDesc { const char *name; const unsigned char *var; const long int size; };
extern const FwDesc fwList[]; extern const int fwNumber;
static inline OSData *getFWDescByName(const char *name) {
 for(int i=0;i<fwNumber;i++)if(!strcmp(name,fwList[i].name))return OSData::withBytes(fwList[i].var,(unsigned int)fwList[i].size);
 return NULL;
}
''')
edit('BtIntel.cpp',lambda t:t.replace('    do {\n        ret = m_pUSBDeviceController->interruptPipeRead','    for (unsigned attempt=0; attempt<16; ++attempt) {\n        ret = m_pUSBDeviceController->interruptPipeRead').replace('    } while (true);','    }').replace('        resetToBootloader();','        // Leave failed device for the next cold boot.').replace('            resetToBootloader();','            // No reset retry.').replace('if (resp->evt.evt == 0xff && resp->numCommands == 0x02)','if (actLen >= 3 && resp->evt.evt == 0xff && resp->numCommands == 0x02)'))
# Completion is protected by one lock, including the done predicate. Synchronous
# abort drains the callback before its stack context or backing buffer is freed.
edit('USBDeviceController.hpp',lambda t:t.replace('    int status;','    bool done;\n    int status;').replace('    IOUSBHostDevice* m_pDevice;','    uint64_t setupDeadline;\n    bool expired();\n    IOUSBHostDevice* m_pDevice;'))
def usb(t):
 t=t.replace('    m_pDevice = dev;','    clock_interval_to_deadline(30000, kMillisecondScale, &setupDeadline);\n    m_pDevice = dev;')
 t=t.replace('if(interfaceCandidate != NULL)', 'if(interfaceCandidate != NULL && interfaceCandidate->getInterfaceDescriptor()->bInterfaceNumber == 0)')
 t=t.replace('->abort();','->abort(IOUSBHostIOSource::kAbortSynchronous);')
 t=t.replace('    resp->status = status;','    IOLockLock(controller->_hciLock);\n    resp->done = true;\n    resp->status = status;').replace('    IOLockWakeup(controller->_hciLock, controller, true);','    IOLockWakeup(controller->_hciLock, controller, true);\n    IOLockUnlock(controller->_hciLock);')
 t=t.replace('    AbsoluteTime deadline;','    if(expired())return kIOReturnTimeout;\n    AbsoluteTime deadline;')
 a=t.index('        if (IOLockSleepDeadline');b=t.index('        if (interrupResp.dataLen <= 0)',a)
 t=t[:a]+'''        while (!interrupResp.done) {
            if (IOLockSleepDeadline(_hciLock, this, deadline, THREAD_UNINT) != THREAD_AWAKENED && !interrupResp.done) {
                IOLockUnlock(_hciLock);
                m_pInterruptReadPipe->abort(IOUSBHostIOSource::kAbortSynchronous);
                return kIOReturnTimeout;
            }
        }
        if (interrupResp.status != kIOReturnSuccess) {
            IOLockUnlock(_hciLock);
            return interrupResp.status;
        }
'''+t[b:]
 t=t.replace('    uint32_t actualLength = 0;','    if(expired())return kIOReturnTimeout;\n    uint32_t actualLength = 0;')
 t=t.replace('    uint32_t actualLength;','    if(expired())return kIOReturnTimeout;\n    uint32_t actualLength;')
 t=t.replace('    IOMemoryDescriptor* buffer =','    if(expired())return kIOReturnTimeout;\n    IOMemoryDescriptor* buffer =')
 t=t.replace('    return ret;\n}\n\nconst char*', '    buffer->release();\n    return actLen == length ? ret : kIOReturnUnderrun;\n}\n\nconst char*')
 t+='\nbool USBDeviceController::expired() { uint64_t now; clock_get_uptime(&now); return now>=setupDeadline; }\n'
 return t
edit('USBDeviceController.cpp',usb)
# Minimal personality: only this measured USB ID, no changes to other Intel devices.
orig=Path(__file__).resolve().parents[2]/'reference/lshbluesky-IntelBluetoothFirmware-14787a2/IntelBluetoothFirmware/Info.plist'
p=plistlib.loads(orig.read_bytes());ident='local.BE201BluetoothFirmware'
for key,val in {'CFBundleDevelopmentRegion':'English','CFBundleExecutable':'IntelBluetoothFirmware','CFBundleIdentifier':ident,'CFBundleName':'BE201BluetoothFirmware','CFBundleShortVersionString':'2.5.3','CFBundleVersion':'2.5.3'}.items():p[key]=val
p['IOKitPersonalities']={'BE201_0037':{'CFBundleIdentifier':ident,'IOClass':'IntelBluetoothFirmware','IOMatchCategory':'IntelBluetoothFirmware','IOProviderClass':'IOUSBHostDevice','IOProbeScore':4000,'idVendor':0x8087,'idProduct':0x37}}
(w/'Info.plist').write_bytes(plistlib.dumps(p,sort_keys=False))
p=w/'module.c';p.write_text(p.read_text().replace('local.NativeALSDisplay','local.BE201BluetoothFirmware').replace('"1.0.0"','"2.5.3"'))
