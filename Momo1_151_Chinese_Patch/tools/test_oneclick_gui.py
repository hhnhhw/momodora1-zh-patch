"""Drive the packaged Windows GUI on an isolated game copy, no game is launched."""
import argparse, ctypes as c, hashlib, json, os, subprocess, sys, tempfile, time
from ctypes import wintypes as w
from pathlib import Path

PATCH=Path(__file__).resolve().parents[1]
EXE=PATCH/'Momodora1ZH_Setup.exe'
u=c.WinDLL('user32',use_last_error=True)
k=c.WinDLL('kernel32',use_last_error=True)
CB=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
u.EnumWindows.argtypes=[CB,w.LPARAM];u.EnumChildWindows.argtypes=[w.HWND,CB,w.LPARAM]
u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
u.IsWindowVisible.argtypes=[w.HWND];u.IsWindowVisible.restype=w.BOOL
u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
u.GetClassNameW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
u.GetWindowRect.argtypes=[w.HWND,c.POINTER(w.RECT)]
u.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
k.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD];k.CreateToolhelp32Snapshot.restype=w.HANDLE
k.CloseHandle.argtypes=[w.HANDLE]
class PROCESS(c.Structure):
 _fields_=[('dwSize',w.DWORD),('cntUsage',w.DWORD),('pid',w.DWORD),('heap',c.c_size_t),('module',w.DWORD),('threads',w.DWORD),('parent',w.DWORD),('priority',w.LONG),('flags',w.DWORD),('name',w.WCHAR*260)]
k.Process32FirstW.argtypes=[w.HANDLE,c.POINTER(PROCESS)];k.Process32NextW.argtypes=[w.HANDLE,c.POINTER(PROCESS)]

def descendants(pid):
 s=k.CreateToolhelp32Snapshot(2,0);r=PROCESS();r.dwSize=c.sizeof(r);pairs=[]
 try:
  more=k.Process32FirstW(s,c.byref(r))
  while more:
   pairs.append((r.pid,r.parent));more=k.Process32NextW(s,c.byref(r))
 finally:k.CloseHandle(s)
 found={pid}
 for _ in range(5):
  found.update(p for p,parent in pairs if parent in found)
 return found

def windows(pids,parent=None):
 out=[]
 @CB
 def visit(h,l):
  pid=w.DWORD();u.GetWindowThreadProcessId(h,c.byref(pid))
  if pid.value in pids and u.IsWindowVisible(h):
   text=c.create_unicode_buffer(512);cl=c.create_unicode_buffer(128);rect=w.RECT()
   u.GetWindowTextW(h,text,512);u.GetClassNameW(h,cl,128);u.GetWindowRect(h,c.byref(rect))
   out.append(dict(hwnd=int(h),pid=pid.value,title=text.value,cls=cl.value,x=rect.left,y=rect.top,w=rect.right-rect.left,h=rect.bottom-rect.top))
  return True
 if parent:u.EnumChildWindows(parent,visit,0)
 else:u.EnumWindows(visit,0)
 return out

def until(fn,seconds=30):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.12)
 raise RuntimeError('Timed out waiting for GUI test condition')

def click(win):
 # ttk tests pointer containment while processing a click. Send an actual
 # bounded mouse click to this test window rather than fabricated messages.
 point=w.POINT();u.GetCursorPos(c.byref(point))
 u.SetForegroundWindow(u.GetAncestor(win['hwnd'],2))
 u.SetCursorPos(win['x']+win['w']//2,win['y']+win['h']//2)
 time.sleep(.2)
 u.mouse_event(0x2,0,0,0,0)
 time.sleep(.15)
 u.mouse_event(0x4,0,0,0,0)
 time.sleep(.2)
 u.SetCursorPos(point.x,point.y)


def main():
 p=argparse.ArgumentParser();p.add_argument('--source-exe',type=Path,required=True);args=p.parse_args()
 source=args.source_exe.resolve();original=source.read_bytes()
 manifest=json.loads((PATCH/'patch.json').read_text(encoding='utf-8'))
 assert hashlib.sha256(original).hexdigest()==manifest['source_sha256']
 with tempfile.TemporaryDirectory(prefix='gui-test-',dir=PATCH.parent) as tmp:
  root=Path(tmp);(root/'data/graphic').mkdir(parents=True);(root/'data/saves/slot1').mkdir(parents=True)
  (root/'momo1_v151.exe').write_bytes(original)
  sentinel=root/'data/saves/slot1/user-save';sentinel.write_bytes(b'UNCHANGED-SAVE')
  env=os.environ.copy();env['PATH']=r'C:\Windows\System32;C:\Windows';env.pop('PYTHONHOME',None);env.pop('PYTHONPATH',None)
  proc=subprocess.Popen([str(EXE)],cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  target=None;pids={proc.pid};checks=[]
  try:
   def find_main():
    nonlocal pids
    pids=descendants(proc.pid)
    return next((v for v in windows(pids) if v['cls']=='TkTopLevel' and v['w']>500),None)
   target=until(find_main)
   checks.append('packaged-GUI-visible-with-no-Python-or-Git-PATH')
   controls=windows(pids,target['hwnd'])
   # Tcl/Tk presents ttk controls as native TkChild windows, not TButton.
   # Group identical button-sized widgets by row; the action row has four.
   groups={}
   for b in controls:
    if 70<=b['w']<=180 and 30<=b['h']<=60:
     groups.setdefault(b['y'],[]).append(b)
   action_rows=[bs for bs in groups.values() if len(bs)==4]
   assert len(action_rows)==1,repr(controls)
   actions=sorted(action_rows[0],key=lambda b:b['x'])
   install_button,check_button,remove_button,open_button=actions
   assert install_button['w']>70
   assert not (root/'momo1_v151_zh.exe').exists()
   click(install_button)
   patched=root/'momo1_v151_zh.exe'
   until(lambda:patched.exists() and (root/'data/graphic/momo1_zh_install.json').exists(),60)
   assert hashlib.sha256(patched.read_bytes()).hexdigest()==manifest['target_sha256']
   assert hashlib.sha256((root/'data/graphic/momo1_zh_text.png').read_bytes()).hexdigest()==manifest['atlas_sha256']
   checks.append('actual-one-click-install-button-generates-verified-EXE-and-atlas')
   dialog=until(lambda:next((v for v in windows(pids) if v['cls']=='#32770'),None))
   ok=next(v for v in windows(pids,dialog['hwnd']) if v['cls']=='Button')
   click(ok)
   checks.append('Chinese-success-dialog-shown')
   assert (root/'momo1_v151.exe').read_bytes()==original and sentinel.read_bytes()==b'UNCHANGED-SAVE'
   checks.append('GUI-install-preserves-original-and-existing-save')
   u.PostMessageW(target['hwnd'],0x10,0,0)
   proc.wait(timeout=15)
  finally:
   if target:u.PostMessageW(target['hwnd'],0x10,0,0)
   if proc.poll() is None:
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
     subprocess.run(['C:\\Windows\\System32\\taskkill.exe','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
     try:proc.wait(timeout=5)
     except Exception:pass
   # The one-file bootloader and unpacked child may close asynchronously.
   for pid in pids:
    if pid!=os.getpid():
     subprocess.run(['C:\\Windows\\System32\\taskkill.exe','/PID',str(pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
  report={'exe_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'checks':checks,'count':len(checks),
    'gui_button_test':True,'target_python_required':False,'original_unchanged':True,
    'scope':'real packaged GUI button on temporary game clone; no live user saves used'}
  (PATCH/'oneclick_gui_test_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  sys.stdout.reconfigure(encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
