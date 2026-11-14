"""1.1.75 and later (1.2.25: in a pause the router's PHY keeps the router's width on the AWDL channel and no rate control changes (1.2.24 asserted the firmware at TLC); 1.2.24: pause mode, once file data flows the whole radio goes to the AWDL channel and the router waits, debug.be201_awdl_pause; 1.2.23: 0x80000/0x100000/0x200000 put back the 1.2.17 sequence aging, receive timestamps and slot flush for the presence A/B (presence_ab.py); 1.2.22: the sparse-peer gate is off by default (0x40000 turns it on): peer absences had quadrupled since 1.2.19; 1.2.21: a peer's last sequence counts for 20 s (was 2 s), and a bulk flow keeps the family in Data for 15 s after it; 1.2.20: the sparse-peer gate looks only at each frame's own receiver (1.2.19 had held frames to the iPad for an idle iPhone's slots); 1.2.19: frames to peers on 149 for fewer than 8 slots (an idle phone sending to this Mac) leave only in their 149 slots, 0x40000 turns it off; 1.2.18: received awdl0 packets carry their arrival time (QUIC had read stale send timestamps as ACK arrivals); 1.2.17: a unicast flow both ways keeps the family in Data mode for 4 s after it (8 packets a check), and a unicast frame the peer missed during an ROC gets up to 2 more turns; R2 default 60 s, default (continued) 60 s, default again 45 s; 1.2.16: within 60 s of an intent (the family widened, or unicast went out) every nearby peer's 149 slots count again, so the first send after boot resolves; 0x20000 covers every slot of a peer data goes to; R2 default 60 s, all data-peer slots 45 s, default again 45 s; 1.2.15: cross-channel is on at boot (be201_awdl_xchan); the tool puts back the switches it found when it ends; the union takes every peer data went to lately, or whose sequence is widened; 2 slots left to the AP by default again, 0x2000 leaves 1; 1.2.14: 1 slot left to the AP between 149 pieces by default, 0x2000 leaves 2; after the last phase cross-channel stays on until awdl0 goes quiet, so the transfer can finish; each phase names the receiving device; 1.2.13: the union follows the sequence of the peer data goes to (an idle iPhone nearby had overwritten the iPad's); A-MSDU through AUX left out again (TID 3 too: 166 sent, 16 completed); R2 default 60 s, again 45 s, 1-slot AP gap 45 s; 1.2.12: 7 slots per 149 piece by default with 2 left to the AP, 0x2000 leaves 1; the TID 3 switch now really rebuilds the AUX queue; R2 default 60 s, 1-slot AP gap 45 s, TID 3 queue 45 s, TID 3 + A-MSDU 45 s; 1.2.11: 6 slots per 149 piece by default, 0x2000 for 7; 0x8000 puts the AUX queue on TID 3, where A-MSDU may go again, stopped for the boot when one ROC sends 4 and none completes; R2 default 60 s, 7-slot pieces 45 s, TID 3 queue 45 s, TID 3 + A-MSDU 45 s; 1.2.10: long 149 runs covered in pieces of 5 slots with 2 left to the AP; no A-MSDU through AUX; R2 default 60 s, again 45 s, 6-slot pieces 45 s; 1.2.9: mode 4 covers the phone's 149 slots too (0x4000 for the family's only); the wait counts only data on awdl0; every phase reads sharingd's AirDrop log; 1.2.8: AUX frames use their own rate step (from VHT20 MCS8, down only on failures inside an ROC, never below HT MCS2); the AUX and link-wide rate steps are printed; 1.2.7: after mode 4 is on, wait up to 90 s for the transfer to start (2 MB out on awdl0 or the sequence widened) before the timed phases, and log that wait; 1.2.6: A-MSDU through AUX on TID 3, 0x2000 for 6 slots per run; R2 default, + A-MSDU, + A-MSDU and 6 slots; the phases that cannot move data (baseline, R1, the link-move check, after off) only with --full; 1.2.5: mode 4 sends non-QoS data and AUX frames stay on the AUX queue (QoS frames had gone out on the router's TID 0 queue); 500 ms pause after a failed ROC; AUX frames off the AUX queue and the own queue state printed; 1.2.4: the ROC is asked 12 ms before a 149 slot so the radio is there for the phone's AW, held frames go just after the boundary, 0x1000 turns it off; R2 default, again, without it; 1.2.3: held frames go 2 ms after an ROC starts and an ROC timer rewrites a stuck AUX write pointer; no new ROC for 2 s after 6 missed AP beacons; R2 default twice and phone-timed, no 80 MHz phase; 1.2.2: family timing by default again, 0x800 for the phone's; 5 slots per run; multicast headroom on the AUX ring; why flushes stop; R2 default 60 s, default at 80 MHz, phone-timed; 1.2.1: mode 4 ROCs timed by the phone's own sequence and boundaries, 0x800 for the family's; the phone's sequence and the offsets; R2 phone-timed, family-timed, phone-timed unclamped; 1.2.0: refill from each completion and ROC start, AUX ring 64, the DTIM clamp and 4 slots again by default; air time, rate and frames per ROC; R2 default, unclamped, 80 MHz; 1.1.99: no ring-full drops, FIFO hold of 256 with the family held back at 192, 6-slot cover, mode 4 without the DTIM clamp by default (0x400 asks for it); R2 default, then clamped, then 80 MHz; --on / --off switch cross-channel AirDrop on or off until reboot; 1.1.98: AUX unicast frames dropped at an ROC's end go back to the hold; R1 one short phase, then mode 4 with the DTIM cap, without it, and without it at 80 MHz; the A-MSDU and S phases are gone; 1.1.97: no ROC ADD within 10 ms of the last end, the R1 phase without the DTIM clamp first, and the last ADD before a fault; 1.1.96: chained ROCs over 64 TU slots; duty in mode 1 with and without the DTIM clamp, mode 4 with the honest sequence, then with A-MSDU and with 80 MHz ROCs, then the link back on the AP (cross-primary probe); 1.1.95: after mode 4, a phase with link 1 on 149 and session protection windows (phy2_te 3, kind 0) and ROC off, and AUX unicast data counted apart; 1.1.94: the move step and link 1's own queue, peer stations and TLC at a fault, and TLC re-sent by moves; 1.1.92: mode 4 holds unicast AWDL frames in the host for the next ROC; 1.1.91: why AUX frames fail and ROC timing; 1.1.90: also the last PHY command's channel and width; 1.1.89: baseline, mode 1 with P2P_TXRX, the AWDL link moved to 149 with ROC off, then mode 4 on that
link for 90 s; the first firmware error switches everything off at once): remain-on-channel (ROC) test beside a router link, phase by phase. The firmware gets an ROC for each run of
the AWDL sequence's other 5 GHz channel, through an AUX station, as Intel's Linux driver sends off-channel frames.
Results are saved after every phase, and each phase asks whether the phone sees this Mac and the transfer moves.
RAM switch only (debug.be201_awdl_roc); it is off again at the end or on any exit."""
import datetime, re, signal, subprocess, sys, threading, time
from pathlib import Path
ROC = 'debug.be201_awdl_roc'
PHY2 = 'debug.be201_awdl_phy2'
TE = 'debug.be201_awdl_phy2_te'
AMSDU = 'debug.be201_awdl_amsdu'
F80, FNODTIM = 0x100, 0x200
FDTIM = 0x400
FPHONE = 0x800
FNOPRE = 0x1000
FGAP1 = 0x2000
FDALL = 0x20000
FTID3 = 0x8000
FNOUNION = 0x4000
KEYS = ['RocMode', 'RocQid', 'RocSetups', 'RocSetupErr', 'RocSetupStage', 'RocTeardowns', 'RocAdds', 'RocAddErr', 'RocStarted', 'RocEnded', 'RocFailed', 'RocStale', 'RocRemoves', 'RocChan', 'RocTxSent', 'RocTxOk', 'RocTxFail', 'RocTxDrop', 'RocRxDuring', 'RocDiscovery', 'RocRxAny', 'RocRxAnyChan', 'RocRxAwdlAny', 'RxPhy2', 'RxHome', 'Phy2Chan', 'RocPhyHolds', 'RocPhyCancels', 'Phy2Switches', 'Phy2Err', 'FaultRoc', 'FaultPhy2', 'FaultLink', 'Phy2TlcRefreshes', 'Phy2TlcErr', 'Phy2OwnQuiesces', 'PeerTlc', 'PeerStations', 'OwnAgg', 'RocLateMaxUs', 'RocTxOkUcast', 'RocTxFailUcast', 'RocTxOkUcastData', 'RocTxFailUcastData', 'RocTxOkMcast', 'RocTxFailMcast', 'RocTxFailIn', 'RocTxFailOut', 'RocTxOkHere', 'RocTxOkAway', 'RocTxFailHere', 'RocTxFailAway', 'RocTxFailUnknown', 'RocTxFailTries', 'RocTxOkTries', 'RocLateN', 'RocLateSumMs', 'RocOnN', 'RocOnSumMs', 'RocHeld', 'RocReleased', 'RocHoldFull', 'RocHoldExpired', 'RocHoldFreed',
        'OwnSentPhy2', 'OwnDonePhy2', 'OwnFailPhy2', 'OwnLastStatusPhy2', 'OwnBaPhy2', 'OwnActive', 'CtxTeRequests', 'CtxTeStarted', 'CtxTeEnded', 'CtxTeFailed', 'CtxTeRemoved', 'CtxTeOwn',
        'RocCovSumMs', 'RocReqSumMs', 'RocChainAdds', 'RocChainSkips', 'RocChainGapN', 'RocChainGapSumMs', 'RocWideAdds', 'RocDwell25', 'RocDwell50', 'RocDwell75', 'RocDwellFull', 'TxOkHere', 'TxFailHere', 'TxOkAway', 'TxFailAway', 'AmsduSent', 'AmsduOk', 'AmsduFail', 'RocCapTu', 'RocAnnounce', 'RocReaddWaits', 'RocReaddMinUs', 'FaultRocAfterUs', 'FaultRocAdd', 'RocRequeued', 'RocRequeueDrop', 'RocRequeuedIn', 'DataHoldFlows', 'DataHoldReports', 'DataHoldPkts', 'RxStamped', 'RxUnstamped', 'RocGateTicks', 'RocGateWaits', 'DataHoldBulk', 'PauseState', 'PauseLastMs', 'PauseMaxMs', 'PauseErr', 'PauseSkips', 'PauseEnters', 'PauseExits', 'PauseAborts', 'PauseDrops', 'PauseNulls', 'PauseNullErr', 'PauseBmissIgnored', 'RocHoldOrder', 'RocHoldRing', 'RocHoldStalls', 'RocHoldKicks', 'RocHoldPeak', 'RocHoldFull', 'RocTxDrop', 'RocFlushDirect', 'RocAirN', 'RocAirMs', 'RocLastRate', 'RocSentPerRocMax', 'RocPeerTicks', 'RocPeerIdleTicks', 'RocPeerK', 'RocPeerLagN', 'RocPeerLagAbsMs', 'RocPeerLagUs', 'RocPeerWaits', 'RocFlushStopRing', 'RocFlushStopRule', 'RocKicks', 'RocKickTicks', 'RocKickReleases', 'RocBmissPauses', 'RocBmissSkips', 'RocBmissLast', 'RocPreArms', 'RocPreAdds', 'RocPreSkips', 'RocPreOnTime', 'RocPreLate', 'RocOffAux', 'RocFailPauses', 'RocRateStep', 'RocRateUps', 'RocRateDowns', 'DataRateMcsStep', 'RocUnionTicks', 'RocUnionSlots', 'RocDestTicks', 'DestSeqUpdates', 'RocTid', 'RocAmsduStuck', 'AmsduGaveUp',
        'SeqChan5', 'OwnSent', 'OwnOk', 'OwnFail', 'OwnRecovers', 'TxTripped', 'DataTx', 'DataRx', 'FirmwareFaults', 'FaultRearms']
COUNTERS = ['RocSetups', 'RocTeardowns', 'RocAdds', 'RocAddErr', 'RocStarted', 'RocEnded', 'RocFailed', 'RocStale', 'RocRemoves', 'RocTxSent', 'RocTxOk', 'RocTxFail', 'RocTxDrop', 'RocRxDuring', 'RocDiscovery', 'RocRxAny', 'RocRxAnyChan', 'RocRxAwdlAny', 'RxPhy2', 'RxHome', 'RocPhyHolds', 'RocPhyCancels', 'Phy2Switches', 'Phy2TlcRefreshes', 'Phy2OwnQuiesces', 'RocTxOkUcast', 'RocTxFailUcast', 'RocTxOkUcastData', 'RocTxFailUcastData', 'RocTxOkMcast', 'RocTxFailMcast', 'RocTxFailIn', 'RocTxFailOut', 'RocTxOkHere', 'RocTxOkAway', 'RocTxFailHere', 'RocTxFailAway', 'RocTxFailUnknown', 'RocTxFailTries', 'RocTxOkTries', 'RocLateN', 'RocLateSumMs', 'RocOnN', 'RocOnSumMs', 'RocHeld', 'RocReleased', 'RocHoldFull', 'RocHoldExpired', 'RocHoldFreed', 'OwnSent', 'OwnOk', 'OwnFail', 'OwnRecovers', 'OwnSentPhy2', 'OwnDonePhy2', 'OwnFailPhy2', 'OwnBaPhy2', 'CtxTeRequests', 'CtxTeStarted', 'CtxTeEnded', 'CtxTeFailed', 'CtxTeRemoved', 'CtxTeOwn', 'RocCovSumMs', 'RocReqSumMs', 'RocChainAdds', 'RocChainSkips', 'RocChainGapN', 'RocChainGapSumMs', 'RocWideAdds', 'RocDwell25', 'RocDwell50', 'RocDwell75', 'RocDwellFull', 'TxOkHere', 'TxFailHere', 'TxOkAway', 'TxFailAway', 'AmsduSent', 'AmsduOk', 'AmsduFail', 'RocReaddWaits', 'RocRequeued', 'RocRequeueDrop', 'RocRequeuedIn', 'DataHoldFlows', 'DataHoldReports', 'DataHoldPkts', 'RxStamped', 'RxUnstamped', 'RocGateTicks', 'RocGateWaits', 'DataHoldBulk', 'PauseEnters', 'PauseExits', 'PauseAborts', 'PauseDrops', 'PauseNulls', 'PauseNullErr', 'PauseBmissIgnored', 'RocHoldOrder', 'RocHoldRing', 'RocHoldStalls', 'RocHoldKicks', 'RocFlushDirect', 'RocAirN', 'RocAirMs', 'RocPeerTicks', 'RocPeerIdleTicks', 'RocPeerLagN', 'RocPeerLagAbsMs', 'RocPeerWaits', 'RocFlushStopRing', 'RocFlushStopRule', 'RocKicks', 'RocKickTicks', 'RocKickReleases', 'RocBmissPauses', 'RocBmissSkips', 'RocPreArms', 'RocPreAdds', 'RocPreSkips', 'RocPreOnTime', 'RocPreLate', 'RocOffAux', 'RocFailPauses', 'RocRateUps', 'RocRateDowns', 'RocUnionTicks', 'RocDestTicks', 'DestSeqUpdates', 'DataTx', 'DataRx']
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

def ref_sequence(text=None):
    # 1.2.1: the phone's (reference peer's) own sequence, from its sync frames.
    m = re.search(r'"ItlwmAwdlRefSeq" = <([0-9a-f]{32})>', text or ioreg())
    return ' '.join(str(b) for b in bytes.fromhex(m[1])) if m else '未知'

def dest_sequence(text=None):
    # 1.2.13: the sequence of the peer data goes to, which the union follows while fresh.
    m = re.search(r'"ItlwmAwdlDestSeq" = <([0-9a-f]{32})>', text or ioreg())
    return ' '.join(str(b) for b in bytes.fromhex(m[1])) if m else '未知'

def dest_peer(text=None):
    # 1.2.14: the device unicast data goes to (last three bytes of its AWDL address).
    m = re.search(r'"ItlwmAwdlDestPeer" = <([0-9a-f]{12})>', text or ioreg())
    return ':'.join(m[1][i:i + 2] for i in range(6, 12, 2)) if m else '未知'

def finish(lines, faulted, quiet_mb=0.5, limit=1800):
    # 1.2.14: 08:39 (1.2.13) the iPhone's transfer stopped at 300+ MB when the tool switched cross-channel off after its
    # last phase. Stay on until awdl0 sends less than quiet_mb in 15 s, or for limit seconds at most.
    print('最后一段结束：跨信道保持开启，直到文件传完（awdl0 15 秒内发出少于 0.5 MB 就关闭，最多 30 分钟；Ctrl-C 可提前结束）。', flush=True)
    t0, b0, quiet, last = time.monotonic(), obytes(), 0, obytes()
    z = props()
    while time.monotonic() - t0 < limit and not faulted(z):
        time.sleep(5)
        now = obytes()
        quiet = quiet + 1 if now - last < quiet_mb * 1e6 / 3 else 0
        last = now
        z = props()
        if int(time.monotonic() - t0) % 30 < 5:
            print(f'  收尾中：{int(time.monotonic() - t0)} 秒，继续发出 {(now - b0) / 1e6:.1f} MB', flush=True)
        if quiet >= 3:
            break
    t = time.monotonic() - t0
    mb = (obytes() - b0) / 1e6
    lines.append(f'收尾：保持开启 {t:.0f} 秒，继续发出 {mb:.1f} MB，平均 {mb / t if t else 0:.2f} MB/s；接收设备 {dest_peer()}；' + ('固件报错，提前结束' if faulted(z) else '传输已停下' if quiet >= 3 else '到达时间上限'))
    print(lines[-1], flush=True)
    return z

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

def getv(oid):
    r = run('sysctl', '-n', oid)
    return int(r.stdout.strip()) if not r.returncode and r.stdout.strip().lstrip('-').isdigit() else 0

START = {}

def restore():
    # 1.2.15: cross-channel may be on from boot; put back what the tool found (ROC last, once link 1 is set).
    setv(ROC, 0)
    setv(TE, 0)
    setv(AMSDU, 0)
    setv(PHY2, START.get(PHY2, 0))
    if START.get(ROC):
        setv(ROC, START[ROC])

def gateway():
    for line in run('route', '-n', 'get', 'default').stdout.splitlines():
        if 'gateway:' in line:
            return line.split()[-1]

# 1.1.94: ItlwmAwdlFaultLink, bits 0-3 the step of a link 1 move that was running.
STEPS = ['无', '结束窗口', '释放自有队列', '取消 ROC', 'TLC 降到 20 MHz', '链路停用', '链路脱离 PHY', 'PHY 换信道', '链路接上新 PHY', 'TLC 恢复 AP 宽度', '链路启用']
def link_fault(v):
    v = v or 0
    step = v & 15
    return (f"移动步骤 {STEPS[step] if step < len(STEPS) else step}，自有队列 {'有' if v & 0x10 else '无'}{'（聚合）' if v & 0x20 else ''}，"
            f"对端站点 {(v >> 8) & 0xff} 个，有 TLC 的 0x{(v >> 16) & 0xff:02X}")

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
    since = datetime.datetime.now()
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
            setv(TE, 0)
            setv(AMSDU, 0)
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
    # 1.1.96: share of the covered 149 time really spent there, chained gaps, dwell against request.
    duty = d.get('RocOnSumMs', 0) / d['RocCovSumMs'] if d.get('RocCovSumMs') else None
    gap = d.get('RocChainGapSumMs', 0) / d['RocChainGapN'] if d.get('RocChainGapN') else None
    dwell = [d.get(k, 0) for k in ('RocDwell25', 'RocDwell50', 'RocDwell75', 'RocDwellFull')]
    on = d.get('RocOnSumMs', 0) / d['RocOnN'] if d.get('RocOnN') else None
    share = d.get('RocOnSumMs', 0) / (seconds * 10)
    # 1.2.0: how full each ROC was, and how much of it the radio spent sending.
    per_roc = d.get('RocTxSent', 0) / d['RocStarted'] if d.get('RocStarted') else None
    per_ms = d.get('RocTxSent', 0) / d['RocOnSumMs'] if d.get('RocOnSumMs') else None
    air = d.get('RocAirMs', 0) * 1000 / d['RocAirN'] if d.get('RocAirN') else None
    busy = d.get('RocAirMs', 0) / d['RocOnSumMs'] if d.get('RocOnSumMs') else None
    lag = d.get('RocPeerLagAbsMs', 0) / d['RocPeerLagN'] if d.get('RocPeerLagN') else None
    line = (f"{name}: 隔空投送 {rate:.2f} MB/s；{family_peers(seconds + 5)}；路由器 {summary(res.get('gw', '')) if gw else '没有网关'}；"
            f"手机 {summary(res.get('peer', '')) if peer else '没有对端'}（awdl0 对端 {len(found)} 个）；时间表 {own_sequence(text)}；"
            f"ROC 模式 {z.get('RocMode')} 队列 {z.get('RocQid')} 建立错误 {z.get('RocSetupErr')}@{z.get('RocSetupStage')} 信道 {z.get('RocChan')}；变化 {d}；"
            f"关闭标记 {z.get('TxTripped')} 固件报错 {z.get('FwErrors')}；ROC 缺少条件 {z.get('ItlwmAwdlRocBlocked')}；"
            f"DMA 已用 {z.get('ItlwmDmaUsedKiB')} KiB 失败 {z.get('ItlwmDmaFailures')} 搁置 {z.get('ItlwmDmaRetiredKiB')} KiB；"
            f"路由器数据队列 {z.get('ItlwmMldDataQueues')} 聚合队列错误 {z.get('ItlwmAwdlOwnErr')}；"
            f"AP 端口标志 {z.get('ItlwmApPortValid')} 加密网络 {z.get('ItlwmApRsnOn')}；"
            f"窗口 请求 {z.get('CtxTeRequests')} 开始 {z.get('CtxTeStarted')} 结束 {z.get('CtxTeEnded')} 失败 {z.get('CtxTeFailed')}；"
            f"149 上自有队列 发出 {z.get('OwnSentPhy2')} 完成 {z.get('OwnDonePhy2')} 失败 {z.get('OwnFailPhy2')} 块确认 {z.get('OwnBaPhy2')} 最后状态 0x{(z.get('OwnLastStatusPhy2') or 0):X}；"
            f"链路信道 {z.get('Phy2Chan')} 换信道错误 {z.get('Phy2Err')} TLC 重发错误 {z.get('Phy2TlcErr')}；对端站点 {z.get('PeerStations')} 有 TLC 0x{(z.get('PeerTlc') or 0):02X} 自有队列聚合 {z.get('OwnAgg')}；"
            f"失败原因 重试上限 {st[0]}+{st[1]} 排空 {st[2]} 超时 {st[3]} 对方省电 {st[4]} 清队列 {st[5]} 中止 {st[6]} 其他 {st[7]}；"
            f"ROC 平均晚开始 {f'{late:.1f}' if late is not None else '?'} ms 最晚 {(z.get('RocLateMaxUs') or 0) / 1000:.1f} ms 平均驻留 {f'{on:.1f}' if on is not None else '?'} ms；"
            f"149 占空比 {f'{duty * 100:.0f}%' if duty is not None else '?'}（驻留 {d.get('RocOnSumMs', 0)} ms / 覆盖 {d.get('RocCovSumMs', 0)} ms，申请 {d.get('RocReqSumMs', 0)} ms）；"
            f"149 时间占比 {share:.0f}%；每个 ROC 发出 {f'{per_roc:.0f}' if per_roc is not None else '?'} 帧（最多 {z.get('RocSentPerRocMax')}），每毫秒驻留 {f'{per_ms:.2f}' if per_ms is not None else '?'} 帧；"
            f"AUX 单播空口 每帧 {f'{air:.0f}' if air is not None else '?'} µs，占驻留 {f'{busy * 100:.0f}%' if busy is not None else '?'}，最后速率 0x{(z.get('RocLastRate') or 0):X}；"
            f"AUX 速率台阶 {(z.get('RocRateStep') or 10) - 10}（升 {d.get('RocRateUps', 0)} 降 {d.get('RocRateDowns', 0)}，-1 是 VHT MCS8，0 是 HT MCS7），全局台阶 {z.get('DataRateMcsStep')}；直接补发 {d.get('RocFlushDirect', 0)}；"
            f"最近单播目标 {dest_peer(text)}；手机时间表 {ref_sequence(text)}；数据对端合并时间表 {dest_sequence(text)}（跟随 {d.get('RocDestTicks', 0)} 个时隙，收到 {d.get('DestSeqUpdates', 0)} 次）；按手机定时 {d.get('RocPeerTicks', 0)} 个时隙 无 149 {d.get('RocPeerIdleTicks', 0)}，"
            f"手机比本机 时隙号差 {z.get('RocPeerK')} 边界差 平均 {f'{lag:.1f}' if lag is not None else '?'} ms 最后 {((z.get('RocPeerLagUs') or 1000000) - 1000000) / 1000:.1f} ms，"
            f"等手机开始 {d.get('RocPeerWaits', 0)}；补发停下 环满 {d.get('RocFlushStopRing', 0)} 等 ROC {d.get('RocFlushStopRule', 0)}；"
            f"提前上 149 申请 {d.get('RocPreAdds', 0)}/{d.get('RocPreArms', 0)} 次（跳过 {d.get('RocPreSkips', 0)}），时隙开始前已就位 {d.get('RocPreOnTime', 0)} 次 迟到 {d.get('RocPreLate', 0)} 次；"
            f"ROC 期间收到手机的帧 {d.get('RxPhy2', 0)}；该走 AUX 却走了别的队列 {d.get('RocOffAux', 0)} 帧，自有队列激活 {z.get('OwnActive')}，ROC 失败后暂停 {d.get('RocFailPauses', 0)} 次；AUX 队列重新唤醒 {d.get('RocKicks', 0)} 次（定时器 {d.get('RocKickTicks', 0)} 次，延后放行 {d.get('RocKickReleases', 0)} 次）；"
            f"路由器漏信标暂停 {d.get('RocBmissPauses', 0)} 次 跳过 {d.get('RocBmissSkips', 0)}，最近连续漏 {z.get('RocBmissLast')} 个；ROC 结束时被丢回暂存的单播 {d.get('RocRequeued', 0)}（其中 ROC 期间对方没收到再发 {d.get('RocRequeuedIn', 0)}）未能放回 {d.get('RocRequeueDrop', 0)}；系统数据模式保持 {d.get('DataHoldFlows', 0)} 次（大流量 {d.get('DataHoldBulk', 0)} 次）补计 {d.get('DataHoldReports', 0)} 次 {d.get('DataHoldPkts', 0)} 包；接收时间戳 已设 {d.get('RxStamped', 0)} 未设 {d.get('RxUnstamped', 0)}；稀疏对端等时隙 暂存 {d.get('RocGateTicks', 0)} 帧 补发停下 {d.get('RocGateWaits', 0)} 次；暂停上网 进入 {d.get('PauseEnters', 0)} 退出 {d.get('PauseExits', 0)} 放弃 {d.get('PauseAborts', 0)} 次，丢弃路由器帧 {d.get('PauseDrops', 0)}，空帧 {d.get('PauseNulls', 0)}（错 {d.get('PauseNullErr', 0)}），忽略漏信标 {d.get('PauseBmissIgnored', 0)}，状态 {z.get('PauseState')} 最近 {z.get('PauseLastMs')} ms 最长 {z.get('PauseMaxMs')} ms 错误码 {z.get('PauseErr')} 路由器过宽跳过 {z.get('PauseSkips')}；"
            f"AUX 单播数据 成功 {d.get('RocTxOkUcastData', 0)} 失败 {d.get('RocTxFailUcastData', 0)}；"
            f"暂存 排队 {d.get('RocHoldOrder', 0)} 满环 {d.get('RocHoldRing', 0)} 让系统等待 {d.get('RocHoldStalls', 0)} 唤醒 {d.get('RocHoldKicks', 0)} 最多 {z.get('RocHoldPeak')} 挤掉 {d.get('RocHoldFull', 0)} 环满丢弃 {d.get('RocTxDrop', 0)}；重加间隔 最短 {(z.get('RocReaddMinUs') or 0) / 1000:.1f} ms 推迟 {d.get('RocReaddWaits', 0)} 次；"
            f"接续 ROC {d.get('RocChainAdds', 0)} 跳过 {d.get('RocChainSkips', 0)} 平均间隔 {f'{gap:.1f}' if gap is not None else '?'} ms；ROC 上限 {z.get('RocCapTu')} TU 如实宣布 {z.get('RocAnnounce')}；"
            f"驻留/申请 <25% {dwell[0]} <50% {dwell[1]} <75% {dwell[2]} 其余 {dwell[3]}；80 MHz ROC {d.get('RocWideAdds', 0)}；"
            f"A-MSDU 发出 {d.get('AmsduSent', 0)} 成功 {d.get('AmsduOk', 0)} 失败 {d.get('AmsduFail', 0)} 卡住停用 {z.get('RocAmsduStuck', 0)} 已停用 {z.get('AmsduGaveUp', 0)}；AUX 队列 TID {z.get('RocTid', '?')}；成功帧重传 {d.get('RocTxOkTries', 0)}；"
            f"按手机时间表 在场 成功 {d.get('TxOkHere', 0)} 失败 {d.get('TxFailHere', 0)} 不在 成功 {d.get('TxOkAway', 0)} 失败 {d.get('TxFailAway', 0)}；"
            f"最后一条 PHY 命令 信道 {z.get('ItlwmPhyChannel')} 宽度 {z.get('ItlwmPhyWidth')} 位置 {z.get('ItlwmPhyCtrlPos')}；出错停用 {z.get('ItlwmAwdlPhy2FaultHolds')}")
    if fault_at is not None or z.get('FwErrors', 0) > FW0[0]:
        line += (f"；固件报错 第 {fault_at} 秒 错误 0x{(z.get('ItlwmFwErrorId') or 0):08X} 命令 0x{(z.get('ItlwmFwErrorCmd') or 0):06X} "
                 f"数据 {z.get('ItlwmFwErrorData1')} 当时 ROC 0x{(z.get('FaultRoc') or 0):06X} 链路 0x{(z.get('FaultPhy2') or 0):06X}；{link_fault(z.get('FaultLink'))}；"
                 f"{last_add(z.get('FaultRocAfterUs'), z.get('FaultRocAdd'))}")
    line += '；' + airdrop_log(since)  # 1.2.9
    print(line, flush=True)
    lines.append(line)
    lines.append(f"{name} 用户：" + input('这一段里，手机分享面板能看到这台电脑吗？电脑上的传输有没有动？（直接描述，回车继续）').strip())
    save(lines, PATH)
    return z, d

def last_add(after_us, add):
    # 1.1.97: the last ROC ADD before the fault: how soon after the previous end, from where, and how long.
    if add is None:
        return '最后一次 ROC 申请 未知'
    src = {1: '时隙', 2: '接续', 3: '发现'}.get(add & 0xFF, '无')
    after = '1 s 以上或没有上一次' if after_us is None or after_us >= 1000000 else f'{after_us / 1000:.1f} ms'
    return f'最后一次 ROC 申请 来自{src}，距上次结束 {after}，时长 {add >> 8} TU'

def _closed(signum, frame):
    raise KeyboardInterrupt

signal.signal(signal.SIGHUP, _closed)
signal.signal(signal.SIGTERM, _closed)

FW0 = [0]  # firmware errors before the test: anything above is new
PATH = Path(__file__).resolve().parent / f"roc-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt"

def airdrop_log(since):
    # 1.2.9: what sharingd did since then: Bonjour resolutions that failed, asks that failed, QUIC on awdl0 that came up.
    # On 22:24 the resolution of the phone failed after 30 s ("DNS Error: Refused") and only the last try connected.
    out = run('/usr/bin/log', 'show', '--start', since.strftime('%Y-%m-%d %H:%M:%S'), '--style', 'compact', '--predicate',
              'process == "sharingd" AND (eventMessage CONTAINS "DNS Error" OR eventMessage CONTAINS "Ask failed" OR '
              'eventMessage CONTAINS "ready multipath-socket-flow" OR eventMessage CONTAINS "SDAirDropSendService.transfers ADD")',
              timeout=60).stdout
    dns = out.count('DNS Error')
    asks = out.count('Ask failed')
    up = sum(1 for l in out.splitlines() if 'ready multipath-socket-flow' in l and 'awdl0' in l)
    sends = out.count('transfers ADD')
    return f'AirDrop 日志：新发送 {sends} 次，服务解析失败 {dns} 次，询问手机失败 {asks} 次，awdl0 上连接建立 {up} 次'

def seq149(text=None):
    # 1.2.7: how many of this Mac's 16 slots are on 149 (11 while a transfer runs, 2-5 idle).
    return own_sequence(text).split().count('149')

def wait_start(lines, faulted, limit=120):
    # 1.2.7: on 21:58 the timed phases began right after the link move (the no-data phases were skipped) and AirDrop
    # never started; at 21:39 it had had 55 s before them. Wait for the transfer itself before timing anything.
    print(f'ROC 已开启。现在请在电脑上重新把文件隔空投送给手机；等传输真正开始后才开始计时（最多 {limit} 秒）。', flush=True)
    a, b0, t0, since = props(), obytes(), time.monotonic(), datetime.datetime.now()
    started, z = False, a
    while time.monotonic() - t0 < limit:
        time.sleep(3)
        z = props()
        if faulted(z):
            break
        # 1.2.9: data only; on 22:24 a briefly widened sequence counted as a start after 4 s with nothing sent.
        if obytes() - b0 > 2_000_000:
            started = True
            break
    waited = int(time.monotonic() - t0)
    d = {k: z.get(k, 0) - a.get(k, 0) for k in COUNTERS}
    line = (f"等待传输开始: {'已开始' if started else f'{limit} 秒内没有开始'}，用时 {waited} 秒；时间表 {own_sequence()}；"
            f"手机时间表 {ref_sequence()}；接收设备时间表 {dest_sequence()}；awdl0 发出 {(obytes() - b0) / 1e6:.2f} MB；AUX 单播数据 成功 {d.get('RocTxOkUcastData', 0)} "
            f"失败 {d.get('RocTxFailUcastData', 0)}；数据帧 发出 {d.get('DataTx', 0)} 收到 {d.get('DataRx', 0)}；"
            f"ROC 期间收到手机的帧 {d.get('RxPhy2', 0)}；系统对端 {family_peers(5)}；{airdrop_log(since)}")
    print(line, flush=True)
    lines.append(line)
    save(lines, PATH)
    return z

def switch(on):
    # 1.1.99: cross-channel AirDrop on or off for this boot only (RAM switches), the same steps as the test.
    if run('sysctl', '-n', ROC).returncode:
        sys.exit('当前运行的驱动没有 ROC 开关，请先重启。')
    if not on:
        for oid in (ROC, TE, AMSDU, PHY2):
            setv(oid, 0)
        print('跨信道隔空投送已关闭。')
        return
    if props().get('TxTripped'):
        sys.exit('这次开机 AWDL 已经停用（固件报错），请重启后再开。')
    setv(ROC, 0)
    time.sleep(2)
    setv(PHY2, 1)
    for _ in range(10):
        time.sleep(1.5)
        if props().get('Phy2Chan'):
            break
    if not props().get('Phy2Chan'):
        setv(PHY2, 0)
        sys.exit('第二信道没有建立（可能路由器已在 149，或 AWDL 未启动），已恢复。')
    setv(ROC, 4 + 16 * 2 | (F80 if '--80' in sys.argv else 0))
    print('跨信道隔空投送已开启（重启后自动关闭；要关闭请运行 关闭跨信道隔空投送.command）。')

def main():
    if '--on' in sys.argv or '--off' in sys.argv:
        switch('--on' in sys.argv)
        return
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
        sys.exit('电脑现在不在路由器的其他信道上，ROC 不会启动。请连到不在 149 的路由器（最好 153 或 36，不要连手机热点）再运行。')
    # 1.2.0: on 23:17 the router was on 6, a channel AWDL also visits, so the baseline moved 2.2 MB/s without ROC.
    if home in (6, 44):
        print(f'注意：路由器在信道 {home}，AWDL 本来就会在这个信道停留，不开 ROC 也能传；'
              '要测 ROC，最好连到 6、44、149 以外的信道（例如 153 或 36）。', flush=True)
    full = '--full' in sys.argv
    print(f"iPhone 解锁放在旁边。准备一个 1 GB 以上的文件。全程约 {'5' if full else '3'} 分钟。", flush=True)
    if not full:
        print('只跑会传数据的阶段；要连基准、R1、链路检查和关闭后一起跑，请用 完整ROC实验.command。', flush=True)
    print('每一段结束时会问你手机能不能看到电脑、传输有没有动；结果每段都会保存。', flush=True)
    print('这个实验可能让 Wi-Fi 断开十几秒，请先保存工作。', flush=True)
    input('现在用隔空投送把文件发给手机（发不出去也没关系，保持发送窗口开着），然后按回车。')
    FW0[0] = props().get('FwErrors', 0)
    START.update({ROC: getv(ROC), PHY2: getv(PHY2)})
    lines = [f'开始 {datetime.datetime.now()} 当前信道 {home}；时间表 {seq}；开机默认 ROC {START[ROC]:#x} 第二信道 {START[PHY2]}']
    save(lines, PATH)
    activity = 2
    faulted = lambda z: z.get('TxTripped') or z.get('FwErrors', 0) > FW0[0]
    try:
        # 1.2.6 (user's request): baseline, R1 and the link-move check cannot move data; they run only with --full.
        z, d = props(), {}
        if full:
            z, d = phase('基准（ROC 关闭）', 20, lines)
            if not faulted(z):
                # 1.1.87: P2P_TXRX only; HOTSPOT with AUX transmit asserted the firmware on 16:08.
                # 1.1.98: one short duty check; 21:40 ran 141 ROCs both ways with no fault and full dwell.
                setv(ROC, (1 + 16 * activity) | FNODTIM)
                z, d = phase('R1 模式 1：整段 ROC（不按 DTIM 限制）', 15, lines)
        if not faulted(z) and (not full or d.get('RocStarted')):
            # 1.1.89: the link moves with ROC off, and only then do ROCs start. On 07:47 the move and the P2P_TXRX ROCs
            # overlapped and the firmware asserted at PHY_CONTEXT_CMD.
            setv(ROC, 0)
            time.sleep(2)
            setv(PHY2, 1)
            for _ in range(10):
                time.sleep(1.5)
                if props().get('Phy2Chan'):
                    break
            if full:
                z, d = phase('链路先移到 149（ROC 关闭），看能否收到手机的帧', 20, lines)
            else:
                z = props()
            if not faulted(z) and z.get('Phy2Chan'):
                setv(ROC, 4 + 16 * activity)
                z = wait_start(lines, faulted)
                if not faulted(z):
                    z, d = phase('R2 模式 4：默认', 60, lines)
                # 1.2.17: the all-slots phase is gone (12:05, iPad: 0.01 MB/s, as default); the hold needs time to climb.
                if not faulted(z):
                    print('下一段：同样设置继续计时；文件可以继续发。', flush=True)
                    z, d = phase('R2 模式 4：默认（继续）', 60, lines)
                if not faulted(z):
                    z, d = phase('R2 模式 4：默认（再次）', 45, lines)
                if not faulted(z):
                    setv(ROC, 4 + 16 * activity)
                    z = finish(lines, faulted)
                # 1.2.13: no A-MSDU phase. 08:18 (1.2.12) on the TID 3 queue: 166 sent, 16 completed, the transfer stopped.
                setv(AMSDU, 0)
            elif not faulted(z):
                lines.append('链路没有移到 149，模式 4 已跳过')
                print(lines[-1], flush=True)
        if faulted(z):
            lines.append('固件报错或 AWDL 已停用，后面的阶段已跳过')
            print(lines[-1], flush=True)
    finally:
        restore()
    time.sleep(3)
    if full:
        phase('关闭后', 20, lines)
    lines.append('传输结果：' + input('文件最后传完了吗？ ').strip())
    save(lines, PATH)
    print('已结束，开关已恢复成实验前的状态。结果已保存：', PATH.name)
main()
