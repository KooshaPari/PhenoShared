"""Read original resume files; write additive evidence artifacts only."""
from pathlib import Path
import hashlib,json,subprocess,zipfile,xml.etree.ElementTree as ET
base=Path(__file__).parent
root=Path('/Users/kooshapari/Downloads')
files=sorted(p for p in root.iterdir() if p.is_file() and p.suffix.lower() in ('.docx','.pdf') and ('Koosha' in p.name or p.name.startswith(('Eng Resume','MGMTProduct Resume'))))
out=base/'extracted'; out.mkdir(exist_ok=True)
manifest=[]
for i,p in enumerate(files,1):
    key=f'S{i:03d}'
    if p.suffix.lower()=='.docx':
        with zipfile.ZipFile(p) as z:
            xml=ET.fromstring(z.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        text='\n'.join(''.join(t.text or '' for t in paragraph.findall('.//w:t',ns)) for paragraph in xml.findall('.//w:p',ns))
    else:
        text=subprocess.check_output(['pdftotext','-layout',str(p),'-'],text=True)
    extracted=out/(key+'.txt'); extracted.write_text(text)
    manifest.append({'id':key,'path':str(p),'format':p.suffix[1:],'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'normalized_text_sha256':hashlib.sha256(' '.join(text.split()).encode()).hexdigest(),'extracted':str(extracted.relative_to(base))})
(base/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
groups={}
for m in manifest: groups.setdefault(m['normalized_text_sha256'],[]).append(m['id'])
(base/'duplicate-groups.json').write_text(json.dumps([g for g in groups.values() if len(g)>1],indent=2)+'\n')
print('\n'.join(f"{m['id']} {Path(m['path']).name}" for m in manifest))
