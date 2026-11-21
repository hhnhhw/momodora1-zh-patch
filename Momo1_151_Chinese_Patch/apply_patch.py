"""Install/remove the Momodora 1.51 Chinese source patch. Python 3 stdlib only."""
import argparse
import json
import re
import shutil
import sys
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'tools'))
from gm7 import (ORIGINAL,OFFSET,SCRIPTS,FONT,apply_edits,digest,field,inflate,need,pack,
                repack_exe,script_record,scripts,u32,unpack_exe)

BASE=Path(__file__).resolve().parent
MANIFEST=BASE/'patch.json'
OUTPUT='momo1_v151_zh.exe'
ATLAS='momo1_zh_text.png'
CALL=re.compile(rb'\b(draw_text(?:_transformed_color|_transformed|_color)?)\s*(?=\()')


def hook(code):
    return CALL.sub(lambda m:b'zh_'+m.group(1),code)


def make_patched(exe,manifest):
    plain=unpack_exe(exe,original=True)
    need(digest(plain[SCRIPTS:FONT])==manifest['script_table_sha256'],'Unexpected script table')
    old=scripts(plain)
    helpers={row['slot']:(row['name'],manifest['helpers'][row['name']].encode('ascii'))
             for row in manifest['allocated_scripts']}
    need(len(helpers)==5,'Invalid helper script manifest')
    for row in manifest['allocated_scripts']:
        name,code=helpers[row['slot']]
        need(digest(code)==row['code_sha256'],'Helper script checksum mismatch')
    table=bytearray(plain[SCRIPTS:SCRIPTS+8]); p=SCRIPTS+8
    for slot in range(129):
        start=p; flag=u32(plain,p); p+=4
        if flag:
            need(slot not in helpers,'Refusing to replace an existing script')
            n=u32(plain,p); name=plain[p+4:p+4+n].decode('ascii'); p+=4+n
            need(u32(plain,p)==400,'Invalid script version'); p+=4
            end=p+4+u32(plain,p)
            if name in manifest['original_script_sha256']:
                code=old[name][2]
                need(digest(code)==manifest['original_script_sha256'][name],'Unexpected source script: '+name)
                new=hook(code)
                need(new!=code,'Missing text hooks: '+name)
                table.extend(plain[start:p]); table.extend(script_record(new))
            else:
                table.extend(plain[start:end])
            p=end
        elif slot in helpers:
            name,code=helpers[slot]
            table.extend(pack(1)+field(name.encode('ascii'))+pack(400)+script_record(code))
        else:
            table.extend(pack(0))
    need(p==FONT,'Invalid table boundary')
    edits=[(SCRIPTS,FONT,bytes(table))]
    for row in manifest['inline']:
        p=row['offset']; n=row['before_length']
        need(u32(plain,p)==n,'Unexpected source length')
        code=plain[p+4:p+4+n]
        need(digest(code)==row['before_sha256'],'Unexpected inline source')
        new=hook(code)
        need(len(new)==row['after_length'],'Unexpected replacement length')
        edits.append((p,p+4+n,field(new)))
    newplain=apply_edits(plain,edits)
    result=repack_exe(exe,newplain)
    need(result[:OFFSET]==exe[:OFFSET],'Engine prefix changed')
    need(unpack_exe(result)==newplain,'Patched output readback mismatch')
    # The target hash is zlib-version dependent. If compression differs, resource
    # identity and readback are still checked rather than claiming a matching hash.
    return result,digest(newplain)


def main():
    parser=argparse.ArgumentParser(description='Momodora 1.51 Chinese patch installer')
    parser.add_argument('--game-dir',type=Path,default=BASE.parent)
    parser.add_argument('--check',action='store_true',help='Validate without writing')
    parser.add_argument('--remove',action='store_true',help='Remove only installed patch files')
    parser.add_argument('--test-output',type=Path,help='Create a test EXE outside the original path (no installation)')
    args=parser.parse_args()
    need(not (args.remove and (args.check or args.test_output)),'Conflicting options')
    root=args.game_dir.resolve()
    original=root/'momo1_v151.exe'
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    need(manifest['format']=='momo1-151-zh-source-patch-v1','Invalid patch format')
    need(manifest['source_sha256']==ORIGINAL,'Invalid supported source hash')
    need(original.is_file(),'Original momo1_v151.exe not found')
    exe=original.read_bytes()
    need(digest(exe)==ORIGINAL,'Unsupported/modified original EXE. Original was not changed.')
    atlas=BASE/'assets'/ATLAS
    need(atlas.is_file() and digest(atlas.read_bytes())==manifest['atlas_sha256'],'Atlas checksum mismatch')
    out=root/OUTPUT; target_atlas=root/'data'/'graphic'/ATLAS
    receipt=root/'data'/'graphic'/'momo1_zh_install.json'
    if args.remove:
        need(receipt.exists(),'No install receipt. No files removed.')
        rec=json.loads(receipt.read_text(encoding='utf-8'))
        need(rec.get('patch_format')==manifest['format'],'Invalid installation receipt')
        if out.exists(): need(digest(out.read_bytes())==rec['exe_sha256'],'Localized EXE modified; not removing it')
        if target_atlas.exists(): need(digest(target_atlas.read_bytes())==rec['atlas_sha256'],'Atlas modified; not removing it')
        for p in (out,target_atlas,receipt):
            if p.exists():p.unlink()
        print('Removed localized EXE and patch atlas. Original game and saves unchanged.')
        return
    result,plain_sha=make_patched(exe,manifest)
    need(digest(exe)==digest(original.read_bytes()),'Original changed during build')
    status={'source_sha256':ORIGINAL,'output_sha256':digest(result),'output_length':len(result),
      'decoded_payload_sha256':plain_sha,'target_matches_build':digest(result)==manifest['target_sha256'],
      'readback_verified':True,'original_unchanged':True,'mode':'check' if args.check else 'install'}
    if not args.check:
        if args.test_output:
            output=args.test_output.resolve()
            need(output!=original and not output.exists(),'Refusing to overwrite test output')
            with output.open('xb') as f:f.write(result)
            status['mode']='test-output'; status['output']=str(output)
        else:
            # Refuse to overwrite unknown files. Existing identical installation
            # is idempotent and may be adopted after a local development build.
            if out.exists():need(digest(out.read_bytes())==digest(result),'Existing localized EXE differs; move it first')
            if target_atlas.exists():need(digest(target_atlas.read_bytes())==manifest['atlas_sha256'],'Existing atlas differs; move it first')
            need(target_atlas.parent.is_dir(),'Original data/graphic directory missing')
            if receipt.exists():
                oldreceipt=json.loads(receipt.read_text(encoding='utf-8'))
                need(oldreceipt.get('exe_sha256')==digest(result),'Existing install receipt differs')
            if not target_atlas.exists():
                with target_atlas.open('xb') as f:f.write(atlas.read_bytes())
            if not out.exists():
                with out.open('xb') as f:f.write(result)
            record={'patch_format':manifest['format'],'version':manifest['version'],
              'exe_sha256':digest(result),'atlas_sha256':manifest['atlas_sha256']}
            receipt.write_text(json.dumps(record,indent=2),encoding='utf-8')
            status['output']=str(out)
    print(json.dumps(status,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,zlib.error) as err:
        print('ERROR: '+str(err),file=sys.stderr)
        sys.exit(1)
