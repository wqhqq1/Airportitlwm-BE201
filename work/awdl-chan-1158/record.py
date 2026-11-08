"""1.1.58: AWDL starts by itself, so this only records. 15 minutes of counters and logs, kept on disk. Changes nothing."""
from pathlib import Path
import datetime, json, os, plistlib, subprocess, time

HERE = Path(__file__).resolve().parent
PREDICATE = ('process == "wifip2pd" OR process == "UniversalControl" OR process == "ContinuityCaptureAgent" OR process == "rapportd" '
             'OR eventMessage CONTAINS "BE201VIF" OR eventMessage CONTAINS[c] "awdl" OR eventMessage CONTAINS "panic"')

def run(*a, timeout=15):
    return subprocess.run(a, capture_output=True, text=True, timeout=timeout)

def props():
    out = {}
    try:
        r = subprocess.run(['ioreg', '-a', '-r', '-n', 'pci8086,7740', '-l', '-w0'], capture_output=True, timeout=10)
    except subprocess.TimeoutExpired:
        return dict(ioreg_timeout=True)
    def walk(n):
        for k, v in n.items():
            if k.startswith(('ItlwmAwdl', 'ItlwmFw')) and isinstance(v, (int, bool, str)):
                out[k] = v
        for c in n.get('IORegistryEntryChildren', []):
            walk(c)
    if r.returncode == 0 and r.stdout:
        for row in plistlib.loads(r.stdout):
            walk(row)
    return out

def main():
    assert os.geteuid() == 0, '请通过 开始记录.command 运行'
    names = run('ifconfig', '-l').stdout.split()
    p = props()
    print('awdl0：', '已创建' if 'awdl0' in names else '还没有创建')
    print('自动启动：', '已开启' if p.get('ItlwmAwdlAuto') else ('上次开机 panic，本次跳过' if p.get('ItlwmAwdlAutoSkippedAfterPanic') else '未开启'))
    print('已在后台记录 15 分钟，这个窗口可以关闭。')
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    if os.fork():
        return
    os.setsid()
    null = os.open(os.devnull, os.O_RDWR)
    for n in (0, 1, 2):
        os.dup2(null, n)
    def create(path):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        os.fchown(fd, int(os.environ.get('SUDO_UID', 0)), int(os.environ.get('SUDO_GID', 0)))
        return fd
    counters = create(HERE/f'vif-watch-{stamp}.ndjson')
    logged = create(HERE/f'vif-watch-log-{stamp}.ndjson')
    log = subprocess.Popen(['/usr/bin/log', 'stream', '--style', 'ndjson', '--level', 'debug', '--predicate', PREDICATE], stdout=logged, stderr=subprocess.DEVNULL)
    for _ in range(180):
        time.sleep(5)
        try:
            router = run('ipconfig', 'getoption', 'en1', 'router').stdout.strip()
            row = dict(at=time.time(), props=props(), awdl0=run('ifconfig', 'awdl0').stdout, netstat=run('netstat', '-I', 'awdl0', '-b').stdout,
                       gateway_ok=bool(router) and run('ping', '-c', '1', '-t', '2', router).returncode == 0)
        except Exception as e:
            row = dict(at=time.time(), error=str(e))
        os.write(counters, (json.dumps(row) + '\n').encode())
    log.terminate()
    os._exit(0)
main()
