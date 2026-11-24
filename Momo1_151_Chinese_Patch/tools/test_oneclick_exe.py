"""Black-box integration test for the shipped one-file GUI/CLI executable."""
import argparse,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
from gm7 import need

PATCH=Path(__file__).resolve().parents[1]
REPO=PATCH.parent
EXE=PATCH/'Momodora1ZH_Setup.exe'
MANIFEST=json.loads((PATCH/'patch.json').read_text(encoding='utf-8'))
ORIGINAL_SHA=MANIFEST['source_sha256']


def sha(data):return hashlib.sha256(data).hexdigest()

def run(action,folder,ok=True):
 env=os.environ.copy()
 env['PATH']=r'C:\\Windows\\System32;C:\\Windows'
 p=subprocess.run([str(EXE),action,str(folder)],cwd=PATCH,stdin=subprocess.DEVNULL,
   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=180,check=False,env=env)
 need((p.returncode==0)==ok, f'{action} returned {p.returncode}, expected ok={ok}')
 return p.returncode


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source-exe',type=Path,required=True);args=parser.parse_args()
 source=args.source_exe.resolve()
 need(EXE.is_file(),'Built GUI EXE not found')
 original=source.read_bytes()
 need(sha(original)==ORIGINAL_SHA,'Local source executable hash does not match patch')
 tests=[]
 with tempfile.TemporaryDirectory(prefix='momodora-oneclick-test-',dir=REPO) as temp:
  folder=Path(temp)
  graphics=folder/'data'/'graphic';graphics.mkdir(parents=True)
  saves=folder/'data'/'saves'/'slot1';saves.mkdir(parents=True)
  game=folder/'momo1_v151.exe';game.write_bytes(original)
  saved=saves/'existing.ini';saved.write_bytes(b'KEEP-ORIGINAL-SAVE')

  run('--cli-check',folder);need(not (folder/'momo1_v151_zh.exe').exists(),'Check mode wrote output')
  tests.append('embedded-manifest-and-atlas-version-check')
  run('--cli-install',folder)
  patched=folder/'momo1_v151_zh.exe'
  target_atlas=graphics/'momo1_zh_text.png'
  receipt=graphics/'momo1_zh_install.json'
  need(sha(patched.read_bytes())==MANIFEST['target_sha256'],'Unexpected patched EXE hash')
  need(sha(target_atlas.read_bytes())==MANIFEST['atlas_sha256'],'Unexpected atlas hash')
  record=json.loads(receipt.read_text(encoding='utf-8'))
  need(record['exe_sha256']==MANIFEST['target_sha256'],'Receipt EXE hash mismatch')
  tests.append('onefile-patch-build-and-target-sha256')
  run('--cli-install',folder);tests.append('same-version-install-idempotence')
  target_atlas.unlink()
  run('--cli-install',folder,ok=False)
  need(not target_atlas.exists(),'A partial install was silently accepted')
  tests.append('partial-receipt-missing-file-is-rejected')
  target_atlas.write_bytes(Path(PATCH/'assets/momo1_zh_text.png').read_bytes())
  run('--cli-install',folder)
  need(sha(game.read_bytes())==ORIGINAL_SHA and saved.read_bytes()==b'KEEP-ORIGINAL-SAVE',
       'Install modified original or existing save')
  tests.append('original-and-existing-save-preserved')
  run('--cli-remove',folder)
  need(not patched.exists() and not target_atlas.exists() and not receipt.exists(),'Uninstall left patch files')
  need(sha(game.read_bytes())==ORIGINAL_SHA and saved.read_bytes()==b'KEEP-ORIGINAL-SAVE',
       'Uninstall modified original or existing save')
  tests.append('safe-uninstall-and-save-preservation')

  corrupt=game.read_bytes();game.write_bytes(corrupt[:-1]+bytes([corrupt[-1]^1]))
  run('--cli-install',folder,ok=False)
  need(not patched.exists() and not target_atlas.exists(),'Invalid game wrote patch files')
  tests.append('reject-modified-wrong-version-exe')
  game.write_bytes(original)

  patched.write_bytes(b'KEEP-UNKNOWN-OUTPUT')
  run('--cli-install',folder,ok=False)
  need(patched.read_bytes()==b'KEEP-UNKNOWN-OUTPUT' and not target_atlas.exists(),
       'Unknown output was overwritten or partial atlas was installed')
  tests.append('unknown-same-name-file-not-overwritten')

  patched.unlink()
  run('--cli-install',folder)
  patched.write_bytes(b'USER-MODIFIED-EXE')
  run('--cli-remove',folder,ok=False)
  need(patched.read_bytes()==b'USER-MODIFIED-EXE','Modified EXE was deleted')
  tests.append('modified-output-is-protected-from-uninstall')
 report={'exe_sha256':sha(EXE.read_bytes()),'exe_size_bytes':EXE.stat().st_size,
         'passed':tests,'count':len(tests),'original_sha256':sha(source.read_bytes()),
         'original_unchanged':sha(source.read_bytes())==ORIGINAL_SHA,
         'test_scope':'isolated temporary game clone; no live user save files used'}
 out=PATCH/'oneclick_exe_test_report.json'
 out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 sys.stdout.reconfigure(encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
