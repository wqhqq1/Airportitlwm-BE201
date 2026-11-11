"""1.1.80 and later: reads the driver's last 90 seconds (ItlwmAwdlHistory) and the scan counters, prints them per second and
saves them next to this file. Read only. Run it right after an AirDrop stalls."""
import datetime, re, struct, subprocess
from pathlib import Path
FMT = '<9I2HI'
SIZE = struct.calcsize(FMT)
FLAGS = [(1, '队列'), (2, '卡住'), (4, '扫描中'), (8, '看门狗'), (16, '独立'), (32, '等空位'), (64, '大流量'), (128, '扫描暂缓')]

def main():
    text = subprocess.run(['ioreg', '-l', '-w0'], capture_output=True, text=True).stdout
    m = re.search(r'"ItlwmAwdlHistory" = <([0-9a-f]+)>', text)
    if not m:
        raise SystemExit('没有找到记录：驱动早于 1.1.80，或者 AWDL 还没启动。')
    raw = bytes.fromhex(m[1])
    rows = [struct.unpack_from(FMT, raw, i) for i in range(0, len(raw) - SIZE + 1, SIZE)]
    rows = [r for r in rows if r[0]]
    extra = {k: int(v) for k, v in re.findall(r'"(ItlwmWclScan(?:Deferred|RunStarted|Req)|ItlwmAwdlOwnRecovers)" = (\d+)', text)}
    lines = [f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {extra}',
             '秒  发送帧  完成帧  聚合失败 BA通知 忙 等空位 重建 同步帧 队列深度 AP队列 状态']
    prev = None
    for r in rows:
        t, sent, ok, fail, ba, busy, stalls, rec, mc, oq, aq, fl = r
        if prev:
            d = [x - y for x, y in zip(r[1:9], prev[1:9])]
            flags = ' '.join(n for b, n in FLAGS if fl & b)
            lines.append(f'{t:6d} {d[0]:7d} {d[1]:7d} {d[2]:7d} {d[3]:6d} {d[4]:5d} {d[5]:5d} {d[6]:3d} {d[7]:5d} {oq:7d} {aq:6d} {flags}')
        prev = r
    out = Path(__file__).resolve().parent / f'stall-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt'
    out.write_text('\n'.join(lines) + '\n')
    out.chmod(0o600)
    print('\n'.join(lines[-40:]))
    print('已保存：', out.name)

main()
