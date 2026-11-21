"""Build source-only patch assets. Requires Pillow only at build time."""
import json, math, re, struct, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from gm7 import *

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parent
SOURCE=ROOT/'momo1_v151.exe'
INLINE={
 204105:(2762,'e77e2bf05e66d3ab4770b047f96b86c49a794ae4bac388ec0c66c381501285fd'),
 222760:(493,'1c5a5eda6be331be81e22df5c26f7c7768b98397ded334a15f48e76d3736bf83'),
 226513:(77,'f8b50abbf0c22e6cebb5ae9e54efb7279b3b9a48fd32f5109248ca018fe15d35'),
 230063:(900,'14a3d26aa1eb9b049b0c711f743d90e4cb2720e045a653b80cd0121e84dac5f8'),
 236732:(221,'0547a09918f454f530f411e6d6e1e52590c81663448623604efb3d107f0154e3'),
 271151:(5046,'ccf33938532753fa272654fa9dc9df08646cc9a01bfe900945a6775ff7221dd6'),
 276874:(146,'3c6e0cdacc90caa84075ee9b2e676a0356c674ddee622f429ff807f30f08371e')
}
REPLACEMENTS={
 'draw_text':'zh_draw_text',
 'draw_text_color':'zh_draw_text_color',
 'draw_text_transformed':'zh_draw_text_transformed',
 'draw_text_transformed_color':'zh_draw_text_transformed_color'
}
CALL=re.compile(rb'\b(draw_text(?:_transformed_color|_transformed|_color)?)\s*(?=\()')


def quoted(text):
    need(all(32<=ord(c)<=126 and c not in '\\"' for c in text),'Unexpected GML literal')
    return '"'+text+'"'


def hook(code):
    return CALL.sub(lambda m:REPLACEMENTS[m.group(1).decode()].encode(),code)


def prepare_atlas(rows):
    fontpath='C:/Windows/Fonts/simhei.ttf'
    atlas=Image.new('RGB',(512,2048),(0,0,0))
    tiles=[]; x=y=2; rowh=0
    previews=[]
    for row in rows:
        font=ImageFont.truetype(fontpath,row.get('font',12))
        lines=row['target'].split('#')
        w=max(1,math.ceil(max(font.getlength(t) for t in lines)))
        h=len(lines)*13
        need(w<=row['width'], 'Translation too wide: '+row['source'])
        tile=Image.new('L',(w,h),0); draw=ImageDraw.Draw(tile)
        for j,line in enumerate(lines):
            # Baseline fixed to the same 13 px cadence as the original font.
            draw.text((0,j*13),line,font=font,fill=255,anchor='lt',stroke_width=0)
        tile=tile.point(lambda v:255 if v>=100 else 0)
        need(tile.getbbox() is not None,'Empty translation bitmap')
        rgba=Image.new('RGBA',tile.size,(255,255,255,255)); rgba.putalpha(tile)
        if x+w+2>512: x=2; y+=rowh+2; rowh=0
        need(y+h+2<=2048,'Atlas exceeds budget')
        atlas.paste(rgba,(x,y),rgba)
        tiles.append(dict(row,x=x,y=y,w=w,h=h))
        previews.append((row,rgba))
        x+=w+2; rowh=max(rowh,h)
    used=y+rowh+2
    height=2**math.ceil(math.log2(used))
    atlas=atlas.crop((0,0,512,height))
    path=BASE/'assets'/'momo1_zh_text.png'
    atlas.save(path,optimize=True)
    # Contact sheet is a build preview, never read by the game.
    ph=sum(max(34,t.height+8) for _,t in previews)
    sheet=Image.new('RGB',(640,ph),(25,30,42)); d=ImageDraw.Draw(sheet)
    small=ImageFont.truetype(fontpath,11); yy=0
    for idx,(row,tile) in enumerate(previews):
        d.text((3,yy+2),f'{idx+1:02d}',font=small,fill=(130,200,240))
        sheet.paste(tile,(30,yy+3),tile)
        yy+=max(34,tile.height+8)
    sheet.save(BASE/'assets'/'translation_preview.png')
    return tiles,(512,height)


def helper_scripts(tiles):
    lines=['''// Chinese image-atlas renderer. Original texts remain untouched.
var zz_x,zz_y,zz_t,zz_sx,zz_sy,zz_c,zz_a,zz_l,zz_top,zz_w,zz_h,zz_dynamic,zz_suffix;
zz_x=argument0; zz_y=argument1; zz_t=string(argument2);
zz_sx=argument3; zz_sy=argument4; zz_c=argument5; zz_a=argument6;
zz_l=-1; zz_top=0; zz_w=0; zz_h=0; zz_dynamic=false;
''']
    for t in tiles:
        if t.get('dynamic'):
            prefix=t['source']
            cond='string_pos('+quoted(prefix)+',zz_t)=1'
        else: cond='zz_t='+quoted(t['source'])
        lines.append('if ('+cond+') {zz_l=%d; zz_top=%d; zz_w=%d; zz_h=%d; %s}\n'%(
            t['x'],t['y'],t['w'],t['h'],'zz_dynamic=true;' if t.get('dynamic') else ''))
    lines.append('''if (zz_l<0) return false;
if (!variable_global_exists("zh_atlas")) {
 global.zh_atlas=-1;
 if (file_exists(working_directory+"/data/graphic/momo1_zh_text.png")) {
  global.zh_atlas=background_add(working_directory+"/data/graphic/momo1_zh_text.png",true,false,true);
 }
}
if (global.zh_atlas<0) return false;
draw_background_part_ext(global.zh_atlas,zz_l,zz_top,zz_w,zz_h,zz_x,zz_y,zz_sx,zz_sy,zz_c,zz_a);
''')
    dyn=next(t for t in tiles if t.get('dynamic'))
    lines.append('''if (zz_dynamic) {
 zz_suffix=string_copy(zz_t,%d,string_length(zz_t)-%d);
 draw_text_transformed(zz_x+%d*zz_sx,zz_y+26*zz_sy,zz_suffix,zz_sx,zz_sy,0);
}
return true;
'''%(len(dyn['source'])+1,len(dyn['source'])+1,dyn['w']))
    helpers={'zh_render':''.join(lines)}
    helpers['zh_draw_text']='''if (!zh_render(argument0,argument1,argument2,1,1,draw_get_color(),draw_get_alpha())) {
 draw_text(argument0,argument1,argument2);
}
'''
    helpers['zh_draw_text_color']='''if (argument3!=argument4 || argument3!=argument5 || argument3!=argument6) {
 draw_text_color(argument0,argument1,argument2,argument3,argument4,argument5,argument6,argument7);
} else {
 if (!zh_render(argument0,argument1,argument2,1,1,argument3,argument7)) {
  draw_text_color(argument0,argument1,argument2,argument3,argument4,argument5,argument6,argument7);
 }
}
'''
    helpers['zh_draw_text_transformed']='''if (argument5!=0) {
 draw_text_transformed(argument0,argument1,argument2,argument3,argument4,argument5);
} else {
 if (!zh_render(argument0,argument1,argument2,argument3,argument4,draw_get_color(),draw_get_alpha())) {
  draw_text_transformed(argument0,argument1,argument2,argument3,argument4,argument5);
 }
}
'''
    helpers['zh_draw_text_transformed_color']='''if (argument5!=0 || argument6!=argument7 || argument6!=argument8 || argument6!=argument9) {
 draw_text_transformed_color(argument0,argument1,argument2,argument3,argument4,argument5,argument6,argument7,argument8,argument9,argument10);
} else {
 if (!zh_render(argument0,argument1,argument2,argument3,argument4,argument6,argument10)) {
  draw_text_transformed_color(argument0,argument1,argument2,argument3,argument4,argument5,argument6,argument7,argument8,argument9,argument10);
 }
}
'''
    return {n:c.replace('\n','\r\n').encode('ascii') for n,c in helpers.items()}


def script_table(plain,helpers):
    old=scripts(plain)
    pending=list(helpers.items())
    out=bytearray(plain[SCRIPTS:SCRIPTS+8]); p=SCRIPTS+8
    assigned=[]
    for slot in range(129):
        begin=p; flag=u32(plain,p); p+=4
        if flag:
            n=u32(plain,p); name=plain[p+4:p+4+n].decode('ascii'); p+=4+n
            need(u32(plain,p)==400,'Unexpected script version'); p+=4
            end=p+4+u32(plain,p)
            code=old[name][2]
            if name in ('say','pause_scr'):
                new=hook(code)
                need(new!=code,'Missing draw hook in '+name)
                out.extend(plain[begin:p]); out.extend(script_record(new))
            else: out.extend(plain[begin:end])
            p=end
        elif pending:
            name,code=pending.pop(0)
            out.extend(pack(1)+field(name.encode('ascii'))+pack(400)+script_record(code))
            assigned.append({'slot':slot,'name':name,'code_sha256':digest(code)})
        else: out.extend(pack(0))
    need(p==FONT and not pending,'Script slot allocation failed')
    return bytes(out),assigned


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows=json.loads((BASE/'texts.json').read_text(encoding='utf-8'))
    need(len({r['source'] for r in rows})==len(rows),'Duplicate translation key')
    exe=SOURCE.read_bytes(); plain=unpack_exe(exe,True)
    need(repack_exe(exe,plain)==exe,'No-op roundtrip failed')
    tiles,atlas_size=prepare_atlas(rows)
    helpers=helper_scripts(tiles)
    table,assigned=script_table(plain,helpers)
    edits=[(SCRIPTS,FONT,table)]
    audit=[]
    for p,(n,sha) in INLINE.items():
        need(u32(plain,p)==n,'Unexpected GML length')
        code=plain[p+4:p+4+n]
        need(digest(code)==sha,'Unexpected GML source')
        new=hook(code); need(new!=code,'No replacement')
        edits.append((p,p+4+n,field(new)))
        audit.append({'offset':p,'before_sha256':digest(code),'before_length':n,'after_length':len(new)})
    newplain=apply_edits(plain,edits)
    patched=repack_exe(exe,newplain)
    need(unpack_exe(patched)==newplain,'Patched EXE readback failed')
    need(patched[:OFFSET]==exe[:OFFSET],'Engine prefix was changed')
    # Store only original source hashes and the new source/translation code, not game data.
    manifest={'format':'momo1-151-zh-source-patch-v1','version':'0.1-test',
      'source_sha256':ORIGINAL,'target_sha256':digest(patched),
      'source_length':len(exe),'target_length':len(patched),
      'atlas_sha256':digest((BASE/'assets'/'momo1_zh_text.png').read_bytes()),
      'atlas_size':atlas_size,'translation_count':len(rows),'allocated_scripts':assigned,
      'inline':audit,'script_table_sha256':digest(plain[SCRIPTS:FONT]),
      'helpers':{n:c.decode('ascii') for n,c in helpers.items()},
      'original_script_sha256':{n:digest(scripts(plain)[n][2]) for n in ('say','pause_scr')}}
    (BASE/'patch.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (BASE/'assets'/'atlas_layout.json').write_text(json.dumps(tiles,ensure_ascii=False,indent=2),encoding='utf-8')
    # Only local build output; this executable must not be redistributed with the patch.
    out=ROOT/'momo1_v151_zh.exe'
    need(not out.exists(),'Refusing to overwrite existing localized executable')
    with out.open('xb') as f: f.write(patched)
    report={'original_unchanged':digest(SOURCE.read_bytes())==ORIGINAL,
      'source_round_trip':True,'patched_readback':True,'engine_prefix_unchanged':True,
      'translations':len(rows),'atlas_size':atlas_size,'inline_hooks':len(audit),
      'localized_exe_sha256':digest(patched),'localized_exe_size':len(patched),
      'runtime_tested':False}
    (BASE/'build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
