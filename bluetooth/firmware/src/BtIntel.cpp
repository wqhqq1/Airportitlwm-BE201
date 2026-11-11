/** @file
  Copyright (c) 2020 zxystd. All rights reserved.
  SPDX-License-Identifier: GPL-3.0-only
**/

//
//  BtIntel.cpp
//  IntelBluetoothFirmware
//
//  Created by zxystd on 2019/11/17.
//  Copyright © 2019 zxystd. All rights reserved.
//

#include "BtIntel.h"
#include "Log.h"

#define super OSObject
OSDefineMetaClassAndAbstractStructors(BtIntel, OSObject)

bool BtIntel::
initWithDevice(IOService *client, IOUSBHostDevice *dev)
{
    XYLog("%s\n", __PRETTY_FUNCTION__);
    if (!super::init()) {
        return false;
    }
    
    m_pUSBDeviceController = new USBDeviceController();
    if (!m_pUSBDeviceController || !m_pUSBDeviceController->init(client, dev)) {
        return false;
    }
    if (!m_pUSBDeviceController->initConfiguration()) {
        return false;
    }
    if (!m_pUSBDeviceController->findInterface()) {
        return false;
    }
    if (!m_pUSBDeviceController->findPipes()) {
        return false;
    }
    return true;
}

void BtIntel::
free()
{
    XYLog("%s\n", __PRETTY_FUNCTION__);
    OSSafeReleaseNULL(m_pUSBDeviceController);
    super::free();
}

bool BtIntel::
intelSendHCISync(HciCommandHdr *cmd, void *event, uint32_t eventBufSize, uint32_t *size, int timeout)
{
//    XYLog("%s cmd: 0x%02x len: %d\n", __PRETTY_FUNCTION__, cmd->opcode, cmd->len);
    uint8_t reply[CMD_BUF_MAX_SIZE];
    if(m_pUSBDeviceController->sendHCIRequest(cmd, (uint32_t)timeout)!=kIOReturnSuccess)return false;
    for(unsigned i=0;i<8;i++) {
        uint32_t n=0;
        if(m_pUSBDeviceController->interruptPipeRead(reply,sizeof(reply),&n,(uint32_t)timeout)!=kIOReturnSuccess)return false;
        if(n<2 || reply[1]+2!=n)return false;
        if(n==6 && reply[0]==0x0f && reply[4]==(cmd->opcode&255) && reply[5]==(cmd->opcode>>8) && reply[2]) {
            XYLog("Command 0x%04x rejected status=0x%02x\n",cmd->opcode,reply[2]);
            return false;
        }
        if(reply[0]!=0x0e || n<6 || reply[3]!=(cmd->opcode&255) || reply[4]!=(cmd->opcode>>8)) {
            XYLog("Skipping event 0x%02x while waiting for 0x%04x\n",reply[0],cmd->opcode);
            continue;
        }
        if(reply[5]!=0)return false;
        if(event && n>eventBufSize)return false;
        if(event)memcpy(event,reply,n);
        if(size)*size=n;
        return true;
    }
    return false;
}

bool BtIntel::
intelSendHCISyncEvent(HciCommandHdr *cmd, void *event, uint32_t eventBufSize, uint32_t *size, uint8_t syncEvent, int timeout)
{
    IOReturn ret;
    if ((ret = m_pUSBDeviceController->sendHCIRequest(cmd, timeout)) != kIOReturnSuccess) {
        XYLog("%s sendHCIRequest failed: %s %d\n", __FUNCTION__, m_pUSBDeviceController->stringFromReturn(ret), ret);
        return false;
    }
    for (unsigned attempt=0; attempt<16; ++attempt) {
        ret = m_pUSBDeviceController->interruptPipeRead(event, eventBufSize, size, timeout);
        if (ret != kIOReturnSuccess) {
            XYLog("%s interruptPipeRead failed: %s %d\n", __FUNCTION__, m_pUSBDeviceController->stringFromReturn(ret), ret);
            break;
        }
        if (*(uint8_t *)event == syncEvent) {
            return true;
        }
    }
    return false;
}

bool BtIntel::
intelBulkHCISync(HciCommandHdr *cmd, void *event, uint32_t eventBufSize, uint32_t *size, int timeout)
{
//    XYLog("%s cmd: 0x%02x len: %d\n", __FUNCTION__, cmd->opcode, cmd->len);
    uint8_t ack[CMD_BUF_MAX_SIZE];uint32_t n=0;
    if(m_pUSBDeviceController->bulkWrite(cmd,HCI_COMMAND_HDR_SIZE+cmd->len,(uint32_t)timeout)!=kIOReturnSuccess)return false;
    if(m_pUSBDeviceController->bulkPipeRead(ack,sizeof(ack),&n,(uint32_t)timeout)!=kIOReturnSuccess)return false;
    if(n!=6 || ack[0]!=0x0e || ack[1]!=4 || ack[3]!=(cmd->opcode&255) || ack[4]!=(cmd->opcode>>8) || ack[5])return false;
    if(event && n>eventBufSize)return false;
    if(event)memcpy(event,ack,n);
    if(size)*size=n;
    return true;
}

bool BtIntel::
securedSend(uint8_t fragmentType, uint32_t len, const uint8_t *fragment)
{
    bool ret = true;
    uint8_t buf[CMD_BUF_MAX_SIZE];
    HciCommandHdr *hciCommand = (HciCommandHdr *)buf;
    
    while (len > 0) {
        uint8_t fragment_len = (len > 252) ? 252 : len;
        
        memset(buf, 0, sizeof(buf));
        hciCommand->opcode = OSSwapHostToLittleInt16(0xfc09);
        hciCommand->len = fragment_len + 1;
        hciCommand->data[0] = fragmentType;
        memcpy(hciCommand->data + 1, fragment, fragment_len);
        
        if (!(ret = intelBulkHCISync(hciCommand, NULL, 0, NULL, HCI_INIT_TIMEOUT))) {
            XYLog("secure send failed\n");
            return ret;
        }
        
        len -= fragment_len;
        fragment += fragment_len;
    }
    
    return ret;
}

bool BtIntel::
intelVersionInfo(IntelVersion *ver)
{
    const char *variant;
    
    /* The hardware platform number has a fixed value of 0x37 and
     * for now only accept this single value.
     */
    if (ver->hw_platform != 0x37) {
        XYLog("Unsupported Intel hardware platform (%u)\n",
              ver->hw_platform);
        return false;
    }
    
    /* Check for supported iBT hardware variants of this firmware
     * loading method.
     *
     * This check has been put in place to ensure correct forward
     * compatibility options when newer hardware variants come along.
     */
    switch (ver->hw_variant) {
        case 0x0b:      /* SfP */
        case 0x0c:      /* WsP */
        case 0x11:      /* JfP */
        case 0x12:      /* ThP */
        case 0x13:      /* HrP */
        case 0x14:      /* CcP */
            break;
        default:
            XYLog("Unsupported Intel hardware variant (%u)\n",
                  ver->hw_variant);
            return false;
    }
    
    switch (ver->fw_variant) {
        case 0x06:
            variant = "Bootloader";
            break;
        case 0x23:
            variant = "Firmware";
            break;
        default:
            XYLog("Unsupported firmware variant(%02x)\n", ver->fw_variant);
            return false;
    }
    
    XYLog("%s revision %u.%u build %u week %u %u\n",
          variant, ver->fw_revision >> 4, ver->fw_revision & 0x0f,
          ver->fw_build_num, ver->fw_build_ww,
          2000 + ver->fw_build_yy);
    
    return true;
}

bool BtIntel::
intelBoot(uint32_t bootAddr)
{
    uint8_t buf[CMD_BUF_MAX_SIZE];
    uint32_t actLen = 0;
    HciResponse *resp = (HciResponse *)buf;
    
    if (!sendIntelReset(bootAddr)) {
        XYLog("Intel Soft Reset failed\n");
        // Leave failed device for the next cold boot.
        return false;
    }
    
    /* The bootloader will not indicate when the device is ready. This
     * is done by the operational firmware sending bootup notification.
     *
     * Booting into operational firmware should not take longer than
     * 1 second. However if that happens, then just fail the setup
     * since something went wrong.
     */
    IOReturn ret = m_pUSBDeviceController->interruptPipeRead(buf, sizeof(buf), &actLen, 1000);
    if (ret != kIOReturnSuccess || actLen <= 0) {
        XYLog("Intel boot failed\n");
        if (ret == kIOReturnTimeout) {
            XYLog("Reset to bootloader\n");
            // Leave failed device for the next cold boot.
        }
        return false;
    }
    if (actLen >= 3 && resp->evt.evt == 0xff && resp->numCommands == 0x02) {
        XYLog("Notify: Device reboot done\n");
        return true;
    }
    return false;
}

bool BtIntel::
loadDDCConfig(const char *ddcFileName)
{
    const uint8_t *fw_ptr;
    uint8_t buf[CMD_BUF_MAX_SIZE];
    HciCommandHdr *cmd = (HciCommandHdr *)buf;
    
    OSData *fwData = requestFirmwareData(ddcFileName);
    
    if (fwData == NULL) {
        XYLog("DDC file not found: %s\n", ddcFileName);
        return false;
    }
    
    XYLog("Load DDC config: %s %d\n", ddcFileName, fwData->getLength());
    
    fw_ptr = (uint8_t *)fwData->getBytesNoCopy();
    
    /* DDC file contains one or more DDC structure which has
     * Length (1 byte), DDC ID (2 bytes), and DDC value (Length - 2).
     */
    while (fwData->getLength() > fw_ptr - (uint8_t *)fwData->getBytesNoCopy()) {
        size_t remaining=fwData->getLength()-(size_t)(fw_ptr-(const uint8_t *)fwData->getBytesNoCopy());
        size_t recordSize=(size_t)fw_ptr[0]+1;
        if(recordSize>remaining || recordSize>CMD_BUF_MAX_SIZE-sizeof(HciCommandHdr) || recordSize<3){ OSSafeReleaseNULL(fwData); return false; }
        uint8_t cmd_plen = (uint8_t)recordSize;

        cmd->opcode = OSSwapHostToLittleInt16(0xfc8b);
        cmd->len = cmd_plen;
        memcpy(cmd->data, fw_ptr, cmd->len);
        if (!intelSendHCISync(cmd, NULL, 0, NULL, HCI_INIT_TIMEOUT)) {
            XYLog("Failed to send Intel_Write_DDC\n");
            OSSafeReleaseNULL(fwData);
            return false;
        }

        fw_ptr += cmd_plen;
    }
    OSSafeReleaseNULL(fwData);
    
    XYLog("Load DDC config done\n");
    return true;
}
