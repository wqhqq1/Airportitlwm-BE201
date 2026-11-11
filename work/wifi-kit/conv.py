"""Rewrite an archive COPY's LZBITMAP chunksets as LZ4 so this Mac's log tool can read them."""
import struct,ctypes,glob,sys,collections
lib=ctypes.CDLL('/usr/lib/libcompression.dylib')
lib.compression_decode_buffer.restype=ctypes.c_size_t;lib.compression_encode_buffer.restype=ctypes.c_size_t
def dec(src,size,algo=0x702):
    d=ctypes.create_string_buffer(size)
    n=lib.compression_decode_buffer(d,ctypes.c_size_t(size),src,ctypes.c_size_t(len(src)),None,ctypes.c_int(algo))
    return d.raw[:n]
def enc(src):
    d=ctypes.create_string_buffer(len(src)+65536)
    n=lib.compression_encode_buffer(d,ctypes.c_size_t(len(d)),src,ctypes.c_size_t(len(src)),None,ctypes.c_int(0x100))
    assert n;return d.raw[:n]
A=sys.argv[1];stats=collections.Counter()
for f in glob.glob(A+'/Persist/*.tracev3')+glob.glob(A+'/Special/*.tracev3')+glob.glob(A+'/Signpost/*.tracev3')+glob.glob(A+'/HighVolume/*.tracev3')+glob.glob(A+'/logdata.LiveData.tracev3'):
    b=open(f,'rb').read();o=0;out=bytearray()
    while o+16<=len(b):
        tag,sub,sz=struct.unpack_from('<IIQ',b,o);body=bytearray(b[o+16:o+16+sz]);o=(o+16+sz+7)&~7
        if tag==0x600b:
            so,po,np_,co,cc=struct.unpack_from('<HHHHH',body,0);q=24+co
            sizes=[]
            for i in range(cc):
                st,en,us,al=struct.unpack_from('<QQII',body,q)
                sizes.append(us);stats[('algo',al)]+=1
                struct.pack_into('<I',body,q+20,0x100)
                q+=24;ni=struct.unpack_from('<I',body,q)[0];q+=4+ni*2;ns=struct.unpack_from('<I',body,q)[0];q+=4+ns*2;q=24+co+(((q-(24+co))+7)&~7)
            pend=sizes
        elif tag==0x600d and bytes(body[:3])==b'ZBM':
            us=pend.pop(0);r=dec(bytes(body),us)
            if len(r)!=us:stats['badlen']+=1;print(f,us,len(r))
            body=bytearray(enc(r));stats['converted']+=1
        out+=struct.pack('<IIQ',tag,sub,len(body))+body
        out+=b'\0'*((8-(len(out)%8))%8)
    open(f,'wb').write(out)
print(stats)
