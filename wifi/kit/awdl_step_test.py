"""Tahoe AWDL step-by-step test (1.4.2+; 1.4.1 panicked here, see BE201ActionBuffer.hpp): sudo python3 wifi/kit/awdl_step_test.py

1.4.0 started AWDL at boot and the Mac never finished booting, leaving no log. 1.4.1 starts nothing at boot; this
arms the same switches by hand from a running system and records every step so that a freeze still leaves the
last one on disk: each line of the log stream and each change of the driver's ItlwmAwdl* properties is written to
outputs/tahoe-wifi/awdl-step-<time>.log and flushed with F_FULLFSYNC before the next step.
Phase A: the AWDL interface alone (as 1.4.0's auto start, without the cross-channel switches).
Phase B, only if awdl0 is up and stable for 30 s: the cross-channel defaults of 1.2.25 (phy2, ROC 0x390024, pause).
If the Mac freezes: hold the power button, boot normally (1.4.1 does not arm at boot) and tell Claude."""
import fcntl, os, re, subprocess, sys, threading, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'outputs/tahoe-wifi'/f'awdl-step-{time.strftime("%Y%m%d-%H%M%S")}.log'
F_FULLFSYNC = 51
lock = threading.Lock()
fd = None

def w(line):
    with lock:
        os.write(fd, (time.strftime('%H:%M:%S ') + line.rstrip('\n') + '\n').encode(errors='replace'))
        fcntl.fcntl(fd, F_FULLFSYNC)

def sysctl(name, value):
    r = subprocess.run(['sysctl', f'debug.{name}={value}'], capture_output=True, text=True)
    w(f'SET debug.{name}={value} -> rc {r.returncode} {r.stdout.strip()} {r.stderr.strip()}')
    return r.returncode == 0

def props():
    text = subprocess.run(['ioreg', '-l', '-w0', '-r', '-c', 'AirportItlwm'], capture_output=True, text=True).stdout
    return dict(re.findall(r'"(ItlwmAwdl(?:VifStep|VifStage|VifStep\w*|IfCreate\w*|VifLate\w*|Failed\w*|Unarmed\w*|NativeRx\w*|LlwStage)\w*)" = ([^\n]+)', text))

def awdl0():
    r = subprocess.run(['ifconfig', 'awdl0'], capture_output=True, text=True)
    return r.returncode == 0 and 'flags=' in r.stdout, r.stdout.splitlines()[0] if r.stdout else r.stderr.strip()

stop = threading.Event()

def stream():
    pred = ('eventMessage CONTAINS "BE201VIF" OR process == "wifip2pd" OR '
            '(process == "kernel" AND (eventMessage CONTAINS[c] "awdl" OR eventMessage CONTAINS[c] "itlwm" OR '
            'eventMessage CONTAINS "IO80211" OR eventMessage CONTAINS[c] "panic")) OR '
            '(process == "airportd" AND eventMessage CONTAINS[c] "awdl")')
    p = subprocess.Popen(['/usr/bin/log', 'stream', '--style', 'compact', '--level', 'debug', '--predicate', pred],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        w('LOG ' + line[:600])
        if stop.is_set():
            break
    p.terminate()

def poll():
    last = {}
    while not stop.is_set():
        now = props()
        for k, v in now.items():
            if last.get(k) != v:
                w(f'PROP {k} = {v[:200]}')
        last = now
        time.sleep(0.2)

def wait_up(seconds):
    end = time.time() + seconds
    while time.time() < end:
        up, line = awdl0()
        if up:
            return True, line
        time.sleep(1)
    return awdl0()

def main():
    global fd
    assert os.geteuid() == 0, 'run with sudo'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(OUT, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    print('log file:', OUT)
    ver = subprocess.run(['kextstat', '-b', 'com.zxystd.AirportItlwm'], capture_output=True, text=True).stdout.strip().splitlines()
    w('kextstat: ' + (ver[-1] if ver else 'AirportItlwm not loaded'))
    if not ver or '(1.4.' not in ver[-1] or '(1.4.0)' in ver[-1] or '(1.4.1)' in ver[-1]:
        w('STOP: AirportItlwm 1.4.2 or later is not the loaded driver'); print('AirportItlwm 1.4.2+ not loaded'); return 1
    if subprocess.run(['sysctl', 'debug.be201_awdl_vif_arm'], capture_output=True).returncode:
        w('STOP: debug.be201_awdl_vif_arm missing (AWDL controls not registered)'); print('controls missing'); return 1
    threading.Thread(target=stream, daemon=True).start()
    threading.Thread(target=poll, daemon=True).start()
    time.sleep(2)
    w('PHASE A: interface switches as 1.4.0 auto start, no cross-channel')
    for name, value in (('be201_awdl_vif_accept', 1), ('be201_awdl_vif_link', 1), ('be201_awdl_vif_aw', 1),
                        ('be201_awdl_vif_radio', 1), ('be201_awdl_vif_rx', 1), ('be201_awdl_vif_tx', 1),
                        ('be201_awdl_vif_data', 1), ('be201_awdl_own_queue', 1), ('be201_awdl_txagg', 1),
                        ('be201_awdl_own_fix', 3), ('be201_awdl_umi', 1), ('be201_awdl_cache_rtg', 1),
                        ('be201_awdl_llw', 0), ('be201_awdl_cache_on', 1)):
        sysctl(name, value); time.sleep(0.3)
    w('ARM next (one attempt): capability bit 32 appears, wifip2pd may create awdl0')
    sysctl('be201_awdl_vif_arm', 1)
    up, line = wait_up(30)
    if not up:
        w(f'awdl0 not up after 30 s ({line}); turning Wi-Fi off and on so airportd reads the capabilities again')
        subprocess.run(['networksetup', '-setairportpower', 'en1', 'off']); time.sleep(3)
        subprocess.run(['networksetup', '-setairportpower', 'en1', 'on'])
        up, line = wait_up(60)
    w(f'awdl0 after phase A: up={up} {line}')
    if up:
        time.sleep(30)
        up, line = awdl0()
        w(f'awdl0 30 s later: up={up} {line}')
    if up:
        w('PHASE B: cross-channel defaults of 1.2.25 (phy2, ROC 0x390024, pause)')
        sysctl('be201_awdl_phy2', 1); time.sleep(1)
        sysctl('be201_awdl_roc', 0x390024); time.sleep(1)
        sysctl('be201_awdl_pause', 1)
        time.sleep(30)
        w(f'awdl0 after phase B: up={awdl0()[0]}')
    stop.set(); time.sleep(1)
    w('DONE')
    print('done; awdl0 up:', awdl0()[0], '| log:', OUT)
    return 0

if __name__ == '__main__':
    sys.exit(main())
