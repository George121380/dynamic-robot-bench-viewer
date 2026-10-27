"""Build the source-grounded HPT inset; no model execution or external assets."""
from pathlib import Path
from html import escape
import subprocess

OUT = Path(__file__).resolve().parents[1]
INK, GRAY, BLUE, ORANGE, PURPLE = '#252525', '#666666', '#496fa4', '#ae7541', '#76618f'
parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc">
<title id="title">Inside the HPT trunk: observations and learned tokens</title>
<desc id="desc">The shown B5 configuration concatenates 48 observation tokens, 64 learned action tokens and 16 learned future tokens. Sixteen self-attention and MLP blocks produce separate action and trajectory contexts. The trajectory tokenizer encodes the noisy trajectory, while the HPT future context enters the decoder separately.</desc>
<defs>''']
for name, color in [('ink', INK), ('blue', BLUE), ('orange', ORANGE), ('purple', PURPLE)]:
    parts.append(f'<marker id="{name}" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="{color}"/></marker>')
parts += ['</defs><style>text{font-family:Arial,Helvetica,sans-serif}path,rect{vector-effect:non-scaling-stroke}</style><rect width="1600" height="900" fill="white"/>']

def text(x, y, label, size=21, color=INK, bold=False, anchor='start'):
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{600 if bold else 400}" text-anchor="{anchor}">{escape(label)}</text>')

def rect(x, y, w, h, color=INK, fill='white'):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" stroke="{color}" stroke-width="1.4" fill="{fill}"/>')

def line(points, color=INK, arrow=True, dash=False):
    name = {INK:'ink', BLUE:'blue', ORANGE:'orange', PURPLE:'purple'}.get(color,'ink')
    d = 'M' + ' L'.join(f'{x},{y}' for x,y in points)
    extra = f' marker-end="url(#{name})"' if arrow else ''
    if dash: extra += ' stroke-dasharray="5 5"'
    parts.append(f'<path d="{d}" stroke="{color}" stroke-width="1.5" fill="none"{extra}/>')

def box(x,y,w,h,title,subtitle='',color=INK,fill='white',size=21):
    rect(x,y,w,h,color,fill)
    text(x+w/2,y+h/2-(4 if subtitle else -7),title,size,color,True,'middle')
    if subtitle: text(x+w/2,y+h/2+23,subtitle,18,GRAY,anchor='middle')

text(40,48,'Inside HPT',31,bold=True)
text(1560,46,'B5 / PullCube · 128 tokens × 256 dimensions',19,GRAY,anchor='end')
text(40,84,'Heterogeneous Pretrained Transformer: modality-specific stems → shared transformer → task readouts',22,GRAY)

text(40,132,'Observation-dependent features',21,bold=True)
box(40,150,345,58,'RGB stem','16 × 256')
box(40,226,345,58,'State stem','16 × 256')
box(40,302,345,58,'History tokenizer + resampler','16 × 256 · B5 extension',PURPLE,size=19)

text(40,409,'Learned input tokens · EgoWAM',21,bold=True)
box(40,427,345,58,'64 action tokens','Learned parameter vectors',BLUE,'#edf2f9')
box(40,503,345,58,'16 future tokens','Learned parameter vectors',ORANGE,'#faf1e7')
for y in [179,255,331,456,532]: line([(385,y),(435,y)],arrow=False)
line([(435,179),(435,532)],arrow=False)
line([(435,355),(555,355)])
text(495,315,'Concat.',18,GRAY,anchor='middle')
text(495,339,'+ position',18,GRAY,anchor='middle')

rect(555,150,465,411)
text(787,191,'Shared transformer trunk',25,bold=True,anchor='middle')
text(787,223,'16 blocks · width 256 · 8 attention heads',19,GRAY,anchor='middle')
box(590,256,395,72,'LayerNorm → self-attention','Residual addition',size=21)
line([(787,328),(787,355)])
box(590,355,395,72,'LayerNorm → MLP','Residual addition',size=21)
text(787,470,'All token groups attend to each other.',20,anchor='middle')
text(787,503,'One forward pass per observation.',20,anchor='middle')
text(787,535,'No noisy trajectories or flow time τ here.',18,GRAY,anchor='middle')

text(1135,132,'Read out the corresponding positions',21,bold=True)
line([(1020,256),(1135,256)],BLUE)
box(1135,213,425,86,'64 action-context tokens','Condition the action flow head',BLUE,'#edf2f9')
line([(1020,405),(1135,405)],ORANGE)
box(1135,362,425,86,'16 future-context tokens','Condition the trajectory decoder',ORANGE,'#faf1e7')
text(1135,493,'Both outputs depend on this observation.',19)
text(1135,525,'Token counts are latent capacity;',19,GRAY)
text(1135,551,'they do not count predicted time steps.',19,GRAY)

line([(40,602),(1560,602)],'#d4d4d4',arrow=False)
text(40,644,'Two separate inputs to the trajectory decoder',24,bold=True)
text(1560,644,'HPT context is fixed during 50 generation steps',18,GRAY,anchor='end')
box(40,687,325,72,'16 future-context tokens','From HPT',ORANGE,'#faf1e7')
line([(365,723),(1060,723)],ORANGE)
text(680,710,'Condition via cross-attention',20,ORANGE,anchor='middle')

box(400,802,350,58,'Noisy displacements + anchors','+ observed / noisy slot flags',PURPLE,size=18)
line([(750,831),(790,831)],PURPLE)
box(790,802,180,58,'Tokenizer Tθ','One token per point',PURPLE,size=20)
line([(970,831),(1008,831),(1008,755),(1060,755)],PURPLE)

box(1060,687,280,100,'Trajectory decoder','Predict a velocity field',ORANGE,'#faf1e7')
text(1200,839,'Flow time τ',20,GRAY,anchor='middle')
line([(1200,817),(1200,787)],ORANGE)
line([(1340,737),(1380,737)],ORANGE)
text(1400,729,'Update',23,ORANGE,bold=True)
text(1400,760,'the trajectory',20,ORANGE)
text(40,886,'The 16 HPT context tokens bypass Tθ. The decoder combines context with the evolving trajectory.',18,GRAY)
parts.append('</svg>')
svg = OUT/'hpt-internals.svg'
svg.write_text('\n'.join(parts))
for ext, options in [('png',['--export-width=3200']),('pdf',[])]:
    subprocess.run(['inkscape',str(svg),f'--export-filename={OUT / ("hpt-internals."+ext)}',*options],check=True)
print('Built HPT SVG, PNG and vector PDF.')
