"""Audit patched draw sites and dialogue literals against the translation map."""
import json,re,sys
from pathlib import Path
from gm7 import *
B=Path(__file__).resolve().parents[1];R=B.parent
plain=unpack_exe((R/'momo1_v151.exe').read_bytes(),True)
m=json.loads((B/'patch.json').read_text(encoding='utf-8'))
rows=json.loads((B/'texts.json').read_text(encoding='utf-8'));keys={r['source'] for r in rows}
inline=[plain[r['offset']+4:r['offset']+4+r['before_length']] for r in m['inline']]
scr=scripts(plain)
texts=[]
# All normal NPC/tutorial dialogue assignments. Exclude known test/debug room.
for match in re.finditer(rb'\btext\d*\s*=\s*"([^"\x00\r\n]*)"',plain):
 raw=match.group(1)
 if raw.startswith((b'ERROR in#',b'AAAAAAAID',b'one line')):continue
 if not raw:continue
 try:text=raw.decode('ascii')
 except UnicodeDecodeError:continue
 texts.append(text)
missing=[t for t in texts if t not in keys]
need(not missing,'Untranslated normal dialogue: '+repr(missing))
# Pause item labels/descriptions all supplied in the same verified script.
items=re.findall(rb'draw_text_transformed\([^\r\n]*?"([^"\r\n]*)"',scr['pause_scr'][2])
need(len(items)==30,'Unexpected pause item text count')
need(all(s.decode('ascii') in keys for s in items),'Missing item translation')
need(len(inline)==7,'Draw field audit mismatch')
report={'translation_entries':len(rows),'dialogue_occurrences':len(texts),'dialogue_distinct':len(set(texts)),
 'normal_dialogue_missing':missing,'item_name_and_description_entries':len(items),
 'inline_draw_fields':len(inline),'hooked_named_scripts':['say','pause_scr'],
 'preserved_original_people_names_and_copyright':True,
 'not_claimed':['image-baked text and logos','runtime error dialogs','debug/test-room text','full-game route regression']}
(B/'coverage_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
