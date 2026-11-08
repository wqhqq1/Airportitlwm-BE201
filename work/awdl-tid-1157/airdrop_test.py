"""1.1.57 (1.1.54 content): the speed-up is on by default. Whether a second AirDrop in the same boot is fast too: the first one
leaves a held queue, which this version rebuilds. Records only, changes no switch."""
import datetime, re, subprocess, sys, time
from pathlib import Path
FIX = 'debug.be201_awdl_own_fix'
SECONDS = 20
KEYS = ['OwnSent', 'OwnOk', 'OwnFail', 'OwnHeld', 'OwnSta', 'OwnTid', 'OwnAgg', 'OwnRetargets', 'OwnRecovers', 'OwnRecoverFails',
        'OwnQuietSkips', 'OwnAggOk', 'OwnAggFail', 'OwnBaNotifs', 'OwnActive', 'OwnErr', 'OwnFixDone', 'OwnFixErr', 'DataTx',
        'DataTxDropped', 'TxTripped']
COUNTERS = ('OwnSent', 'OwnOk', 'OwnFail', 'OwnAggOk', 'OwnAggFail', 'OwnBaNotifs', 'OwnRetargets', 'OwnRecovers', 'OwnQuietSkips',
            'DataTx', 'DataTxDropped')

def run(*a, timeout=60):
    return subprocess.run(a, capture_output=True, text=True, timeout=timeout)

def props():
    text = run('ioreg', '-l', '-w0').stdout
    out = {k: int(m[1]) for k in KEYS if (m := re.search(rf'"ItlwmAwdl{k}" = (\d+)', text))}
    m = re.search(r'"ItlwmFwErrors" = (\d+)', text)
    out['FwErrors'] = int(m[1]) if m else 0
    out['SpeedDefault'] = '"ItlwmAwdlSpeedDefault" = Yes' in text
    out['New'] = '"ItlwmAwdlCtxTeOwn"' in text
    return out

def obytes():
    for line in run('netstat', '-I', 'awdl0', '-b').stdout.splitlines():
        f = line.split()
        if len(f) >= 10 and f[0] == 'awdl0' and f[2].startswith('<Link'):
            return int(f[9])
    return 0

def phase(name, lines):
    a, b0 = props(), obytes()
    time.sleep(SECONDS)
    z, b1 = props(), obytes()
    rate = (b1 - b0) / SECONDS / 1e6
    d = {k: z.get(k, 0) - a.get(k, 0) for k in COUNTERS}
    d = {k: v for k, v in d.items() if v}
    state = {k: z.get(k) for k in ('OwnFixDone', 'OwnFixErr', 'OwnActive', 'OwnHeld', 'OwnRecoverFails', 'OwnSta', 'OwnTid', 'OwnAgg',
                                   'OwnErr', 'TxTripped', 'FwErrors')}
    line = f"{name}: 速度 {rate:.2f} MB/s；变化 {d}；状态 {state}"
    print(line, flush=True)
    lines.append(line)
    return z

def main():
    p = props()
    if run('sysctl', '-n', FIX).returncode or not p['New']:
        sys.exit('当前运行的不是 1.1.57，请先重启。')
    if p.get('TxTripped'):
        sys.exit('这次开机 AWDL 已经停用（之前有过固件报错），请重启后再测。')
    info = run('system_profiler', 'SPAirPortDataType', timeout=90).stdout
    m = re.search(r'Channel: (\d+)', info)
    home = int(m[1]) if m else 0
    print(f'电脑当前在信道 {home or "?"}；默认提速{"已" if p["SpeedDefault"] else "未"}打开。', flush=True)
    print('准备两个大文件，各 1 GB 以上。iPhone 解锁放在旁边。这个工具不改任何开关。', flush=True)
    input('现在用隔空投送把第一个文件发给手机，手机接受、开始传输后按回车。')
    lines = [f'开始 {datetime.datetime.now()} 信道 {home} 默认提速 {p["SpeedDefault"]}']
    phase('第一次发送', lines)
    lines.append('第一个文件：' + input('等第一个文件传完后回答：传完了吗？大约用了多久？ ').strip())
    print('等 10 秒，让驱动处理传输结束后留下的帧。', flush=True)
    time.sleep(10)
    phase('两次之间', lines)
    input('现在把第二个文件发给手机，开始传输后按回车。')
    phase('同一次开机第二次发送', lines)
    lines.append('第二个文件：' + input('等第二个文件传完后回答：传完了吗？大约用了多久？ ').strip())
    path = Path(__file__).resolve().parent / f"airdrop-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt"
    path.write_text('\n'.join(lines) + '\n')
    print('已结束。结果已保存：', path.name)
main()
