import json,subprocess,time,pathlib,os,sys
base=pathlib.Path.cwd();old=base/'work/awdl-held-1153/tests';new=base/'work/awdl-speed-1154/tests';new.mkdir(exist_ok=True)
names=sorted(p.stem for p in old.glob('*.log'))
env=dict(os.environ,MAC_KERNEL_SDK=str(base/'work/airportbz-deps/MacKernelSDK'));res=[]
for n in names:
    t=time.time();s=base/'work/airportbz/scripts'/(n+'.py')
    r=subprocess.run([sys.executable,str(s)],cwd=base/'work/airportbz',env=env,capture_output=True,text=True)
    (new/(n+'.log')).write_text(r.stdout+r.stderr);res.append(dict(name=n+'.py',returncode=r.returncode,seconds=round(time.time()-t,2)))
    print(n,r.returncode,flush=True)
ok=all(x['returncode']==0 for x in res);(base/'work/awdl-speed-1154/checks.json').write_text(json.dumps(dict(suites=res,all_passed=ok),indent=1));print('ALL',ok)
