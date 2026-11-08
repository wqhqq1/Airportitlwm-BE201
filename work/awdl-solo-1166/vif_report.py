"""Read the newest vif-stream file and any panic report written after it. Read only."""
from pathlib import Path
import json, re

def read_stream(p):
    """Return the facts in one stream file. Tolerates a torn last line from a crash."""
    steps, unsupported, summary, started, boot, reg_step = [], [], None, None, None, None
    props = {}
    create_failed = None
    for line in p.read_bytes().splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        if 'test_started' in d:
            started, boot = d['test_started'], d.get('boot_uuid')
        if d.get('reg_step'):
            reg_step = d['reg_step']
        if d.get('changed'):
            props.update(d['changed'])
        if 'test_summary' in d:
            summary = d
        m = d.get('eventMessage', '')
        if m.startswith('BE201VIF'):
            steps.append(m)
            u = re.match(r'BE201VIF unsupported id=(\d+)', m)
            if u:
                unsupported.append(int(u[1]))
        if 'Failed to create interface' in m:
            create_failed = m
    return dict(file=p.name, started=started, boot_uuid=boot, finished=summary is not None, summary=summary,
                steps=[s for s in steps if 'unsupported' not in s], last_step=steps[-1] if steps else None, last_registry_step=reg_step, last_properties=props,
                unsupported_ids=sorted(set(unsupported)), wifip2pd_create_failure=create_failed)

def report(here, diagnostics=Path('/Library/Logs/DiagnosticReports')):
    files = sorted(here.glob('vif-stream-*.ndjson'))
    if not files:
        return dict(present=False)
    try:
        out = dict(present=True, **read_stream(files[-1]))
    except PermissionError:
        return dict(present=True, file=files[-1].name, readable=False)
    watched = sorted(here.glob('vif-watch-2*.ndjson'))
    if watched:
        rows = []
        for line in watched[-1].read_bytes().splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
        if rows:
            out['watch'] = dict(file=watched[-1].name, rows=len(rows), first_at=rows[0]['at'], last=rows[-1])
    since = files[-1].stat().st_ctime
    try:
        out['panic_reports_after_start'] = sorted(p.name for p in diagnostics.glob('*.panic') if p.stat().st_mtime >= since)
    except OSError:
        out['panic_reports_after_start'] = None
    return out

if __name__ == '__main__':
    print(json.dumps(report(Path(__file__).resolve().parent), ensure_ascii=False, indent=2))
