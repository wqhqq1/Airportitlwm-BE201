"""1.1.75 and later (1.1.91: why AUX frames fail and ROC timing; 1.1.90: also the last PHY command's channel and width; 1.1.89: baseline, mode 1 with P2P_TXRX, the AWDL link moved to 149 with ROC off, then mode 4 on that
link for 90 s; the first firmware error switches everything off at once): remain-on-channel (ROC) test beside a router link, phase by phase. The firmware gets an ROC for each run of
the AWDL sequence's other 5 GHz channel, through an AUX station, as Intel's Linux driver sends off-channel frames.
Results are saved after every phase, and each phase asks whether the phone sees this Mac and the transfer moves.
RAM switch only (debug.be201_awdl_roc); it is off again at the end or on any exit."""
import datetime, re, signal, subprocess, sys, threading, time
from pathlib import Path
ROC = 'debug.be201_awdl_roc'
PHY2 = 'debug.be201_awdl_phy2'
KEYS = ['RocMode', 'RocQid', 'RocSetups', 'RocSetupErr', 'RocSetupStage', 'RocTeardowns', 'RocAdds', 'RocAddErr', 'RocStarted', 'RocEnded', 'RocFailed', 'RocStale', 'RocRemoves', 'RocChan', 'RocTxSent', 'RocTxOk', 'RocTxFail', 'RocTxDrop', 'RocRxDuring', 'RocDiscovery', 'RocRxAny', 'RocRxAnyChan', 'RocRxAwdlAny', 'RxPhy2', 'RxHome', 'Phy2Chan', 'RocPhyHolds', 'RocPhyCancels', 'Phy2Switches', 'Phy2Err', 'FaultRoc', 'FaultPhy2', 'RocLateMaxUs', 'RocTxOkUcast', 'RocTxFailUcast', 'RocTxOkMcast', 'RocTxFailMcast', 'RocTxFailIn', 'RocTxFailOut', 'RocTxOkHere', 'RocTxOkAway', 'RocTxFailHere', 'RocTxFailAway', 'RocTxFailUnknown', 'RocTxFailTries', 'RocTxOkTries', 'RocLateN', 'RocLateSumMs', 'RocOnN', 'RocOnSumMs',
        'SeqChan5', 'OwnSent', 'OwnOk', 'OwnFail', 'OwnRecovers', 'TxTripped', 'DataTx', 'DataRx', 'FirmwareFaults', 'FaultRearms']
COUNTERS = ['RocSetups', 'RocTeardowns', 'RocAdds', 'RocAddErr', 'RocStarted', 'RocEnded', 'RocFailed', 'RocStale', 'RocRemoves', 'RocTxSent', 'RocTxOk', 'RocTxFail', 'RocTxDrop', 'RocRxDuring', 'RocDiscovery', 'RocRxAny', 'RocRxAnyChan', 'RocRxAwdlAny', 'RxPhy2', 'RxHome', 'RocPhyHolds', 'RocPhyCancels', 'Phy2Switches', 'RocTxOkUcast', 'RocTxFailUcast', 'RocTxOkMcast', 'RocTxFailMcast', 'RocTxFailIn', 'RocTxFailOut', 'RocTxOkHere', 'RocTxOkAway', 'RocTxFailHere', 'RocTxFailAway', 'RocTxFailUnknown', 'RocTxFailTries', 'RocTxOkTries', 'RocLateN', 'RocLateSumMs', 'RocOnN', 'RocOnSumMs', 'OwnSent', 'OwnOk', 'OwnFail', 'OwnRecovers', 'DataTx', 'DataRx']
def run(*a, timeout=60):
    return subprocess.run(a, capture_output=True, text=True, timeout=timeout)

def ioreg():
    return run('ioreg', '-l', '-w0').stdout

def props(text=None):
    text = text or ioreg()
    out = {k: int(m[1]) for k in KEYS if (m := re.search(rf'"ItlwmAwdl{k}" = (\d+)', text))}
    m = re.search(r'"ItlwmFwErrors" = (\d+)', text)
    out['FwErrors'] = int(m[1]) if m else 0
    # 1.1.91: AUX failures by status: short limit, long limit, drain, lifetime, dest PS, FIFO flushed, aborted, other.
    m = re.search(r'"ItlwmAwdlRocTxStatus" = <([0-9a-f]{64})>', text)
    out['TxStatus'] = [int.from_bytes(bytes.fromhex(m[1])[4 * i:4 * i + 4], 'little') for i in range(8)] if m else [0] * 8
    for k in ['ItlwmFwErrorId', 'ItlwmFwErrorCmd', 'ItlwmFwErrorData1']:
        m = re.search(rf'"{k}" = (\d+)', text)
        out[k] = int(m[1]) if m else None
    # 1.1.82: which readiness condition an ROC still waits for, and the DMA pool (the 1.1.81 leak ended in ENOMEM).
    for k in ['ItlwmPhyChannel', 'ItlwmPhyWidth', 'ItlwmPhyCtrlPos', 'ItlwmAwdlPhy2FaultHolds', 'ItlwmAwdlRocBlocked', 'ItlwmDmaUsedKiB', 'ItlwmDmaFailures', 'ItlwmDmaRetiredKiB', 'ItlwmMldDataQueues', 'ItlwmAwdlOwnErr', 'ItlwmApPortValid', 'ItlwmApRsnOn']:
        m = re.search(rf'"{k}" = (\d+)', text)
        out[k] = int(m[1]) if m else None
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
    # 1.1.89: the first new firmware error turns both switches off at once. On 07:47 the driver re-armed twice and
    # each re-arm moved the link again into the same assert, so the router link dropped three times.
    fault_at = None
    start = time.monotonic()
    while time.monotonic() - start < seconds:
        time.sleep(2)
        if fault_at is None and props().get('FwErrors', 0) > FW0[0]:
            setv(ROC, 0)
            setv(PHY2, 0)
            fault_at = int(time.monotonic() - start)
            print(f'固件报错（第 {fault_at} 秒），已关闭 ROC 和第二信道', flush=True)
    for j in jobs:
        j.join()
    text = ioreg()
    z, b1 = props(text), obytes()
    rate = (b1 - b0) / seconds / 1e6
    d = {k: z.get(k, 0) - a.get(k, 0) for k in COUNTERS}
    d = {k: v for k, v in d.items() if v}
    st = [y - x for x, y in zip(a.get('TxStatus', [0] * 8), z.get('TxStatus', [0] * 8))]
    late = d.get('RocLateSumMs', 0) / d['RocLateN'] if d.get('RocLateN') else None
    on = d.get('RocOnSumMs', 0) / d['RocOnN'] if d.get('RocOnN') else None
    line = (f"{name}: 隔空投送 {rate:.2f} MB/s；{family_peers(seconds + 5)}；路由器 {summary(res.get('gw', '')) if gw else '没有网关'}；"
            f"手机 {summary(res.get('peer', '')) if peer else '没有对端'}（awdl0 对端 {len(found)} 个）；时间表 {own_sequence(text)}；"
            f"ROC 模式 {z.get('RocMode')} 队列 {z.get('RocQid')} 建立错误 {z.get('RocSetupErr')}@{z.get('RocSetupStage')} 信道 {z.get('RocChan')}；变化 {d}；"
            f"关闭标记 {z.get('TxTripped')} 固件报错 {z.get('FwErrors')}；ROC 缺少条件 {z.get('ItlwmAwdlRocBlocked')}；"
            f"DMA 已用 {z.get('ItlwmDmaUsedKiB')} KiB 失败 {z.get('ItlwmDmaFailures')} 搁置 {z.get('ItlwmDmaRetiredKiB')} KiB；"
            f"路由器数据队列 {z.get('ItlwmMldDataQueues')} 聚合队列错误 {z.get('ItlwmAwdlOwnErr')}；"
            f"AP 端口标志 {z.get('ItlwmApPortValid')} 加密网络 {z.get('ItlwmApRsnOn')}；"
            f"链路信道 {z.get('Phy2Chan')} 换信道错误 {z.get('Phy2Err')}；"
            f"失败原因 重试上限 {st[0]}+{st[1]} 排空 {st[2]} 超时 {st[3]} 对方省电 {st[4]} 清队列 {st[5]} 中止 {st[6]} 其他 {st[7]}；"
            f"ROC 平均晚开始 {f'{late:.1f}' if late is not None else '?'} ms 最晚 {(z.get('RocLateMaxUs') or 0) / 1000:.1f} ms 平均驻留 {f'{on:.1f}' if on is not None else '?'} ms；"
            f"最后一条 PHY 命令 信道 {z.get('ItlwmPhyChannel')} 宽度 {z.get('ItlwmPhyWidth')} 位置 {z.get('ItlwmPhyCtrlPos')}；出错停用 {z.get('ItlwmAwdlPhy2FaultHolds')}")
    if fault_at is not None or z.get('FwErrors', 0) > FW0[0]:
        line += (f"；固件报错 第 {fault_at} 秒 错误 0x{(z.get('ItlwmFwErrorId') or 0):08X} 命令 0x{(z.get('ItlwmFwErrorCmd') or 0):06X} "
                 f"数据 {z.get('ItlwmFwErrorData1')} 当时 ROC 0x{(z.get('FaultRoc') or 0):06X} 链路 0x{(z.get('FaultPhy2') or 0):06X}")
    print(line, flush=True)
    lines.append(line)
    lines.append(f"{name} 用户：" + input('这一段里，手机分享面板能看到这台电脑吗？电脑上的传输有没有动？（直接描述，回车继续）').strip())
    save(lines, PATH)
    return z, d

def _closed(signum, frame):
    raise KeyboardInterrupt

signal.signal(signal.SIGHUP, _closed)
signal.signal(signal.SIGTERM, _closed)

FW0 = [0]  # firmware errors before the test: anything above is new
PATH = Path(__file__).resolve().parent / f"roc-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt"

def main():
    # The ROC switch exists from 1.1.75 on; any later driver has it too.
    loaded = re.search(r'com\.zxystd\.AirportItlwm \((\d+)\.(\d+)\.(\d+)\)', run('kmutil', 'showloaded').stdout)
    if run('sysctl', '-n', ROC).returncode or not loaded or tuple(map(int, loaded.groups())) < (1, 1, 75):
        sys.exit('当前运行的驱动没有 ROC 实验开关（需要 1.1.75 或更新），请先重启。')
    if props().get('TxTripped'):
        sys.exit('这次开机 AWDL 已经停用（固件报错），请重启后再测。')
    info = run('system_profiler', 'SPAirPortDataType', timeout=90).stdout
    m = re.search(r'Channel: (\d+)', info)
    home = int(m[1]) if m else 0
    seq = own_sequence()
    print(f'电脑当前在信道 {home or "?"}；AWDL 时间表各时段的信道：{seq}', flush=True)
    if not home or home == 149:
        sys.exit('电脑现在不在路由器的其他信道上，ROC 不会启动。请连到不在 149 的路由器（最好 36–48，不要连手机热点）再运行。')
    print('iPhone 解锁放在旁边。准备一个 1 GB 以上的文件。全程约 3 分钟。', flush=True)
    print('每一段结束时会问你手机能不能看到电脑、传输有没有动；结果每段都会保存。', flush=True)
    print('这个实验可能让 Wi-Fi 断开十几秒，请先保存工作。', flush=True)
    input('现在用隔空投送把文件发给手机（发不出去也没关系，保持发送窗口开着），然后按回车。')
    FW0[0] = props().get('FwErrors', 0)
    lines = [f'开始 {datetime.datetime.now()} 当前信道 {home}；时间表 {seq}']
    save(lines, PATH)
    activity = 2
    faulted = lambda z: z.get('TxTripped') or z.get('FwErrors', 0) > FW0[0]
    try:
        z, d = phase('基准（ROC 关闭）', 20, lines)
        if not faulted(z):
            # 1.1.87: P2P_TXRX only; HOTSPOT with AUX transmit asserted the firmware on 16:08.
            setv(ROC, 1 + 16 * activity)
            z, d = phase('模式 1：只做 ROC（P2P 收发），看固件是否接受、是否收到 149 上的帧', 20, lines)
        if not faulted(z) and d.get('RocStarted'):
            # 1.1.89: the link moves with ROC off, and only then do ROCs start. On 07:47 the move and the P2P_TXRX ROCs
            # overlapped and the firmware asserted at PHY_CONTEXT_CMD.
            setv(ROC, 0)
            time.sleep(2)
            setv(PHY2, 1)
            for _ in range(10):
                time.sleep(1.5)
                if props().get('Phy2Chan'):
                    break
            z, d = phase('链路先移到 149（ROC 关闭），看能否收到手机的帧', 20, lines)
            if not faulted(z) and z.get('Phy2Chan'):
                print('下一段最长：开始后请在手机或电脑上重新发一次文件（发送窗口可以重新打开）。', flush=True)
                setv(ROC, 4 + 16 * activity)
                z, d = phase('模式 4：链路已在 149，帧都经 ROC 发送（请重新发一次文件）', 90, lines)
            elif not faulted(z):
                lines.append('链路没有移到 149，模式 4 已跳过')
                print(lines[-1], flush=True)
            setv(ROC, 0)
            setv(PHY2, 0)
        if faulted(z):
            lines.append('固件报错或 AWDL 已停用，后面的阶段已跳过')
            print(lines[-1], flush=True)
    finally:
        setv(ROC, 0)
        setv(PHY2, 0)
    time.sleep(3)
    phase('关闭后', 20, lines)
    lines.append('传输结果：' + input('文件最后传完了吗？ ').strip())
    save(lines, PATH)
    print('已结束，ROC 已关闭。结果已保存：', PATH.name)
main()
