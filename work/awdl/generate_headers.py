"""Generate only declarations whose vtable positions were read from host 24G824."""
from pathlib import Path
import re,json
root=Path(__file__).resolve().parents[1]/'airportbz';out=root/'include/Airport/macOS15'
diffs=json.loads(Path(__file__).with_name('virtual-overrides.json').read_text())
paths=[out/'IO80211SkywalkInterface.h',root/'include/Airport/IOSkywalkEthernetInterface.h',root/'include/Airport/IOSkywalkNetworkInterface.h']
text='\n'.join(p.read_text() for p in paths)
protos=re.findall(r'virtual\s+([^;{}]+);',text,re.S)
old=(root.parent/'reawdl-reference/include/Airport/IO80211VirtualInterface.h').read_text()
oldprotos=re.findall(r'virtual\s+([^;{}]+);',old,re.S)
def cname(symbol):
 z=symbol.split('IO80211VirtualInterface',1)[1];m=re.match(r'(\d+)',z)
 return z[len(m[1]):len(m[1])+int(m[1])] if m else None
body=[]
for d in diffs:
 if d['slot'] in [0,1,7]:continue
 name=cname(d['virtual']);candidates=[p for p in protos if '"'+d['base']+'"' in p]
 if candidates:
  decl=candidates[0].replace(d['base'],d['virtual'])
 else:
  candidates=[p for p in protos if re.search(r'\b'+name+r'\s*\(',p)]
  if not candidates:candidates=[p for p in oldprotos if re.search(r'\b'+name+r'\s*\(',p)]
  assert candidates,(d,name)
  decl=candidates[0]
 decl=re.sub(r'\b(?:override|APPLE_KEXT_OVERRIDE)\b','',decl).strip()
 body.append('    virtual '+decl+' override; // slot '+str(d['slot']))
tail='''
    virtual bool init(IO80211Controller *, ether_addr *, unsigned, const char *);
    virtual void setLinkState(IO80211LinkState, unsigned);
    virtual void forwardPacket(IO80211NetworkPacket *);
    virtual void handleIoctl(ifnet_t, unsigned long, void *);
    virtual void addPeerToCache(unsigned char *);
    virtual void deletePeerFromCache(unsigned char *);
    virtual bool handleDebugCmd(apple80211_debug_command *);
    virtual void _abi_peer_slot_stats() __asm__("__ZN23IO80211VirtualInterface20getPeerSlotDataStatsEP10ether_addrbP17peerSlotDataStats");
    virtual void _abi_peer_stats() __asm__("__ZN23IO80211VirtualInterface16getPeerDataStatsEP10ether_addrbP16packetCounters_t");
    virtual void _abi_clear_peer_stats() __asm__("__ZN23IO80211VirtualInterface18clearPeerDataStatsEP10ether_addrb");
    virtual void setAwdlCurrentChannelSequenceIndex(unsigned);
    virtual bool isOutputFlowControlled();
    virtual void setOutputFlowControlled();
    virtual void clearOutputFlowControlled();
    virtual unsigned configureAQMOutput();
    virtual bool attachToBpf();
    virtual bool configureIfnet();
    virtual void reset();
    virtual void dupAndTransmitMcastPacket(IO80211NetworkPacket *, unsigned char *, unsigned char *);
    virtual void freeMulticastPacket(IO80211NetworkPacket *);
    virtual void triggerAWDLMulticastTx(unsigned, unsigned char);
    virtual void p2pMulticastTx(IO80211NetworkPacket **, unsigned);
    virtual void sendPendingPacketsToStack(IO80211NetworkPacket **, unsigned);
    virtual void freePendingPackets(IO80211NetworkPacket **, unsigned);
'''
res='\n'.join('    OSMetaClassDeclareReservedUnused(IO80211VirtualInterface, %d);'%i for i in range(16))
(out/'IO80211VirtualInterface.h').write_text('''// Sequoia 24G824 declarations. Slot map derived from the installed Boot KC.
// ReAWDL (maddog860) supplied Sonoma comparison declarations, GPL-2.0.
// Private placeholder entries are vtable declarations only and are never called.
#pragma once
#include "IO80211SkywalkInterface.h"
#include "../apple_private_spi.h"
class IO80211VirtualInterface : public IO80211SkywalkInterface {
    OSDeclareDefaultStructors(IO80211VirtualInterface)
public:
'''+ '\n'.join(body)+tail+res+'''
private:
    uint8_t _virtualExpansion[8];
};
static_assert(sizeof(IO80211VirtualInterface) == 0x120, "24G824 virtual interface layout");
''')
s=(root.parent/'reawdl-reference/include/Airport/IO80211AWDLProtocol.h').read_text()
s=s.replace('#include "IO80211VirtualInterface.h"','#include "IO80211VirtualInterface.h"\nstruct apple80211_awdl_config;')
s=s.replace('    virtual IOReturn setAWDL_RTG_PEER_STATS_CONFIG(', '    virtual IOReturn setAWDL_CONFIG(apple80211_awdl_config *) = 0;\n    virtual IOReturn setAWDL_RTG_PEER_STATS_CONFIG(')
s=s.replace('Sonoma','Sequoia 24G824')
(out/'IO80211AWDLProtocol.h').write_text(s)
# Check all known AWDL protocol wrappers against their actual indirect dispatch.
slots=json.loads(Path(__file__).with_name('awdl-method-slots.json').read_text());methods=re.findall(r'virtual IOReturn\s+(\w+)\s*\(',s)
assert len(methods)==63
checked=0
for i,name in enumerate(methods):
 hits=[int(slot) for slot,items in slots.items() if any(x['method']==name for x in items)]
 if hits:assert 500+i in hits,(name,500+i,hits);checked+=1
print('Generated VirtualInterface and AWDLProtocol; verified',checked,'native ioctl dispatch slots of 63')
