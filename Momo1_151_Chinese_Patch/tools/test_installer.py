"""Installer tests run only in temporary directories under the patch workspace."""
import tempfile,subprocess,sys,json,shutil
from pathlib import Path
from gm7 import *
B=Path(__file__).resolve().parents[1];R=B.parent
exe=(R/'momo1_v151.exe').read_bytes();m=json.loads((B/'patch.json').read_text(encoding='utf-8'))
results=[]
def run(root,*args,ok=True):
 p=subprocess.run([sys.executable,str(B/'apply_patch.py'),'--game-dir',str(root),*args],stdin=None,stdout=None,stderr=None)
 need((p.returncode==0)==ok,'Unexpected installer result '+str(args));return p.returncode
with tempfile.TemporaryDirectory(prefix='installer-test-',dir=B/'tools') as folder:
 root=Path(folder);(root/'data'/'graphic').mkdir(parents=True);(root/'data'/'saves'/'slot1').mkdir(parents=True)
 original=root/'momo1_v151.exe';original.write_bytes(exe)
 save=root/'data'/'saves'/'slot1'/'test-save';save.write_bytes(b'KEEP-SAVE')
 run(root,'--check');need(not (root/'momo1_v151_zh.exe').exists(),'Check wrote files');results.append('dry-run-no-writes')
 run(root);out=root/'momo1_v151_zh.exe';need(digest(out.read_bytes())==m['target_sha256'],'Wrong installed EXE');results.append('install-target-hash')
 run(root);results.append('idempotent-install')
 run(root,'--remove');need(not out.exists(),'Localized EXE not removed');need(save.read_bytes()==b'KEEP-SAVE' and original.read_bytes()==exe,'Original/save changed');results.append('remove-preserves-original-and-saves')
 original.write_bytes(exe[:-1]+bytes([exe[-1]^1]));run(root,'--check',ok=False);need(not out.exists(),'Unsupported input wrote output');results.append('reject-modified-source')
 original.write_bytes(exe);run(root);out.write_bytes(b'UNKNOWN FILE');run(root,ok=False);run(root,'--remove',ok=False);need(out.read_bytes()==b'UNKNOWN FILE','Unknown output overwritten');results.append('reject-unknown-existing-files')
print(json.dumps({'passed':results,'count':len(results)},indent=2))
(B/'installer_test_report.json').write_text(json.dumps({'passed':results,'count':len(results)},indent=2),encoding='utf-8')
