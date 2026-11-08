"""1.1.60: AirDrop with a second channel beside the router link, phase by phase. Results are saved after every phase
(the 06:51 run was closed before the end and left nothing), and each phase asks whether the phone sees this Mac.
The family's own AWDL peer count for the phase is read from the log. RAM switches only; the second channel is off
again at the end or on any exit, in the safe order. The speed-up (own queue, aggregation) stays at its default."""
import datetime, re, signal, subprocess, sys, threading, time
from pathlib import Path
PHY2, TE = 'debug.be201_awdl_phy2', 'debug.be201_awdl_phy2_te'
KEYS = ['Phy2Chan', 'Phy2Err', 'Phy2Switches', 'Phy2Auto', 'Phy2AutoChanges', 'Phy2SlotMoves', 'SlotNext5', 'SeqChan5', 'RxPhy2', 'RxHome',
        'CtxTeRequests', 'CtxTeStarted', 'CtxTeEnded', 'CtxTeFailed', 'CtxTeRemoved', 'CtxTeOwn',
        'OwnSent', 'OwnOk', 'OwnFail', 'OwnHeld', 'OwnAgg', 'OwnRecovers', 'OwnRetries', 'OwnRetargets', 'TxTripped', 'DataTx', 'DataRx']
COUNTERS = ['Phy2Switches', 'Phy2AutoChanges', 'Phy2SlotMoves', 'RxPhy2', 'RxHome', 'CtxTeRequests', 'CtxTeStarted', 'CtxTeEnded', 'CtxTeFailed',
            'CtxTeRemoved', 'CtxTeOwn', 'OwnSent', 'OwnOk', 'OwnFail', 'OwnRecovers', 'OwnRetries', 'OwnRetargets', 'DataTx', 'DataRx']

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

def family_peers(seconds):
    # Numbers only from the family's periodic state dump: peer count and real-time sessions over the phase.
    out = run('log', 'show', '--last', f'{seconds}s', '--style', 'compact', '--predicate',
              'process == "kernel" AND eventMessage CONTAINS "AWDLStateDump: AWDL up time"', timeout=120).stdout
    peers = [int(x) for x in re.findall(r'peers:(\d+)', out)]
    rtg = [int(x) for x in re.findall(r'rtg\((\d+)\)', out)]
    return f"系统对端 {min(peers) if peers else '?'}–{max(peers) if peers else '?'}，实时会话 {max(rtg) if rtg else '?'}"

def save(lines, path):
    path.write_text('\n'.join(lines) + '\n')

def phase(name, seconds, lines):
    found = peers()
    peer = found[0] if found else None
    a, b0 = props(), obytes()
    res = {}
    def pinger(key, cmd):
        res[key] = run(*cmd, timeout=seconds + 15).stdout
    jobs = []
    gw = gateway()
    if gw:
        jobs.append(threading.Thread(target=pinger, args=('gw', ['ping', '-c', str(seconds * 2), '-i', '0.5', '-t', str(seconds + 3), gw])))
    if peer:
        jobs.append(threading.Thread(target=pinger, args=('peer', ['ping6', '-c', str(seconds * 2), '-i', '0.5', peer])))
    for j in jobs:
        j.start()
    time.sleep(seconds)
    for j in jobs:
        j.join()
    text = ioreg()
    z, b1 = props(text), obytes()
    rate = (b1 - b0) / seconds / 1e6
    d = {k: z.get(k, 0) - a.get(k, 0) for k in COUNTERS}
    d = {k: v for k, v in d.items() if v}
    seq5 = z.get('SeqChan5', 0)
    line = (f"{name}: 隔空投送 {rate:.2f} MB/s；{family_peers(seconds + 5)}；路由器 {summary(res.get('gw', '')) if gw else '没有网关'}；"
            f"手机 {summary(res.get('peer', '')) if peer else '没有对端'}（awdl0 对端 {len(found)} 个）；"
            f"时间表 {own_sequence(text)}；5GHz 候选 {seq5 & 0xff}/{seq5 >> 8}；第二信道 {z.get('Phy2Chan')} 自动选 {z.get('Phy2Auto')} "
            f"错误 {z.get('Phy2Err')}；变化 {d}；聚合 {z.get('OwnAgg')} 扣住 {z.get('OwnHeld')} 关闭标记 {z.get('TxTripped')} 固件报错 {z.get('FwErrors')}")
    print(line, flush=True)
    lines.append(line)
    lines.append(f"{name} 用户：" + input('这一段里，手机分享面板能看到这台电脑吗？电脑上的传输有没有动？（直接描述，回车继续）').strip())
    save(lines, PATH)
    return z

def _closed(signum, frame):
    # Closing the Terminal window sends SIGHUP: turn it into an exception so the switches still go off.
    raise KeyboardInterrupt

signal.signal(signal.SIGHUP, _closed)
signal.signal(signal.SIGTERM, _closed)

PATH = Path(__file__).resolve().parent / f"channel-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt"

def main():
    if run('sysctl', '-n', PHY2).returncode or 'AirportItlwm (1.1.60)' not in run('kmutil', 'showloaded').stdout:
        sys.exit('当前运行的不是 1.1.60，请先重启。')
    if props().get('TxTripped'):
        sys.exit('这次开机 AWDL 已经停用（之前有过固件报错），请重启后再测。')
    info = run('system_profiler', 'SPAirPortDataType', timeout=90).stdout
    m = re.search(r'Channel: (\d+)', info)
    home = int(m[1]) if m else 0
    seq = own_sequence()
    print(f'电脑当前在信道 {home or "?"}；AWDL 时间表各时段的信道：{seq}', flush=True)
    if not home or home == 149:
        sys.exit('电脑现在不在路由器的其他信道上，看不出第二信道的效果。请连到不在 149 的路由器（最好 36–48）再运行。')
    print('iPhone 解锁放在旁边，连它自己的网络或蜂窝都可以。准备一个 3 GB 以上的大文件。全程约 3 分钟。', flush=True)
    print('每一段结束时会问你手机能不能看到电脑、传输有没有动；结果每段都会保存。', flush=True)
    print('这个实验可能让 Wi-Fi 断开十几秒，请先保存工作。', flush=True)
    input('现在用隔空投送把大文件发给手机（发不出去也没关系，保持发送窗口开着），然后按回车。')
    lines = [f'开始 {datetime.datetime.now()} 当前信道 {home}；时间表 {seq}']
    save(lines, PATH)
    try:
        z = phase('基准（只在路由器信道）', 20, lines)
        if not z.get('TxTripped'):
            # Windows mode first, then the automatic channel: mode 4 must never see a moment of plain automatic.
            setv(TE, 4)
            setv(PHY2, 1)
            time.sleep(4)
            z = props()
            note = f"打开模式 4（跟着时间表在路由器信道和第二信道之间切换）：自动选 {z.get('Phy2Auto')} 下一个 5GHz 时段 {z.get('SlotNext5')}"
            print(note, flush=True)
            lines.append(note)
            z = phase('模式 4：36 的时段回路由器信道，149 的时段去 149', 40, lines)
        if not z.get('TxTripped'):
            setv(TE, 3)
            z = phase('模式 3：一直在 149，只在 149 时段开窗口', 30, lines)
        if z.get('TxTripped'):
            lines.append('固件报错或 AWDL 已停用，后面的阶段已跳过')
            print(lines[-1], flush=True)
    finally:
        # The driver ends any window and moves the link back itself; windows off last.
        setv(PHY2, 0)
        time.sleep(3)
        setv(TE, 0)
    phase('关闭后', 15, lines)
    lines.append('传输结果：' + input('文件最后传完了吗？ ').strip())
    save(lines, PATH)
    print('已结束，第二信道已关闭。结果已保存：', PATH.name)
main()
