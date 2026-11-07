"""1.1.53: try Continuity Camera with UMI, then with llw0. RAM switches; UMI goes off at the end, llw0 stays until reboot."""
import datetime, json, os, plistlib, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE, UMI, LLW = 'debug.be201_awdl_cache_on', 'debug.be201_awdl_umi', 'debug.be201_awdl_llw'
KEYS = ['UmiSent', 'UmiOk', 'UmiFail', 'UmiRejected', 'CacheAdds', 'CacheDeletes', 'CacheFull', 'LlwAttempts', 'LlwCreateResult', 'LlwRegistrationError', 'LlwStage', 'LlwFailedStage', 'LlwPolls', 'LlwFeatureFlags',
        'DataTx', 'DataRx', 'DataRxBad', 'TxTripped']
PREDICATE = ('process == "ContinuityCaptureAgent" OR process == "SidecarDisplayAgent" OR process == "SidecarRelay" OR process == "rapportd" OR process == "avconferenced" OR process == "wifip2pd" OR '
             '(process == "kernel" AND (eventMessage CONTAINS "com.apple.p2p" OR eventMessage CONTAINS "BE201"))')

def run(*a, timeout=30):
    return subprocess.run(a, capture_output=True, text=True, timeout=timeout)

def setv(oid, value):
    return run('sysctl', '-w', f'{oid}={value}').returncode == 0

def props():
    out = {}
    text = run('ioreg', '-l', '-w0').stdout
    for k in KEYS:
        found = re.findall(rf'"ItlwmAwdl{k}" = (\d+)', text)
        if found:
            out[k] = [int(x) for x in found]
    m = re.search(r'"ItlwmFwErrorId" = (\d+)', text)
    if m:
        out['FwError'] = int(m[1])
    return out

def channel():
    m = re.search(r'Channel: (\d+)[^\n]*', run('system_profiler', 'SPAirPortDataType', timeout=60).stdout)
    return m[0] if m else '未知'

def phase(name, lines, seconds=45):
    input(f'\n{name}\n打开 FaceTime 或 QuickTime 的“新建影片录制”，在摄像头里选 iPhone；再在“显示器”设置里连接 iPad（随航）。等到有画面或明确失败。准备好后按回车，我等 {seconds} 秒。')
    start = datetime.datetime.now()
    a = props()
    time.sleep(seconds)
    z = props()
    text = run('log', 'show', '--start', start.strftime('%Y-%m-%d %H:%M:%S'), '--style', 'compact', '--predicate', PREDICATE, timeout=120).stdout
    (HERE/f"camera-{start:%Y%m%d-%H%M%S}.log").write_text(text)
    os.chmod(HERE/f"camera-{start:%Y%m%d-%H%M%S}.log", 0o600)
    checks = {'系统发出 UMI': 'sending UMI', '手机确认 UMI': 'acked our UMI', '手机没确认': 'DID NOT ack', '握手超时': 'Ensemble start Failure',
              '没有 llw0': 'without local llw0', '视频连接没有路由': 'No network route', '视频连接创建失败': 'Failed to create nw_connection for RTP', '随航 32002': 'Unable to retrieve NWConnection', '随航握手失败': 'failed to add SideCar to RTG'}
    found = {k: text.count(v) for k, v in checks.items()}
    seen = input('相机或随航有画面吗？(y/n，分别说明也可以，比如 相机y 随航n) ').strip().lower()
    line = f'{name}: 画面 {seen or "?"}；日志 {found}；计数 前 {a} 后 {z}'
    print(line, flush=True)
    lines.append(line)
    return seen == 'y' or seen.count('y') >= 2

def main():
    assert os.geteuid() == 0, '请通过 开始相机实验.command 运行'
    if run('sysctl', '-n', UMI).returncode:
        sys.exit('当前运行的不是 1.1.53，请先重启。')
    if 'awdl0' not in run('ifconfig', '-l').stdout.split():
        sys.exit('awdl0 还没有创建，请等几分钟再运行。')
    home = channel()
    print(f'电脑当前 {home}。实时会话期间系统只排 149 和手机所在的信道，电脑请连手机的 5GHz 热点（149 信道）再测。')
    if '149' not in home and input('电脑不在 149 信道，仍然继续吗？(y/n) ').strip().lower() != 'y':
        sys.exit('已退出，没有改动任何开关。')
    print('手机解锁放在旁边。这个实验可能让隔空投送暂时异常，重启后恢复。请先保存工作。')
    input('准备好后按回车。')
    lines = [f'开始 {datetime.datetime.now()} {home}']
    try:
        setv(CACHE, 1)
        setv(UMI, 1)
        if not phase('第一步：只开 UMI 握手', lines):
            setv(LLW, 1)
            print('第二步：创建 llw0，会重启 wifip2pd。')
            run('killall', 'wifip2pd')
            for _ in range(75):
                time.sleep(1)
                if 'llw0' in run('ifconfig', '-l').stdout.split():
                    break
            state = run('ifconfig', '-v', 'llw0').stdout
            line = 'llw0: ' + (state.replace('\n', ' | ')[:900] if state else '没有创建')
            print(line, flush=True)
            lines.append(line)
            lines.append(f"驱动状态: {props()}")
            lines.append('接口列表: ' + run('ifconfig', '-l').stdout.strip())
            lines.append(f"awdl0 还在: {'awdl0' in run('ifconfig', '-l').stdout.split()}")
            if state:
                phase('第二步：UMI 加 llw0', lines)
        input('\n最后请从电脑向手机发一个文件，确认隔空投送是否还正常，然后按回车。')
        lines.append('发送结果：' + input('发送成功吗？(y/n) ').strip())
    finally:
        setv(CACHE, 0)
        setv(UMI, 0)
        setv(LLW, 0)
    path = HERE/f"camera-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt"
    path.write_text('\n'.join(lines) + '\n')
    print('已结束，UMI 已关闭；如果创建了 llw0，它留到下次重启。结果已保存：', path.name)
main()
