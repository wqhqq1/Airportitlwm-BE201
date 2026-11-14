"""1.2.23 presence A/B: how often nearby devices drop out of this Mac's AWDL view, with and without three later changes.

Peer absences on the router's channel ran at 3.3 a minute on 1.2.22 (0.67 on 1.2.17). Rounds alternate A (the current
switch) and B (the same switch plus 0x380000: sequences age out after 2 s, no receive timestamps, no flush at each slot
start, all as on 1.2.17), ROUND_S seconds each, twice. Each round counts wifip2pd "Posted peer absence" and "Aging out
discovery result" lines and the driver's receive counters. The switch is put back at the end, whatever happens.
Run with nothing being sent, the phone and iPad unlocked nearby, the AirDrop window open on the Mac.
"""
import datetime, pathlib, re, subprocess, sys, time

ROC = 'debug.be201_awdl_roc'
AB = 0x80000 | 0x100000 | 0x200000
ROUND_S = 180
KEYS = ['RxPhy2', 'RocRxDuring', 'RocDiscovery', 'RocStarted', 'RocOnSumMs', 'RocCovSumMs', 'DataRx', 'DataTx']
HERE = pathlib.Path(__file__).resolve().parent


def run(*a, timeout=120):
    return subprocess.run(a, capture_output=True, text=True, timeout=timeout)


def getv():
    r = run('sysctl', '-n', ROC)
    s = r.stdout.strip()
    return int(s) if not r.returncode and s.lstrip('-').isdigit() else 0


def setv(v):
    run('sysctl', '-w', f'{ROC}={v}')


def props():
    text = run('ioreg', '-l', '-w0').stdout
    out = {}
    for k in KEYS:
        m = re.search(rf'"ItlwmAwdl{k}" = (\d+)', text)
        out[k] = int(m[1]) if m else 0
    m = re.search(r'"IO80211Channel" = (\d+)', text)
    out['Channel'] = int(m[1]) if m else 0
    return out


def counts(start, end):
    fmt = '%Y-%m-%d %H:%M:%S'
    r = run('/usr/bin/log', 'show', '--style', 'compact', '--start', start.strftime(fmt), '--end', end.strftime(fmt),
            '--predicate', 'process == "wifip2pd" AND (eventMessage CONTAINS "Posted peer absence" OR '
            'eventMessage CONTAINS "Aging out discovery result" OR eventMessage CONTAINS "Posted peer presence")')
    text = r.stdout
    return text.count('Posted peer absence'), text.count('Aging out discovery result'), text.count('Posted peer presence')


def main():
    start_value = getv()
    if not start_value:
        print('跨信道隔空投送没有开启（debug.be201_awdl_roc 为 0），无法比较。')
        return 1
    base = start_value & ~AB
    name = HERE / f'presence-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt'
    lines = [f'开始 {datetime.datetime.now()} 开关 0x{start_value:X}，A=0x{base:X}，B=0x{base | AB:X}，每轮 {ROUND_S} 秒']
    print(lines[-1], flush=True)
    print('请这段时间不要传东西；手机和 iPad 解锁放在旁边，Mac 打开隔空投送窗口。', flush=True)
    rounds = [('A 当前', base), ('B 退回 1.2.17', base | AB), ('A 当前', base), ('B 退回 1.2.17', base | AB)]
    total = {}
    try:
        for label, value in rounds:
            setv(value)
            time.sleep(5)
            p0, t0 = props(), datetime.datetime.now()
            time.sleep(ROUND_S)
            p1, t1 = props(), datetime.datetime.now()
            ab, ag, pr = counts(t0, t1)
            minutes = (t1 - t0).total_seconds() / 60
            d = {k: p1[k] - p0[k] for k in KEYS}
            lines.append(f'{label}（0x{value:X}，路由器信道 {p1["Channel"]}）：对端不在场 {ab} 次（每分钟 {ab / minutes:.1f}），'
                         f'服务过期 {ag} 次，重新在场 {pr} 次；ROC 期间收到 {d["RocRxDuring"]} 帧，第二信道收到 {d["RxPhy2"]} 帧，'
                         f'发现 ROC {d["RocDiscovery"]} 次，149 驻留 {d["RocOnSumMs"] / 1000:.0f} 秒；数据 收 {d["DataRx"]} 发 {d["DataTx"]}')
            print(lines[-1], flush=True)
            t = total.setdefault(label, [0, 0, 0.0])
            t[0] += ab
            t[1] += ag
            t[2] += minutes
    finally:
        setv(start_value)
        lines.append(f'已恢复开关 0x{start_value:X}')
        print(lines[-1], flush=True)
    for label, (ab, ag, minutes) in total.items():
        lines.append(f'合计 {label}：不在场每分钟 {ab / minutes:.1f}，服务过期每分钟 {ag / minutes:.1f}')
        print(lines[-1], flush=True)
    name.write_text('\n'.join(lines) + '\n')
    print(f'结果已保存到 {name.name}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
