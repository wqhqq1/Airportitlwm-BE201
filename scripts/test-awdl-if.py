#!/usr/bin/env python3
"""Source checks for the default-off AWDL create-request probe (1.1.19)."""
from pathlib import Path
import re
R = Path(__file__).resolve().parent.parent
v = (R/'AirportItlwm/AirportItlwmV2.cpp').read_text()
i = v.index('getCARD_CAPABILITIES(OSObject *object,'); f = v[i:v.index('getDRIVER_VERSION(OSObject *object,', i)]
a = f.index('ItlDiagnosticFlag("be201_awdl_if")'); assert 'cd->capabilities[4] |= 0x01;' in f[a:a+220]
assert a < f.index('#else'), 'capability only on the WCL path'
assert f.count('capabilities[4] |= 0x01') == 1
s = (R/'AirportItlwm/AirportItlwmSkywalkInterface.cpp').read_text()
i = s.index('AirportItlwmSkywalkInterface::setVIRTUAL_IF_CREATE'); f = s[i:s.index('const char* hexdump', i)]
assert 'return kIOReturnUnsupported;' in f and 'kIOReturnSuccess' not in f and 'ItlDiagnosticFlag("be201_awdl_if")' in f
assert 'char name[IFNAMSIZ + 1]' in f
h = (R/'AirportItlwm/AirportItlwmSkywalkInterface.hpp').read_text()
assert re.search(r'setVIRTUAL_IF_CREATE\(apple80211_virt_if_create_data \*\) AIRPORT_SKYWALK_OVERRIDE;', h)
print('PASS: capability bit 32 only with the boot argument on the WCL path; create request recorded, bounded and still refused')
