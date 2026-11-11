"""Compile-only AWDL ABI fixture. Never link/load this fixture as a kext."""
from pathlib import Path
import os,json,re,subprocess,hashlib
root=Path(__file__).resolve().parents[1]
out=root/'build/awdl-vif-abi';out.mkdir(parents=True,exist_ok=True)
native=json.loads((root/'tests/abi/sequoia-24G824-awdl.json').read_text())
sdk=Path(os.environ['MAC_KERNEL_SDK'])
fixture = '#include "AirportItlwmAWDLInterface.cpp"\n'
source=out/'fixture.cpp';source.write_text(fixture)
flags=['-target','x86_64-apple-macos15.2','-mkernel','-fapple-kext',
 '-fno-sized-deallocation','-fno-use-cxa-atexit','-fno-exceptions','-fno-rtti',
 '-mno-red-zone','-mcmodel=kernel','-nostdinc','-std=gnu++14','-D__PRIVATE_SPI__',
 '-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-DIEEE80211_STA_ONLY',
 '-DAIRPORT','-DAIRPORT_WCL','-DAIRPORT_VTD','-DIO80211FAMILY_V2','-D__IO80211_TARGET=150200',
 '-isystem',str(sdk/'Headers'),'-isystem',subprocess.check_output(['clang','-print-resource-dir'],text=True).strip()+'/include']
for p in ['.','itlwm','itlwm/hal_iwx','itl80211','itl80211/openbsd','itl80211/linux','include','include/Airport','AirportItlwm']:
 flags+=['-I',str(root/p)]
flags+=['-include',str(root/'itlwm/PrivateSPI.pch'),'-Wno-deprecated-register','-Wno-multichar']
with (out/'clang-vtables.txt').open('w') as f:
 rc=subprocess.run(['clang++',*flags,'-Xclang','-fdump-vtable-layouts','-c',str(source),'-o',str(out/'fixture.o')],stdout=f,stderr=subprocess.STDOUT)
text=(out/'clang-vtables.txt').read_text()
if rc.returncode:
 print(text[-10000:]);raise SystemExit(rc.returncode)
start=text.index("Vtable for 'AirportItlwmAWDLInterface'");end=text.find('\nVtable for ',start+1)
table=text[start:end if end>=0 else len(text)]
pool_start=text.index("Vtable for 'IO80211BufferPool'")
pool_end=text.index('VTable indices for',pool_start)
assert re.search(r'^\s*37 \| IO80211Buffer \*IO80211BufferPool::getBuffer\(\)',text[pool_start:pool_end],re.M), 'native management pool getBuffer must stay at slot 35'
symbols=[r['symbol'] for r in native['slots']]
demangled=subprocess.check_output(['c++filt','-n'],input='\n'.join(s[1:] for s in symbols)+'\n',text=True).splitlines()
headers='\n'.join(p.read_text() for p in (root/'include/Airport/macOS15').glob('*.h'))
alias_pairs=re.findall(r'void (\w+)\(\) __asm__\("([^"]+)"\)',headers)
alias_names=subprocess.check_output(['c++filt','-n'],input='\n'.join(m[1:] for _,m in alias_pairs)+'\n',text=True).splitlines()
aliases={a:d.split('::',1)[1].split('(')[0] for (a,_),d in zip(alias_pairs,alias_names)}
for i,(r,demangle) in enumerate(zip(native['slots'],demangled)):
 line=re.search(r'^\s*'+str(i+2)+r' \| (.*)$',table,re.M)
 assert line,(i,r)
 got=line[1].split('::',1)[1].split('(')[0];got=aliases.get(got,got)
 if r['symbol']=='___cxa_pure_virtual':
  expected='setMacAddress' if i==415 else native['methods'][i-500]['name']
 else:expected=demangle.split('::',1)[1].split('(')[0]
 if got.startswith('~'):got='~destructor'
 if expected.startswith('~'):expected='~destructor'
 assert got==expected,(hex(i*8),got,expected)
symbols_path=Path(os.environ.get('NATIVE_KERNEL_SYMBOLS',str(root.parents[1]/'deps/system-symbols-24G824.txt')))
available={fields[-1] for line in symbols_path.read_text().splitlines()
           if len(fields:=line.split())>=3 and fields[-2]!='U'}
required=set(subprocess.check_output(['nm','-u',str(out/'fixture.o')],text=True).split())
# AirportItlwm's own methods come from AirportItlwmV2.cpp, which this fixture does not compile.
missing=sorted(x for x in required-available if not x.startswith('__ZN12AirportItlwm'))
assert not missing,('AWDL symbols absent from native kernel collection',missing)
report={'os_build':native['os_build'],'native_uuid':native['native_uuid'],
 'object_size':native['object_size'],'slots_checked':len(native['slots']),
 'typed_awdl_handlers':len(native['methods']),'all_dispatch_positions_match':True,
 'fixture_loaded':False,'runtime_interface_created':False, 'concrete_class':'AirportItlwmAWDLInterface',
 'native_imports_checked':len(required),'missing_native_imports':missing,
 'kernel_symbols_sha256':hashlib.sha256(symbols_path.read_bytes()).hexdigest()}
report['management_pool_get_buffer_slot']=35
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS:',len(native['slots']),'Sequoia native dispatch slots,',len(native['methods']),'typed AWDL handlers and',len(required),'native imports; actual AWDL concrete class compiled, not loaded.')
