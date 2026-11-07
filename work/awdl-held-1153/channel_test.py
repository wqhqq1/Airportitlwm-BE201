"""1.1.53: second channel for AWDL beside the AP link. RAM switches, all off at the end, in a safe order."""
import datetime, re, subprocess, sys, time
from pathlib import Path
PHY2, TE, OWN = 'debug.be201_awdl_phy2', 'debug.be201_awdl_phy2_te', 'debug.be201_awdl_own_queue'
TARGET = 149
KEYS = ['Phy2Chan', 'Phy2Err', 'Phy2Switches', 'RxPhy2', 'RxHome', 'CtxTeRequests', 'CtxTeStarted', 'CtxTeEnded', 'CtxTeFailed', 'CtxTeRemoved',
        'OwnSent', 'OwnOk', 'OwnFail', 'OwnHeld', 'OwnErr', 'OwnReleased', 'TxTripped', 'DataTx', 'DataRx']

def run(*a, timeout=60):
    return subprocess.run(a, capture_output=True, text=True, timeout=timeout)

def props():
    text = run('ioreg', '-l', '-w0').stdout
    out = {k: int(m[1]) for k in KEYS if (m := re.search(rf'"ItlwmAwdl{k}" = (\d+)', text))}
    m = re.search(r'"ItlwmFwErrorId" = (\d+)', text)
    out['FwError'] = int(m[1]) if m else 0
    m = re.search(r'"ItlwmFwErrors" = (\d+)', text)
    out['FwErrors'] = int(m[1]) if m else 0
    return out

def setv(oid, value):
    run('sysctl', '-w', f'{oid}={value}')

def gateway():
    for line in run('route', '-n', 'get', 'default').stdout.splitlines():
        if 'gateway:' in line:
            return line.split()[-1]

def ping(target, seconds):
    if not target:
        return '没有网关'
    r = run('ping', '-c', str(seconds * 2), '-i', '0.5', '-t', str(seconds + 3), target, timeout=seconds + 10).stdout
    loss = re.search(r'([\d.]+)% packet loss', r)
    avg = re.search(r'= [\d.]+/([\d.]+)/', r)
    return f"丢包 {loss[1] if loss else '?'}%，平均 {avg[1] if avg else '?'} ms"

def peers():
    # A multicast echo fills the neighbor table, so the own queue phase has someone to send to.
    run('ping6', '-c', '2', '-i', '0.5', 'ff02::1%awdl0', timeout=10)
    out = []
    for line in run('ndp', '-an').stdout.splitlines():
        f = line.split()
        if f and '%awdl0' in f[0] and f[0].startswith('fe80') and 'permanent' not in line and f[1] != '(incomplete)':
            out.append(f[0])
    return out

def phase(name, seconds, lines, sender=None):
    a = props()
    net = ping(gateway(), seconds)
    z = props()
    sent = ''
    if sender:
        sender.wait(timeout=30)
        out = sender.stdout.read() if sender.stdout else ''
        m = re.search(r'(\d+) packets transmitted, (\d+) packets received', out)
        sent = f"；对端 ping {m[2]}/{m[1]}" if m else '；对端 ping 无结果'
    d = {k: z.get(k, 0) - a.get(k, 0) for k in KEYS if k not in ('Phy2Chan', 'Phy2Err', 'TxTripped')}
    d = {k: v for k, v in d.items() if v}
    line = f"{name}: 网关{net}{sent}；变化 {d}；信道 {z.get('Phy2Chan')} 错误 {z.get('Phy2Err')} 关闭标记 {z.get('TxTripped')} 固件报错 {z.get('FwErrors')}"
    print(line, flush=True)
    lines.append(line)
    return z

def main():
    if run('sysctl', '-n', 'debug.be201_awdl_umi').returncode or run('sysctl', '-n', PHY2).returncode:
        sys.exit('当前运行的不是 1.1.53，请先重启。')
    if props().get('TxTripped'):
        sys.exit('这次开机 AWDL 已经停用（之前有过固件报错），请重启后再测。')
    info = run('system_profiler', 'SPAirPortDataType', timeout=90).stdout
    home = re.search(r'Channel: (\d+)', info)
    if not home or int(home[1]) == TARGET:
        sys.exit(f'电脑现在在信道 {home[1] if home else "?"}，看不出第二信道的效果。请连到不在 {TARGET} 的路由器再运行。')
    print(f'当前信道 {home[1]}，第二信道 {TARGET}。全程约 3 分钟。', flush=True)
    print('iPhone 解锁放在旁边，打开分享面板并保持亮屏；电脑上打开访达的“隔空投送”窗口。', flush=True)
    print('这个实验可能让 Wi-Fi 断开十几秒，请先保存工作。', flush=True)
    input('准备好后按回车。')
    lines = [f'开始 {datetime.datetime.now()} 当前信道 {home[1]} 目标 {TARGET}']
    found = peers()
    lines.append(f'awdl0 对端: {len(found)} 个')
    print(lines[-1], flush=True)
    try:
        phase('基准', 15, lines)
        setv(PHY2, TARGET)
        z = phase('第二信道', 30, lines)
        if not z.get('TxTripped'):
            setv(TE, 2)
            z = phase('按手机时间表开窗口', 30, lines)
        if not z.get('TxTripped'):
            found = found or peers()
            setv(OWN, 1)
            time.sleep(2)
            # A neighbor is rarely in the table without traffic; a real AirDrop send makes both.
            input('现在从电脑用隔空投送给手机发一张照片，点“发送”后马上按回车。')
            sender = subprocess.Popen(['ping6', '-c', '60', '-i', '0.5', found[0]], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True) if found else None
            z = phase('加对端专用队列（同时隔空投送）', 30, lines, sender)
            lines.append('照片发送结果：' + input('照片发送成功了吗？大约用了几秒？ ').strip())
        if z.get('TxTripped'):
            lines.append('固件报错或 AWDL 已停用，后面的阶段已跳过')
            print(lines[-1], flush=True)
    finally:
        # The driver ends the window and frees the queue itself before the link moves back; this order is the safe one anyway.
        setv(OWN, 0)
        setv(PHY2, 0)
        time.sleep(3)
        setv(TE, 0)
    phase('关闭后', 15, lines)
    path = Path(__file__).resolve().parent / f"channel-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt"
    path.write_text('\n'.join(lines) + '\n')
    print('已结束，所有开关已关闭。结果已保存：', path.name)
main()
