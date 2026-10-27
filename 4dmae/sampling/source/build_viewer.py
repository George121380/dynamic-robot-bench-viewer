"""Build one offline HTML and portable, sanitized source metadata."""
import argparse
import base64
import json
import shutil
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--root',type=Path,required=True)
a=p.parse_args();root=a.root
data=json.loads((root/'public/samples.json').read_text())
for frame in data['frames']:
    path=root/'raw'/frame['image']
    frame['image_data']='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
    shutil.copy2(path,root/'public'/path.name)
template=(root/'scripts/viewer.template.html').read_text()
encoded=json.dumps(data,separators=(',',':')).replace('</','<\\/')
(root/'public/index.html').write_text(template.replace('__DATA__',encoded))
verification=json.loads((root/'qa/sampling-verification.json').read_text())
verification['scene_source']=json.loads((root/'raw/scene.json').read_text())
verification['feature_source']=json.loads((root/'qa/dino.json').read_text())
extra=root/'qa/causal-verification.json'
if extra.exists():verification['additional_checks']=json.loads(extra.read_text())
(root/'public/verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print('Built offline HTML:',(root/'public/index.html').stat().st_size,'bytes')
