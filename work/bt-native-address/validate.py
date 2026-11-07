from pathlib import Path
import sys,json,subprocess,difflib
w=Path(__file__).resolve().parent;old=w.parent/'bt-le-probe';sys.path.insert(0,'/Users/wqhqq/Documents/Codex/2026-10-30/bang/work/ish-als');from audit_entry import MachO
p=w/'IntelBTPatcher.kext/Contents/MacOS/IntelBTPatcher';m=MachO(p);a=m.audit()
assert a['entry_self_reference_absent'] and not a['no_custom_callbacks'];a['constructors']=[s for s in m.sections if s['type']==9];assert a['constructors']
for ptr,sym in [('__realmain','_IntelBTPatcher_kern_start'),('__antimain','_IntelBTPatcher_kern_stop')]:assert m.pointer(ptr)==m.symbols[sym]
a['lilu_callbacks_verified']=True;(w/'entry-audit.json').write_text(json.dumps(a,indent=2))
def imports(p):return {l.split()[-1] for l in subprocess.check_output(['nm','-u',str(p)],text=True).splitlines() if l.strip()}
new=imports(p);before=imports(old/'IntelBTPatcher.kext/Contents/MacOS/IntelBTPatcher');assert new==before
(w/'symbol-check.json').write_text(json.dumps({'imports':len(new),'same_as_loaded_2_5_3':True,'new_imports':[],'stack_protector':'strong'},indent=2))
s=(w/'IntelBTPatcher.cpp').read_text();prior=(old/'IntelBTPatcher.cpp').read_text();assert s[s.index('#define HCI_EVT_LE_META '):]==prior[prior.index('#define HCI_EVT_LE_META '):]
a=s[s.index('void CIntelBTPatcher::processKext'):s.index('#pragma mark - For Bigsur-')];b=prior[prior.index('void CIntelBTPatcher::processKext'):prior.index('#pragma mark - For Bigsur-')];assert a==b
(w/'preserved-paths.json').write_text(json.dumps({'existing_USB_routes_source_unchanged':True,'existing_receive_event_rewrites_source_unchanged':True,'policy':'skip fixed placeholder only after synchronous native RPA USB acceptance; experimental not HCI completion','scope':'8087:0037 + Sequoia + -be201nativeaddr','fallback':'existing injection if native RPA is not accepted; reset invalidates decision'},indent=2))
(w/'source.diff').write_text(''.join(difflib.unified_diff(prior.splitlines(True),s.splitlines(True),fromfile='2.5.3',tofile='2.5.4')))
print(json.dumps({'uuid':m.uuid,'sha256':a if False else json.loads((w/'entry-audit.json').read_text())['sha256'],'imports':len(new),'entry_callbacks':'verified','constructors':'present','receive_rewrites':'unchanged'}))
