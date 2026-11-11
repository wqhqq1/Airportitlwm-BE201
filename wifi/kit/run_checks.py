"""Runs the driver's offline test suites; logs go to tests/, the result to checks.json (package.py needs it)."""
import json, os, pathlib, subprocess, sys, time
KIT = pathlib.Path(__file__).resolve().parent
BASE = KIT.parents[1]
SUITES = ['test-awdl-abi', 'test-awdl-ba', 'test-awdl-ctx', 'test-awdl-if', 'test-awdl-native', 'test-awdl-probe',
          'test-awdl-rx', 'test-awdl-tx', 'test-awdl-vif-abi', 'test-awdl-vif', 'test-be201-he', 'test-beacon-peer-tx',
          'test-bz-boot-checks', 'test-continuity-diagnostics', 'test-hotspot-client-ie', 'test-hotspot-join',
          'test-hotspot-mfp', 'test-join-rsn-diag', 'test-key-command-ack', 'test-p2p-mac', 'test-sta-authorized',
          'test-tlc-mode-flags', 'test-wcl-disconnect', 'test-wcl-switch']
logs = KIT/'tests'
logs.mkdir(exist_ok=True)
env = dict(os.environ, MAC_KERNEL_SDK=str(BASE/'deps/MacKernelSDK'))
res = []
for n in SUITES:
    t = time.time()
    r = subprocess.run([sys.executable, str(BASE/'wifi/airportbz/scripts'/(n+'.py'))], cwd=BASE/'wifi/airportbz',
                       env=env, capture_output=True, text=True)
    (logs/(n+'.log')).write_text(r.stdout+r.stderr)
    res.append(dict(name=n+'.py', returncode=r.returncode, seconds=round(time.time()-t, 2)))
    print(n, r.returncode, flush=True)
ok = all(x['returncode'] == 0 for x in res)
version = json.loads((KIT/'release.json').read_text())['version']
(KIT/'checks.json').write_text(json.dumps(dict(version=version, suites=res, all_passed=ok), indent=1)+'\n')
print('ALL', ok)
sys.exit(0 if ok else 1)
