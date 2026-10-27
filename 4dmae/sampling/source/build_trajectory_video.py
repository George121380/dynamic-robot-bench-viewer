"""A shareable two-panel movie of observed input and withheld reference tracks."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
    d=json.loads((root/'public/animation/clip-988.json').read_text());selection=d['samples']['holdout:cube/0']
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    decoded=subprocess.run([ff,'-v','error','-i',str(root/'public/animation/clip-988.mp4'),'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True).stdout
    images=np.frombuffer(decoded,dtype=np.uint8).reshape(-1,512,512,3);assert len(images)==160
    fontpath='/System/Library/Fonts/Supplemental/Arial.ttf'
    fonts={n:ImageFont.truetype(fontpath,n) for n in (15,17,19,29)}
    colors={'C':'#0072b2','Q':'#d55e00'}
    writer=subprocess.Popen([ff,'-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','10','-i','-','-an','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(root/'public/animation/trajectory-demo.mp4')],stdin=subprocess.PIPE)
    try:
        for t in range(64,160):
            canvas=Image.new('RGB',(1280,720),'white');draw=ImageDraw.Draw(canvas)
            draw.text((640,17),'Point Trajectories',font=fonts[29],fill='#333',anchor='mt')
            draw.text((640,57),'PullCubeTool · Cube holdout · Seed 0 · 64-state history · 0.5× playback',font=fonts[17],fill='#666',anchor='mt')
            for role,x in [('C',64),('Q',704)]:
                current=min(t,127) if role=='C' else t
                panel=Image.fromarray(images[current].copy());pd=ImageDraw.Draw(panel)
                for idx in selection[role]:
                    point=d['points'][idx];path=[tuple(p) for p in point['uv'][64:current+1]]
                    if len(path)>1:
                        pd.line(path,fill='white',width=4,joint='curve')
                        pd.line(path,fill=colors[role],width=2,joint='curve')
                roles=[(role,current,selection[role])]
                if role=='C' and t>=127:roles.append(('Q',127,selection['Q']))
                for marker_role,k,indices in roles:
                    for idx in indices:
                        point=d['points'][idx];u,v=point['uv'][k]
                        if not (0<=u<512 and 0<=v<512):continue
                        color=colors[marker_role];fill=color if point['visible'][k] or (marker_role=='Q' and role=='C') else None
                        if marker_role=='C':
                            pd.ellipse((u-5,v-5,u+5,v+5),outline='white',width=3)
                            pd.ellipse((u-4,v-4,u+4,v+4),fill=fill,outline=color,width=2)
                        else:
                            pts=[(u,v-5),(u+5,v),(u,v+5),(u-5,v)]
                            pd.line(pts+[pts[0]],fill='white',width=4)
                            pd.polygon(pts,fill=fill,outline=color,width=2)
                canvas.paste(panel,(x,119))
                title=('Condition input · frozen at t0' if t>127 else 'Condition trajectories') if role=='C' else 'Query trajectories'
                draw.text((x,88),title,font=fonts[19],fill='#333')
                caption='15 condition · Input history: 3.15 s' if role=='C' else '3 query · Ground truth, not model input'
                draw.text((x,641),caption,font=fonts[17],fill=colors[role])
            elapsed=(t-127)/20
            phase='Future reference' if t>127 else 'Input boundary' if t==127 else 'Observed history'
            draw.line((64,680,1216,680),fill='#ddd',width=3)
            progress=64+(t-64)/95*1152;boundary=64+63/95*1152
            draw.line((64,680,progress,680),fill=colors['C'] if t<=127 else colors['Q'],width=3)
            draw.line((boundary,674,boundary,686),fill='#666',width=1)
            draw.text((64,693),f'{elapsed:+.2f} s · {phase}',font=fonts[15],fill='#555')
            draw.text((1216,693),'Demo 416 · Frame 988 · Simulation ground truth',font=fonts[15],fill='#777',anchor='rt')
            writer.stdin.write(canvas.tobytes())
            if t in (64,127,159):canvas.save(root/'qa'/f'trajectory-video-{t}.png')
        writer.stdin.close();assert writer.wait()==0
    finally:
        if writer.poll() is None:writer.terminate();writer.wait()
    print('Built 96-frame, 1280 × 720 movie at 10 fps (0.5× playback)')

if __name__=='__main__':main()
