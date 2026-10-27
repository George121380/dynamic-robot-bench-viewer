"""Editable, source-grounded B5 figures. All line drawings are schematic."""
from pathlib import Path
from html import escape
import base64
import json
import math
import subprocess

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
OUT.mkdir(exist_ok=True)
INK = '#252525'
GRAY = '#666666'
LINE = '#a8a8a8'
BLUE = '#496fa4'
BLUE_LIGHT = '#edf2f9'
ORANGE = '#ae7541'
ORANGE_LIGHT = '#faf1e7'
PURPLE = '#76618f'
SHA = 'cf880fa7882665aad0d66c86adb1b45d6f14327c'
BASE = f'https://github.com/George121380/4dmae/blob/{SHA}/'

class Figure:
    def __init__(self, title, description, w=1600, h=900):
        self.p = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">',
                  f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
                  '<defs>']
        for name, color in [('ink', INK), ('blue', BLUE), ('orange', ORANGE), ('purple', PURPLE)]:
            self.p.append(f'<marker id="{name}" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="{color}"/></marker>')
        self.p += ['</defs>', '<style>text{font-family:Arial,Helvetica,sans-serif} path,line,rect,circle{vector-effect:non-scaling-stroke}</style>',f'<rect width="{w}" height="{h}" fill="white"/>']
    def text(self,x,y,t,size=21,color=INK,bold=False,anchor='start',serif=False):
        family=' font-family="Georgia,serif" font-style="italic"' if serif else ''
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{600 if bold else 400}" text-anchor="{anchor}"{family}>{escape(t)}</text>')
    def rect(self,x,y,w,h,fill='white',stroke=INK,sw=1.5,rx=0):
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>')
    def line(self,pts,color=INK,sw=1.5,arrow=False,dash=False):
        d='M'+' L'.join(f'{x},{y}' for x,y in pts)
        name={INK:'ink',BLUE:'blue',ORANGE:'orange',PURPLE:'purple'}.get(color,'ink')
        extra=f' marker-end="url(#{name})"' if arrow else ''
        if dash: extra+=' stroke-dasharray="5 5"'
        self.p.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{extra}/>')
    def circle(self,x,y,r,fill='white',stroke=INK,sw=1.5):
        self.p.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    def box(self,x,y,w,h,title,subtitle='',color=INK,fill='white',size=21):
        self.rect(x,y,w,h,fill,color)
        self.text(x+w/2,y+(h/2-3 if subtitle else h/2+7),title,size,color,True,'middle')
        if subtitle:self.text(x+w/2,y+h/2+25,subtitle,17,GRAY,False,'middle')
    def tokens(self,x,y,n=6,color=GRAY,fill='#f2f2f2',w=12,h=30,gap=5):
        for i in range(n):self.rect(x+i*(w+gap),y,w,h,fill,color,1)
    def tracks(self,x,y,w=130,h=85,color=BLUE,n=4,dashed=False):
        for i in range(n):
            pts=[]
            for j in range(22):
                t=j/21
                pts.append((x+w*t,y+h*(.12+i*.23)+math.sin(t*math.pi*(.7+i*.15))*h*(.12 if i%2 else -.13)))
            self.line(pts,color,1.8,dash=dashed)
            self.circle(*pts[-1],3,color,color,1)
    def save(self,name):
        (OUT/f'{name}.svg').write_text('\n'.join(self.p+['</svg>']))


def overview():
    f=Figure('4D MAE / B5: policy and trajectory completion',
        'PullCube configuration. RGB, state, and observed point history condition a shared HPT. '
        'The physical Q anchor enters the trajectory tokenizer with noisy tracks and slot flags. Its point token queries the HPT future context inside decoder cross-attention. The trajectory tokenizer '
        'is shared across observation encoding and decoder inputs. Only the action branch is used for control.')
    f.text(40,48,'4D MAE / B5',31,bold=True)
    f.text(1560,46,'PullCube configuration',19,GRAY,anchor='end')
    f.text(40,98,'(a) Policy architecture',23,bold=True)

    # Actual simulator frame, shown only as an example observation.
    frame=HERE/'pullcube-rgb.png'
    if frame.exists():
        data=base64.b64encode(frame.read_bytes()).decode()
        f.p.append(f'<image x="42" y="133" width="118" height="118" xlink:href="data:image/png;base64,{data}"/>')
    else:f.rect(42,133,118,118,'#f4f4f4',LINE)
    f.text(101,276,'Current RGB',19,anchor='middle')
    f.line([(170,193),(215,193)],arrow=True)
    f.box(215,153,230,80,'ResNet18','RGB stem + resampler')
    f.line([(445,193),(475,193)],arrow=True)
    f.tokens(482,178)
    f.text(531,224,'16 tokens',16,GRAY,anchor='middle')

    for i,v in enumerate([.62,.33,.8,.52,.9,.2,.4,.66,.3]):
        f.rect(44+i*13,346-v*38,8,v*38,'#b9b9b9','none')
    f.line([(40,347),(162,347)],LINE,1)
    f.text(101,375,'Robot state',19,anchor='middle')
    f.line([(170,329),(215,329)],arrow=True)
    f.box(215,289,230,80,'State MLP','+ resampler')
    f.line([(445,329),(475,329)],arrow=True)
    f.tokens(482,314)
    f.text(531,360,'16 tokens',16,GRAY,anchor='middle')

    f.tracks(42,428,118,65)
    f.text(101,521,'Point history C',19,anchor='middle')
    f.line([(170,465),(215,465)],arrow=True)
    f.box(215,425,230,80,'Tokenizer Tθ','+ point resampler',PURPLE)
    f.line([(445,465),(475,465)],arrow=True)
    f.tokens(482,450,color=PURPLE,fill='#f3f0f7')
    f.text(531,496,'16 tokens',16,GRAY,anchor='middle')

    # Concatenation of learned queries and the three observation modalities.
    f.line([(588,193),(614,193),(614,465),(588,465)],GRAY,1.5)
    f.line([(588,329),(652,329)],arrow=True)
    f.text(751,138,'Learned queries',20,bold=True,anchor='middle')
    f.text(751,166,'64 action + 16 future',18,GRAY,anchor='middle')
    f.line([(751,178),(751,223)],arrow=True)
    f.rect(652,223,198,214,'#f5f5f5',INK,1.7)
    f.text(751,279,'HPT',30,bold=True,anchor='middle')
    f.text(751,314,'128 × 256',22,anchor='middle')
    f.text(751,350,'16 blocks',19,GRAY,anchor='middle')
    f.text(751,378,'8 heads',19,GRAY,anchor='middle')
    f.text(751,464,'Concat. + position',17,GRAY,anchor='middle')

    # Independent output branches: no trajectory-to-action edge.
    f.line([(850,278),(890,278),(890,206),(1064,206)],BLUE,arrow=True)
    f.tokens(924,177,4,BLUE,BLUE_LIGHT)
    f.text(954,245,'64 action',18,BLUE,anchor='middle')
    f.text(1187,133,'Noisy actions + τ',18,GRAY,anchor='middle')
    f.line([(1187,144),(1187,165)],BLUE,arrow=True)
    f.box(1064,165,246,82,'Action flow head','6 blocks · width 128',BLUE,BLUE_LIGHT)
    f.line([(1310,206),(1354,206)],BLUE,arrow=True)
    f.tracks(1372,164,163,68,BLUE,3)
    f.text(1452,269,'Action chunk',21,BLUE,True,'middle')
    f.text(1452,297,'32 × 8',19,GRAY,anchor='middle')
    f.text(1452,325,'Execute 8; replan',17,GRAY,anchor='middle')

    # Show the Q call explicitly: anchor/noisy-track tokens query HPT context.
    f.line([(850,380),(880,380),(880,405),(1280,405),(1280,445)],ORANGE,arrow=True)
    f.tokens(924,375,4,ORANGE,ORANGE_LIGHT)
    f.text(1077,432,'16 future-context tokens (K, V)',18,ORANGE,anchor='middle')

    f.box(895,445,120,75,'Point query Q','Current XYZ',PURPLE,size=17)
    f.line([(1015,482),(1045,482)],PURPLE,arrow=True)
    f.box(1045,445,100,75,'Tθ','Point token',PURPLE,size=25)
    f.line([(1145,482),(1175,482)],PURPLE,arrow=True)
    f.text(1160,468,'q',19,PURPLE,True,'middle')
    f.text(966,559,'Noisy tracks + flags',17,GRAY,anchor='middle')
    f.line([(1055,550),(1095,520)],PURPLE,arrow=True)
    f.box(1175,445,210,75,'Trajectory decoder','q attends to K, V',ORANGE,ORANGE_LIGHT,20)
    f.text(1280,568,'Flow time τ',18,GRAY,anchor='middle')
    f.line([(1280,548),(1280,520)],ORANGE,arrow=True)
    f.line([(1385,482),(1410,482)],ORANGE,arrow=True)
    f.tracks(1420,446,125,65,ORANGE,4)
    f.text(1482,546,'Q completion',20,ORANGE,True,'middle')
    f.text(1482,572,'50 flow steps',16,GRAY,anchor='middle')
    f.text(1482,598,'15 past + 15 future',17,GRAY,anchor='middle')

    f.line([(330,505),(330,592),(1160,592),(1160,505),(1145,505)],PURPLE,1.3,dash=True)
    f.rect(647,576,235,32,'white','none')
    f.text(764,598,'Tθ: shared weights',18,PURPLE,anchor='middle')
    f.text(40,615,'Control uses the action branch. Trajectory completion supplies auxiliary training supervision.',18,GRAY)
    f.line([(40,640),(1560,640)],'#d4d4d4',1)

    f.text(40,683,'(b) Trajectory supervision',23,bold=True)
    f.text(312,721,'Past',18,GRAY,anchor='middle')
    f.text(568,721,'Now',18,GRAY,anchor='middle')
    f.text(821,721,'Future',18,GRAY,anchor='middle')
    for y,label,known in [(747,'C  Observed points',True),(790,'Q  Query points',False)]:
        f.text(40,y+19,label,19)
        for j in range(15):
            f.rect(226+j*21,y,16,24,BLUE_LIGHT if known else ORANGE_LIGHT,BLUE if known else ORANGE,1)
            f.rect(597+j*21,y,16,24,ORANGE_LIGHT,ORANGE,1)
        f.circle(568,y+12,7,INK,INK,1)
    f.text(226,846,'Observed / clamped',17,BLUE)
    f.text(466,846,'Current anchor',17,INK)
    f.text(676,846,'Reconstruct / predict',17,ORANGE)
    f.p.append('<text x="1000" y="749" font-size="24" fill="#252525">L = L<tspan baseline-shift="sub" font-size="15">action</tspan><tspan baseline-shift="baseline"> + (L</tspan><tspan baseline-shift="sub" font-size="15">C,future</tspan><tspan baseline-shift="baseline"> + L</tspan><tspan baseline-shift="sub" font-size="15">Q,past</tspan><tspan baseline-shift="baseline"> + L</tspan><tspan baseline-shift="sub" font-size="15">Q,future</tspan><tspan baseline-shift="baseline">) / 3</tspan></text>')
    f.text(1000,782,'Flow-matching losses on valid targets.',17,GRAY)
    f.text(1000,817,'C: same decoder; observed past stays fixed.',17,GRAY)
    f.text(40,885,'64 C points · 64 Q points · 16 history frames · privileged simulator history in PullCube',16,GRAY)
    f.text(1560,885,'All trajectory sketches are schematic.',16,GRAY,anchor='end')
    f.save('architecture')



if __name__ == '__main__':
    overview()
    svg = OUT / 'architecture.svg'
    for ext, options in [('png', ['--export-width=3200']), ('pdf', [])]:
        subprocess.run(['inkscape', str(svg), f'--export-filename={OUT / ("architecture." + ext)}', *options], check=True)
    subprocess.run(['pdfunite', str(OUT/'architecture.pdf'), str(OUT/'shared-tokenizer.pdf'), str(OUT/'b5-figures.pdf')], check=True)
    subprocess.run(['pdfunite', str(OUT/'architecture.pdf'), str(OUT/'hpt-internals.pdf'), str(OUT/'shared-tokenizer.pdf'), str(OUT/'b5-figures-with-hpt.pdf')], check=True)
    print('Updated overview SVG/PNG/PDF and both PDF bundles.')
