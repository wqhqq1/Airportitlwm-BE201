"""Capture awdl0 on this Mac and on the USB-connected iPhone at once. Local files only.

The phone side uses its own packet capture service over the existing USB pairing. Changes nothing on either device.
Files may hold addresses and service names, so keep them local.
"""
import datetime, json, os, plistlib, socket, ssl, struct, subprocess, sys, tempfile, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
USBMUXD = '/var/run/usbmuxd'
SECONDS = 180

def mux_message(sock, tag, payload):
    body = plistlib.dumps(payload)
    sock.sendall(struct.pack('<IIII', 16 + len(body), 1, 8, tag) + body)

def mux_reply(sock):
    head = read_exact(sock, 16)
    length = struct.unpack('<I', head[:4])[0]
    return plistlib.loads(read_exact(sock, length - 16))

def read_exact(sock, n):
    out = bytearray()
    while len(out) < n:
        chunk = sock.recv(n - len(out))
        if not chunk:
            raise ConnectionError('closed')
        out += chunk
    return bytes(out)

def mux_socket():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(USBMUXD)
    return sock

def mux_request(fields, tag=1):
    base = dict(ClientVersionString='be201', ProgName='be201', kLibUSBMuxVersion=3)
    sock = mux_socket()
    mux_message(sock, tag, {**base, **fields})
    return sock, mux_reply(sock)

def find_phone():
    sock, reply = mux_request(dict(MessageType='ListDevices'))
    sock.close()
    for device in reply.get('DeviceList', []):
        props = device.get('Properties', {})
        if props.get('ConnectionType') == 'USB':
            return device['DeviceID'], props['SerialNumber']
    return None, None

def pair_record(udid):
    sock, reply = mux_request(dict(MessageType='ReadPairRecord', PairRecordID=udid))
    sock.close()
    if 'PairRecordData' not in reply:
        raise RuntimeError('no pair record: unlock the phone and trust this Mac')
    return plistlib.loads(reply['PairRecordData'])

def connect(device_id, port):
    swapped = socket.htons(port)
    sock, reply = mux_request(dict(MessageType='Connect', DeviceID=device_id, PortNumber=swapped))
    if reply.get('Number') != 0:
        sock.close()
        raise RuntimeError(f'cannot reach phone port {port}: {reply}')
    return sock

def tls_context(record, folder):
    cert, key = Path(folder) / 'c.pem', Path(folder) / 'k.pem'
    cert.write_bytes(record['HostCertificate'])
    key.write_bytes(record['HostPrivateKey'])
    os.chmod(key, 0o600)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.load_cert_chain(str(cert), str(key))
    return ctx

def send_plist(sock, value):
    body = plistlib.dumps(value)
    sock.sendall(struct.pack('>I', len(body)) + body)

def recv_plist(sock):
    length = struct.unpack('>I', read_exact(sock, 4))[0]
    return plistlib.loads(read_exact(sock, length))

def start_pcapd(device_id, record, folder):
    """Lockdown: session, then the capture service. Returns a socket that streams packets."""
    lockdown = connect(device_id, 62078)
    send_plist(lockdown, dict(Label='be201', Request='QueryType'))
    if recv_plist(lockdown).get('Type') != 'com.apple.mobile.lockdown':
        raise RuntimeError('unexpected lockdown service')
    send_plist(lockdown, dict(Label='be201', Request='StartSession', HostID=record['HostID'], SystemBUID=record['SystemBUID']))
    session = recv_plist(lockdown)
    if 'SessionID' not in session:
        raise RuntimeError(f'lockdown refused the session: {session.get("Error")}')
    ctx = tls_context(record, folder)
    channel = ctx.wrap_socket(lockdown) if session.get('EnableSessionSSL') else lockdown
    send_plist(channel, dict(Label='be201', Request='StartService', Service='com.apple.pcapd'))
    service = recv_plist(channel)
    if 'Port' not in service:
        raise RuntimeError(f'capture service refused: {service.get("Error")}')
    sock = connect(device_id, service['Port'])
    # The lockdown session stays open for as long as the capture runs.
    return (ctx.wrap_socket(sock) if service.get('EnableServiceSSL') else sock), channel

def describe(frame, pre):
    """One line's worth of facts about an Ethernet or bare IP packet."""
    out = dict(len=len(frame))
    ip = frame
    if pre >= 14 and len(frame) >= 14:
        out['dst_mac'] = frame[:6].hex(':')
        out['src_mac'] = frame[6:12].hex(':')
        ip = frame[pre:]
    if ip and ip[0] >> 4 == 6 and len(ip) >= 40:
        out.update(src=socket.inet_ntop(socket.AF_INET6, ip[8:24]), dst=socket.inet_ntop(socket.AF_INET6, ip[24:40]), next=ip[6])
        l4 = ip[40:]
        if ip[6] == 6 and len(l4) >= 14:
            out.update(sport=int.from_bytes(l4[:2], 'big'), dport=int.from_bytes(l4[2:4], 'big'), tcp_flags=l4[13])
        elif ip[6] == 17 and len(l4) >= 4:
            out.update(sport=int.from_bytes(l4[:2], 'big'), dport=int.from_bytes(l4[2:4], 'big'))
        elif ip[6] == 58 and l4:
            out['icmp6'] = l4[0]
    return out

def parse_packet(data):
    """Device packet header, big endian but for the process ids. Returns None if it is too short."""
    if len(data) < 49:
        return None
    hdr = struct.unpack('>I', data[:4])[0]
    plen = struct.unpack('>I', data[5:9])[0]
    io = data[12]
    pre = struct.unpack('>I', data[17:21])[0]
    name = data[25:41].split(b'\0')[0].decode('ascii', 'replace')
    return dict(ifname=name, io='out' if io else 'in', pre=pre, frame=data[hdr:hdr + plen])

def phone_capture(sock, path, stop):
    counts = {}
    samples = []
    with open(path, 'w') as out:
        sock.settimeout(1)
        while not stop.is_set():
            try:
                raw = recv_plist(sock)
            except socket.timeout:
                continue
            except (OSError, ConnectionError, ssl.SSLError) as e:
                out.write(json.dumps(dict(at=time.time(), error=str(e))) + '\n')
                break
            pkt = parse_packet(raw) if isinstance(raw, bytes) else None
            if not pkt:
                continue
            counts[pkt['ifname']] = counts.get(pkt['ifname'], 0) + 1
            if pkt['ifname'].startswith(('awdl', 'llw', 'nan')):
                if len(samples) < 4:
                    samples.append(raw[:160].hex())
                row = dict(at=time.time(), ifname=pkt['ifname'], io=pkt['io'], **describe(pkt['frame'], pkt['pre']))
                out.write(json.dumps(row) + '\n')
                out.flush()
    Path(str(path) + '.interfaces.json').write_text(json.dumps(dict(counts=counts, first_headers=samples)))

def main():
    assert os.geteuid() == 0, 'Run through 开始抓包.command'
    names = subprocess.run(['ifconfig', '-l'], capture_output=True, text=True).stdout.split()
    if 'awdl0' not in names:
        sys.exit('这次开机还没有 awdl0。请先运行“开始接口实验.command”，再运行本工具。')
    device_id, udid = find_phone()
    if not device_id:
        sys.exit('没有找到 USB 连接的手机。请用线连接手机，解锁并信任这台电脑，然后再运行。')
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    uid, gid = int(os.environ.get('SUDO_UID', 0)), int(os.environ.get('SUDO_GID', 0))
    phone_path = HERE/f'capture-phone-{stamp}.jsonl'
    mac_path = HERE/f'capture-mac-{stamp}.txt'
    ndp_path = HERE/f'capture-ndp-{stamp}.txt'
    with tempfile.TemporaryDirectory() as folder:
        os.chmod(folder, 0o700)
        record = pair_record(udid)
        sock, session = start_pcapd(device_id, record, folder)
    print('手机和电脑都已开始抓包。')
    print(f'请现在在电脑访达打开“隔空投送”，10 秒后在手机上分享一张照片并停在分享面板，再互相试着发送。共 {SECONDS} 秒。')
    stop = threading.Event()
    worker = threading.Thread(target=phone_capture, args=(sock, phone_path, stop), daemon=True)
    worker.start()
    with open(mac_path, 'w') as mac_file:
        dump = subprocess.Popen(['/usr/sbin/tcpdump', '-i', 'awdl0', '-n', '-e', '-tttt', '-l', '-s', '128'],
                                stdout=mac_file, stderr=subprocess.DEVNULL)
        with open(ndp_path, 'w') as ndp_file:
            for left in range(SECONDS, 0, -5):
                ndp_file.write(f'--- {time.time()}\n' + subprocess.run(['ndp', '-an'], capture_output=True, text=True).stdout)
                ndp_file.flush()
                if left % 30 == 0:
                    print(f'还剩 {left} 秒')
                time.sleep(5)
        dump.terminate()
    stop.set()
    worker.join(5)
    sock.close()
    session.close()
    for path in HERE.glob(f'capture-*-{stamp}*'):
        os.chown(path, uid, gid)
        os.chmod(path, 0o600)
    print('已保存：', phone_path.name, mac_path.name, ndp_path.name)

if __name__ == '__main__':
    try:
        main()
    except (OSError, ConnectionError, RuntimeError, ssl.SSLError) as e:
        sys.exit(f'抓包没有开始：{e}')
