"""Build fixed-identity tracks, visibility checks and playable clip metadata."""
import argparse,json,shutil
from pathlib import Path
import numpy as np
from build_samples import Scene,CONFIG

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
    dest=root/'public/animation';dest.mkdir(parents=True,exist_ok=True)
    reports=[];modes=['random','dino','holdout:cube','holdout:tool','holdout:gripper']
    for anchor in [255,510,765,988]:
        scene=Scene(root,anchor);z=np.load(root/'raw/animation'/f'clip-{anchor}.npz')
        pooled={};samples={}
        for mode in modes:
            for seed in CONFIG['seeds']:
                c,q=scene.choose(mode,seed)
                assert len(set(c)&set(q))==0
                if mode.startswith('holdout:'):
                    target=mode.split(':')[1]
                    assert all(scene.bodies[int(scene.seg.ravel()[i])]['group']!=target for i in c)
                    assert all(scene.bodies[int(scene.seg.ravel()[i])]['group']==target for i in q)
                groups={}
                for role,ids in [('C',c),('Q',q)]:
                    groups[role]=[]
                    for idx in ids:
                        idx=int(idx)
                        if idx not in pooled:
                            p=scene.point(idx,role)
                            pooled[idx]=dict(index=len(pooled),pixel_id=idx,body_id=p['body_id'],entity=p['entity'],part=p['part'],local_xyz_m=p['local_xyz_m'])
                        groups[role].append(pooled[idx]['index'])
                samples[f'{mode}/{seed}']=groups
                scene.z['body_poses'][16:]=np.nan
                c2,q2=scene.choose(mode,seed)
                assert np.array_equal(c,c2) and np.array_equal(q,q2)
                # Restore reference poses before constructing new point records.
                scene.z['body_poses']=z['body_poses'][112:143]
        points=list(pooled.values());body_indices={int(x):i for i,x in enumerate(z['body_ids'])}
        bi=np.array([body_indices[p['body_id']] for p in points]);local=np.array([p['local_xyz_m'] for p in points])
        poses=z['body_poses'][:,bi]
        xyz=np.einsum('tpij,pj->tpi',poses[:,:,:3,:3],local)+poses[:,:,:3,3]
        e=z['extrinsic_cv'];k=z['intrinsic_cv'];cv=xyz@e[:3,:3].T+e[:3,3];projection=cv@k.T
        uv=projection[:,:,:2]/projection[:,:,2:];finite=np.isfinite(uv).all(-1)&(cv[:,:,2]>.01)
        pixels=np.floor(np.nan_to_num(uv)).astype(np.int64);inside=finite&(pixels[:,:,0]>=0)&(pixels[:,:,0]<512)&(pixels[:,:,1]>=0)&(pixels[:,:,1]<512)
        pixels=np.clip(pixels,0,511);times=np.arange(len(uv))[:,None]
        segmentation=z['segmentation'];depth=z['depth'];sample_depth=depth[times,pixels[:,:,1],pixels[:,:,0]]
        sid=np.array([p['body_id'] for p in points])[None]
        visible=inside&(segmentation[times,pixels[:,:,1],pixels[:,:,0]]==sid)&(np.abs(cv[:,:,2]-sample_depth)<(.004+.003*sample_depth))
        maximum_anchor_error=0
        for i,p in enumerate(points):
            error=np.max(np.abs(xyz[127,i]-scene.xyz[p['pixel_id']]))
            maximum_anchor_error=max(maximum_anchor_error,float(error))
            p['uv']=np.round(np.clip(np.nan_to_num(uv[:,i]),-1e6,1e6),3).tolist()
            p['visible']=visible[:,i].astype(int).tolist()
            p['displacement_64_m']=round(float(np.linalg.norm(xyz[127,i]-xyz[64,i])),7)
        assert maximum_anchor_error<1e-5
        assert len(z['physical_frames'])==160 and int(z['physical_frames'][127])==anchor
        clip=dict(anchor=anchor,episode=416,fps=20,anchor_index=127,frame_count=160,physical_frames=z['physical_frames'].tolist(),history_options=[16,32,64,128],future_states=32,points=points,samples=samples,video=f'animation/clip-{anchor}.mp4',poster=f'animation/frame-{anchor}.png',oracle_tracks=True)
        (dest/f'clip-{anchor}.json').write_text(json.dumps(clip,separators=(',',':'))+'\n')
        for suffix,prefix in [('mp4','clip'),('png','frame')]:shutil.copy2(root/'raw/animation'/f'{prefix}-{anchor}.{suffix}',dest/f'{prefix}-{anchor}.{suffix}')
        reports.append(dict(anchor=anchor,sample_sets=len(samples),unique_points=len(points),anchor_error_m=maximum_anchor_error,future_independent_selection=True,visible_point_fraction=float(visible.mean()),minimum_visible_current=float(visible[127].mean())))
        print(json.dumps(reports[-1]),flush=True)
    report=dict(clips=reports,identity='fixed material anchors; never resampled during playback',visibility='body ID plus depth tolerance 4 mm + 0.3% depth',fps=20,physics_steps=0,model_predictions=False)
    (root/'qa/animation-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (dest/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copy2(root/'scripts/trajectory.template.html',root/'public/trajectories.html')

if __name__=='__main__':main()
