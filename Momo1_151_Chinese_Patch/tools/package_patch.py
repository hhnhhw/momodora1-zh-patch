"""Create the standalone one-click release ZIP without any original game files."""
import hashlib
import json
import zipfile
from pathlib import Path

PATCH = Path(__file__).resolve().parents[1]
REPO = PATCH.parent
OUT = REPO / 'dist'
OUT.mkdir(exist_ok=True)
ARCHIVE = OUT / 'Momodora1ZH_OneClick_v0.1.0_win64.zip'
REPORT = json.loads((PATCH/'oneclick_build_report.json').read_text(encoding='utf-8-sig'))
EXE = PATCH / REPORT['file']
assert hashlib.sha256(EXE.read_bytes()).hexdigest() == REPORT['sha256']
FILES = [
    (EXE, 'Momodora1ZH_Setup.exe'),
    (PATCH/'Momodora1ZH_Setup.exe.sha256', 'Momodora1ZH_Setup.exe.sha256'),
    (REPO/'Momodora1ZH_Setup_README.txt', '使用说明.txt'),
    (REPO/'NOTICE.md', 'NOTICE.md'),
]
FILES.extend((p, 'Licenses/'+p.name) for p in sorted((PATCH/'Licenses').iterdir()) if p.is_file())
assert not ARCHIVE.exists(), 'Refusing to replace existing ZIP: '+str(ARCHIVE)
with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
    for source, name in FILES:
        assert source.is_file(), str(source)
        bundle.write(source, name)
with zipfile.ZipFile(ARCHIVE) as bundle:
    assert bundle.testzip() is None
    assert set(bundle.namelist()) == {name for _,name in FILES}
    assert bundle.read('Momodora1ZH_Setup.exe') == EXE.read_bytes()
    forbidden = ('.dll','.gml','.bin','.ogg','.wav','.mp3','.ttf','.ttc','.otf','.bak','.pem','.key')
    assert not any(n.lower().endswith(forbidden) for n in bundle.namelist())
    assert [n for n in bundle.namelist() if n.lower().endswith('.exe')] == ['Momodora1ZH_Setup.exe']
result = {
    'archive': ARCHIVE.name,
    'size_bytes': ARCHIVE.stat().st_size,
    'sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
    'installer_sha256': REPORT['sha256'],
    'entries': len(FILES),
    'zip_crc_verified': True,
    'original_game_files_excluded': True,
}
(PATCH/'oneclick_package_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
