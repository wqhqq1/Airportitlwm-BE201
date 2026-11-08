"""1.1.57 (1.1.54 content): AirDrop and peer latency with a second channel beside the router link. RAM switches only; the second
channel is off again at the end, in the safe order. The speed-up (own queue, aggregation) stays at its default."""
import datetime, re, subprocess, sys, threading, time
from pathlib import Path
PHY2, TE = 'debug.be201_awdl_phy2', 'debug.be201_awdl_phy2_te'
SECONDS = 20
KEYS = ['Phy2Chan', 'Phy2Err', 'Phy2Switches', 'Phy2Auto', 'Phy2AutoChanges', 'SeqChan5', 'RxPhy2', 'RxHome',
        'CtxTeRequests', 'CtxTeStarted', 'CtxTeEnded', 'CtxTeFailed', 'CtxTeRemoved', 'CtxTeOwn',
        'OwnSent', 'OwnOk', 'OwnFail', 'OwnHeld', 'OwnAgg', 'OwnRecovers', 'OwnRetargets', 'TxTripped', 'DataTx', 'DataRx']
COUNTERS = ['Phy2Switches', 'RxPhy2', 'RxHome', 'CtxTeRequests', 'CtxTeStarted', 'CtxTeEnded', 'CtxTeFailed', 'CtxTeRemoved',
            'CtxTeOwn', 'OwnSent', 'OwnOk', 'OwnFail', 'OwnRecovers', 'OwnRetargets', 'DataTx', 'DataRx']

def run(*a, timeout=60):
    return subprocess.run(a, capture_output=True, text=True, timeout=timeout)

def ioreg():
    return run('ioreg', '-l', '-w0').stdout

def props(text=None):
    text = text or ioreg()
    out = {k: int(m[1]) for k in KEYS if (m := re.search(rf'"ItlwmAwdl{k}" = (\d+)', text))}
    m = re.search(r'"ItlwmFwErrors" = (\d+)', text)
    out['FwErrors'] = int(m[1]) if m else 0
    return out

def own_sequence(text=None):
    # The 16 slots this Mac advertises, as the family set them: channel numbers only.
    m = re.search(r'"ItlwmAwdlPayload535" = <([0-9a-f]+)>', text or ioreg())
    if not m:
        return '未知'
    raw = bytes.fromhex(m[1])
    return ' '.join(str(int.from_bytes(raw[12 + 12 * i + 4:12 + 12 * i + 8], 'little')) for i in range(16) if len(raw) >= 24 + 12 * i)

def obytes():
    for line in run('netstat', '-I', 'awdl0', '-b').stdout.splitlines():
        f = line.split()
        if len(f) >= 10 and f[0] == 'awdl0' and f[2].startswith('<Link'):
            return int(f[9])
    return 0

def setv(oid, value):
    run('sysctl', '-w', f'{oid}={value}')

def gateway():
    for line in run('route', '-n', 'get', 'default').stdout.splitlines():
        if 'gateway:' in line:
            return line.split()[-1]

def summary(out):
    loss = re.search(r'([\d.]+)% packet loss', out)
    avg = re.search(r'= [\d.]+/([\d.]+)/([\d.]+)', out)
    return f"丢包 {loss[1] if loss else '?'}%，平均 {avg[1] if avg else '?'} ms，最大 {avg[2] if avg else '?'} ms"

def peers():
    # A multicast echo fills the neighbor table with this Mac's awdl0 peers.
    run('ping6', '-c', '2', '-i', '0.5', 'ff02::1%awdl0', timeout=10)
    out = []
    for line in run('ndp', '-an').stdout.splitlines():
        f = line.split()
        if f and '%awdl0' in f[0] and f[0].startswith('fe80') and 'permanent' not in line and f[1] != '(incomplete)':
            out.append(f[0])
    return out

def phase(name, lines, peer):
    a, b0 = props(), obytes()
    res = {}
    def pinger(key, cmd):
        res[key] = run(*cmd, timeout=SECONDS + 15).stdout
    jobs = []
    gw = gateway()
    if gw:
        jobs.append(threading.Thread(target=pinger, args=('gw', ['ping', '-c', str(SECONDS * 2), '-i', '0.5', '-t', str(SECONDS + 3), gw])))
    if peer:
        jobs.append(threading.Thread(target=pinger, args=('peer', ['ping6', '-c', str(SECONDS * 2), '-i', '0.5', peer])))
    for j in jobs:
        j.start()
    time.sleep(SECONDS)
    for j in jobs:
        j.join()
    text = ioreg()
    z, b1 = props(text), obytes()
    rate = (b1 - b0) / SECONDS / 1e6
    d = {k: z.get(k, 0) - a.get(k, 0) for k in COUNTERS}
    d = {k: v for k, v in d.items() if v}
    line = (f"{name}: 隔空投送 {rate:.2f} MB/s；路由器 {summary(res.get('gw', '')) if gw else '没有网关'}；"
            f"手机 {summary(res.get('peer', '')) if peer else '没有对端'}；第二信道 {z.get('Phy2Chan')} 自动候选 {z.get('Phy2Auto')} "
            f"错误 {z.get('Phy2Err')}；变化 {d}；聚合 {z.get('OwnAgg')} 扣住 {z.get('OwnHeld')} 关闭标记 {z.get('TxTripped')} 固件报错 {z.get('FwErrors')}")
    print(line, flush=True)
    lines.append(line)
    return z

def main():
    if run('sysctl', '-n', PHY2).returncode or 'ItlwmAwdlCtxTeOwn' not in ioreg():
        sys.exit('当前运行的不是 1.1.57，请先重启。')
    if props().get('TxTripped'):
        sys.exit('这次开机 AWDL 已经停用（之前有过固件报错），请重启后再测。')
    info = run('system_profiler', 'SPAirPortDataType', timeout=90).stdout
    m = re.search(r'Channel: (\d+)', info)
    home = int(m[1]) if m else 0
    seq = own_sequence()
    print(f'电脑当前在信道 {home or "?"}；AWDL 时间表各时段的信道：{seq}', flush=True)
    if not home or home == 149:
        sys.exit('电脑现在不在路由器的其他信道上，看不出第二信道的效果。请连到不在 149 的路由器（最好 36–48）再运行。')
    print('iPhone 解锁放在旁边，连自己的 Wi-Fi 或蜂窝都可以，不要连电脑这台路由器以外的热点。', flush=True)
    print('准备一个 3 GB 以上的大文件（越大越好），全程约 2 分钟。', flush=True)
    print('这个实验可能让 Wi-Fi 断开十几秒，请先保存工作。', flush=True)
    input('现在用隔空投送把大文件发给手机，手机接受后（哪怕一直显示“等待中”）按回车。')
    lines = [f'开始 {datetime.datetime.now()} 当前信道 {home}；时间表 {seq}']
    found = peers()
    peer = found[0] if found else None
    lines.append(f'awdl0 对端: {len(found)} 个')
    print(lines[-1], flush=True)
    try:
        z = phase('基准（只在路由器信道）', lines, peer)
        if not z.get('TxTripped'):
            setv(PHY2, 1)
            time.sleep(4)
            z = phase('自动第二信道，不开窗口', lines, peer)
        if not z.get('TxTripped'):
            setv(TE, 2)
            z = phase('自动第二信道，按手机时间表开窗口', lines, peer)
        if not z.get('TxTripped'):
            setv(TE, 3)
            z = phase('自动第二信道，按自己时间表开窗口', lines, peer)
        if z.get('TxTripped'):
            lines.append('固件报错或 AWDL 已停用，后面的阶段已跳过')
            print(lines[-1], flush=True)
    finally:
        # The driver ends any window and moves the link back itself; windows off last.
        setv(PHY2, 0)
        time.sleep(3)
        setv(TE, 0)
    phase('关闭后', lines, peer)
    lines.append('传输结果：' + input('文件最后传完了吗？大约用了多久？哪一段明显变快或卡住？ ').strip())
    path = Path(__file__).resolve().parent / f"channel-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt"
    path.write_text('\n'.join(lines) + '\n')
    print('已结束，第二信道已关闭。结果已保存：', path.name)
main()
