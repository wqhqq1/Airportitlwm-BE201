"""1.1.53: why the peer's own queue holds frames, then aggregation. RAM switches, all off at the end."""
import datetime, re, subprocess, sys, time
from pathlib import Path
OWN, AGG, PHY2, TE, FIX = 'debug.be201_awdl_own_queue', 'debug.be201_awdl_txagg', 'debug.be201_awdl_phy2', 'debug.be201_awdl_phy2_te', 'debug.be201_awdl_own_fix'
SECONDS = 20
KEYS = ['OwnSent', 'OwnOk', 'OwnFail', 'OwnHeld', 'OwnSta', 'OwnTid', 'OwnAgg', 'OwnRetargets', 'OwnAggErr', 'OwnTlcErr', 'OwnTxEnErr',
        'OwnAggOk', 'OwnAggFail', 'OwnBaNotifs', 'OwnActive', 'OwnErr', 'OwnFixDone', 'OwnFixErr', 'DataTx', 'DataTxDropped', 'RxPhy2', 'Phy2Chan', 'TxTripped']

def run(*a, timeout=60):
    return subprocess.run(a, capture_output=True, text=True, timeout=timeout)

def props():
    text = run('ioreg', '-l', '-w0').stdout
    out = {k: int(m[1]) for k in KEYS if (m := re.search(rf'"ItlwmAwdl{k}" = (\d+)', text))}
    m = re.search(r'"ItlwmFwErrors" = (\d+)', text)
    out['FwErrors'] = int(m[1]) if m else 0
    return out

def obytes():
    for line in run('netstat', '-I', 'awdl0', '-b').stdout.splitlines():
        f = line.split()
        if len(f) >= 10 and f[0] == 'awdl0' and f[2].startswith('<Link'):
            return int(f[9])
    return 0

def setv(oid, value):
    run('sysctl', '-w', f'{oid}={value}')

def gateway_rtt():
    gw = None
    for line in run('route', '-n', 'get', 'default').stdout.splitlines():
        if 'gateway:' in line:
            gw = line.split()[-1]
    if not gw:
        return '?'
    r = run('ping', '-c', '4', '-i', '0.5', '-t', '4', gw, timeout=10).stdout
    m = re.search(r'= [\d.]+/([\d.]+)/', r)
    return f"{m[1]} ms" if m else '丢包'

def phase(name, lines):
    a, b0 = props(), obytes()
    time.sleep(SECONDS)
    z, b1 = props(), obytes()
    rate = (b1 - b0) / SECONDS / 1e6
    d = {k: z.get(k, 0) - a.get(k, 0) for k in ('OwnSent', 'OwnOk', 'OwnFail', 'OwnAggOk', 'OwnAggFail', 'OwnBaNotifs', 'OwnRetargets', 'DataTx', 'DataTxDropped', 'RxPhy2')}
    d = {k: v for k, v in d.items() if v}
    state = {k: z.get(k) for k in ('OwnFixDone', 'OwnFixErr', 'OwnActive', 'OwnHeld', 'OwnSta', 'OwnTid', 'OwnAgg', 'OwnErr', 'OwnAggErr', 'OwnTlcErr', 'OwnTxEnErr', 'Phy2Chan', 'TxTripped', 'FwErrors')}
    line = f"{name}: 速度 {rate:.2f} MB/s；网关 {gateway_rtt()}；变化 {d}；状态 {state}"
    print(line, flush=True)
    lines.append(line)
    return z

def main():
    if run('sysctl', '-n', FIX).returncode:
        sys.exit('当前运行的不是 1.1.53，请先重启。')
    if props().get('TxTripped'):
        sys.exit('这次开机 AWDL 已经停用（之前有过固件报错），请重启后再测。')
    info = run('system_profiler', 'SPAirPortDataType', timeout=90).stdout
    m = re.search(r'Channel: (\d+)', info)
    home = int(m[1]) if m else 0
    print(f'电脑当前在信道 {home or "?"}。', flush=True)
    print('准备一个 1 GB 以上的大文件（比如一段视频），iPhone 解锁放在旁边。', flush=True)
    print('这个实验可能让 Wi-Fi 断开十几秒，请先保存工作。', flush=True)
    input('现在用隔空投送把大文件发给手机，手机接受、开始传输后按回车。')
    lines = [f'开始 {datetime.datetime.now()} 信道 {home}']
    try:
        z = phase('基准（全部关闭）', lines)
        if not z.get('TxTripped'):
            setv(OWN, 1)
            time.sleep(2)
            z = phase('对端专用队列', lines)
        if not z.get('TxTripped'):
            setv(FIX, 1)
            time.sleep(3)
            z = phase('加：关闭第二个 MAC 的省电', lines)
        if not z.get('TxTripped'):
            setv(FIX, 3)
            time.sleep(3)
            z = phase('再加：链路 QoS 与信标参数', lines)
        if not z.get('TxTripped'):
            setv(AGG, 1)
            time.sleep(3)
            z = phase('再加：聚合', lines)
        if not z.get('TxTripped') and home and home != 149:
            setv(PHY2, 149)
            time.sleep(1)
            setv(TE, 2)
            time.sleep(2)
            z = phase('再加第二信道 149', lines)
        if z.get('TxTripped'):
            lines.append('固件报错或 AWDL 已停用，后面的阶段已跳过')
            print(lines[-1], flush=True)
    finally:
        setv(OWN, 0)
        setv(AGG, 0)
        setv(FIX, 0)
        setv(PHY2, 0)
        time.sleep(3)
        setv(TE, 0)
    phase('关闭后', lines)
    lines.append('传输结果：' + input('文件最后传完了吗？大约用了多久？手机上有没有异常？ ').strip())
    path = Path(__file__).resolve().parent / f"airdrop-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt"
    path.write_text('\n'.join(lines) + '\n')
    print('已结束，所有开关已关闭。结果已保存：', path.name)
main()
