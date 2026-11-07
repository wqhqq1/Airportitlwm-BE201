"""Build an offline freestanding x86_64 module; never installs or loads it."""
from pathlib import Path
import subprocess,struct,json,hashlib,sys
W=Path(__file__).resolve().parent
sys.path.insert(0,str(W.parent/'awdl/python-deps'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_IMM,X86_OP_MEM,X86_REG_RIP
flags=['-std=c++17','-arch','x86_64','-Oz','-ffreestanding','-fno-builtin',
 '-fno-stack-protector','-fno-exceptions','-fno-rtti','-fvisibility=hidden',
 '-fvisibility-inlines-hidden','-Wall','-Wextra','-Werror']
subprocess.run(['clang++',*flags,'-c',str(W/'AuthenticatedRPA.cpp'),'-o',str(W/'authenticated-rpa.o')],check=True)
subprocess.run(['ld','-static','-arch','x86_64','-e','_BE201ResolveRPA','-no_uuid',
 '-o',str(W/'authenticated-rpa.macho'),str(W/'authenticated-rpa.o')],check=True)
b=(W/'authenticated-rpa.macho').read_bytes();at=32;sections=[];symbols={};relocations=0;dependencies=[]
for _ in range(struct.unpack_from('<I',b,16)[0]):
 cmd,n=struct.unpack_from('<II',b,at)
 if cmd==0x19:
  for i in range(struct.unpack_from('<I',b,at+64)[0]):
   s=at+72+i*80;name=b[s:s+16].rstrip(b'\0').decode();vm,size=struct.unpack_from('<QQ',b,s+32);off=struct.unpack_from('<I',b,s+48)[0]
   relocations+=struct.unpack_from('<I',b,s+60)[0];sections.append({'name':name,'vm':vm,'size':size,'offset':off})
 if cmd==2:symoff,nsyms,stroff,strsize=struct.unpack_from('<IIII',b,at+8)
 if cmd in (0xc,0x80000018,0x8000001f):dependencies.append(cmd)
 at+=n
for i in range(nsyms):
 strx,t,sect,desc,value=struct.unpack_from('<IBBHQ',b,symoff+16*i)
 name=b[stroff+strx:b.index(0,stroff+strx)].decode()
 assert not(t&0xe==0 and name),('undefined',name)
 if name.startswith('_BE201'):symbols[name]=value
text=next(x for x in sections if x['name']=='__text');assert relocations==0 and not dependencies
assert all(x['name']=='__text' or x['size']==0 for x in sections),sections
code=b[text['offset']:text['offset']+text['size']];md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
instructions=list(md.disasm(code,text['vm']));assert sum(i.size for i in instructions)==len(code)
for i in instructions:
 for op in i.operands:
  if op.type==X86_OP_MEM and op.mem.base==X86_REG_RIP:
   assert text['vm']<=i.address+i.size+op.mem.disp<text['vm']+len(code),'external RIP-relative data'
 if (i.mnemonic=='call' or i.mnemonic.startswith('j')) and i.operands[0].type==X86_OP_IMM:
  assert text['vm']<=i.operands[0].imm<text['vm']+len(code),'external direct branch'
marker=bytes(16)
preferred=0x1009d9a10+len(marker)+symbols['_BE201ResolveRPA']-text['vm']
sentinel=struct.pack('<Q',0xBE201BE201BE201B);assert code.count(sentinel)==1
code=code.replace(sentinel,struct.pack('<Q',preferred))
marker=hashlib.sha256(code).digest()[:8]+bytes(8)
payload=marker+code
assert len(payload)<=0x5f0,('payload does not fit pinned executable padding',len(payload))
(W/'authenticated-rpa-code.bin').write_bytes(code)
(W/'authenticated-rpa-payload.bin').write_bytes(payload)
layout={'text':text,'entries':symbols,'relocations':relocations,'dependencies':dependencies,
 'code_sha256':hashlib.sha256(code).hexdigest(),'preferred_entry':preferred,'payload_vm':0x1009d9a10,'payload_size':len(payload),'state_vm':0x100a69f00,'state_size':232}
(W/'authenticated-rpa-layout.json').write_text(json.dumps(layout,indent=2)+'\n')
manifest={'clang':subprocess.check_output(['clang++','--version'],text=True).splitlines()[0],
 'compiler_flags':flags,'unicorn':'2.1.4','native_fixture_sha256':'8272d7fcd7bd72d07ef0d09f6c7e4d51985e5c38996c59014f713397cae6dd63',
 'instructions':len(instructions),'code_size':len(code),'undefined_symbols':[],
 'all_direct_branches_internal':True,'external_rip_data':False,'deployment':False}
(W/'authenticated-rpa-build.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS: authenticated recent RPA routing module;',len(code),'bytes, no imports, dependencies, data sections, external RIP references or external direct branches.')
