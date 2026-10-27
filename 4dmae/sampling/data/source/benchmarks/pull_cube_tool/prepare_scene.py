"""Render a sparse geometry sidecar from saved states; preserve every old window."""
import argparse
import json
import os
from pathlib import Path
import time
import numpy as np
from .common import sha,write,read_tree,at
from .scene_geometry import SceneGeometry,CAPACITY


def initialize(parent,root):
    release=json.loads((parent/'release.json').read_text())
    assert release['status']=='ready' and release['manifest_sha256']==sha(parent/'manifest.json')
    root.mkdir(parents=True,exist_ok=False)
    for old,new in [('manifest.json','parent-manifest.json'),('index.json','index.json'),('evaluation-cases.json','evaluation-cases.json')]:
        os.link(parent/old,root/new)
    write(root/'source.json',dict(parent=str(parent),manifest_sha256=sha(parent/'manifest.json')))


def export(parent,root,worker,workers,limit=None):
    import h5py
    from .environment import make_environment,observation
    index=json.loads((parent/'index.json').read_text());records=index['records'][worker::workers]
    if limit is not None:records=records[:limit]
    env=make_environment();view=None;previous_scene=None
    try:
        with h5py.File(parent/'raw/trajectory.h5','r') as f:
            for row in records:
                ep=row['episode_id'];folder=root/'windows'/f'episode-{ep:04d}';receipt=folder/'receipt.json'
                if receipt.exists():
                    old=json.loads(receipt.read_text());assert old['index_fingerprint']==index['fingerprint']
                    assert all(sha(folder/k)==v for k,v in old['files'].items());continue
                folder.mkdir(parents=True,exist_ok=True);start=time.monotonic()
                states=read_tree(f[f'traj_{ep}/env_states']);n=row['windows'];steps=row['steps']
                env.reset(seed=row['seed'])
                if env.unwrapped.scene is not previous_scene:
                    view=SceneGeometry(env);previous_scene=env.unwrapped.scene
                else:view.refresh_bodies()
                write(folder/'bodies.json',view.bodies)
                shapes={'pixel':((n,CAPACITY),np.int32),'body':((n,CAPACITY),np.int16),
                        'local':((n,CAPACITY,3),np.float32),'cell':((n,CAPACITY),np.uint8),
                        'global_pool':((n,CAPACITY),bool),'poses':((steps+1,len(view.bodies),4,4),np.float32)}
                arrays={k:np.lib.format.open_memmap(folder/(k+'.npy'),mode='w+',dtype=dtype,shape=shape) for k,(shape,dtype) in shapes.items()}
                max_projection=0.;min_global=CAPACITY;max_pose_error=0.
                inherited=[]
                for name in ['observation.rgb.npy','observation.state.npy','targets.action.npy','targets.action_valid.npy']:
                    if not (folder/name).exists():os.link(parent/'windows'/f'episode-{ep:04d}'/name,folder/name)
                    assert os.path.samefile(folder/name,parent/'windows'/f'episode-{ep:04d}'/name);inherited.append(name)
                source_rgb=np.load(folder/'observation.rgb.npy',mmap_mode='r')
                for tick in range(steps+1):
                    env.unwrapped.set_state_dict(at(states,tick));arrays['poses'][tick]=view.poses()
                    actual=env.unwrapped.get_state_dict()
                    for name in ('cube','l_shape_tool'):
                        max_pose_error=max(max_pose_error,float(np.abs(actual['actors'][name][0,:7].cpu().numpy()-states['actors'][name][tick,:7]).max()))
                    if tick>=n:continue
                    candidates,check,params=view.candidates(episode=ep,tick=tick)
                    for k,v in candidates.items():arrays[k][tick]=v
                    max_projection=max(max_projection,check['projection_error_px']);min_global=min(min_global,check['global_candidates'])
                    if tick in (0,n//2,n-1):
                        rgb,state=observation(env)
                        assert np.array_equal(rgb,source_rgb[tick]),'Additional geometry camera changed original policy RGB'
                        assert np.array_equal(state,states['articulations']['panda'][tick,13:22])
                assert max_pose_error<1e-5 and min_global>=24
                for v in arrays.values():v.flush()
                del arrays
                np.savez(folder/'camera.npz',**params)
                names=[k+'.npy' for k in shapes]+['bodies.json','camera.npz']
                result=dict(episode_id=ep,split=row['split'],windows=n,index_fingerprint=index['fingerprint'],
                    source_rgb_verified=True,inherited_hardlinks=inherited,max_pose_error=max_pose_error,
                    max_projection_error_px=max_projection,min_global_candidates=min_global,physics_steps=0,
                    seconds=time.monotonic()-start,files={k:sha(folder/k) for k in names})
                write(receipt,result);print(json.dumps({k:v for k,v in result.items() if k not in ('files','inherited_hardlinks')}),flush=True)
    finally:env.close()


def finalize(parent,root):
    index=json.loads((parent/'index.json').read_text());original=json.loads((parent/'manifest.json').read_text())
    release=json.loads((parent/'release.json').read_text());records=[]
    for row in index['records']:
        folder=root/'windows'/f"episode-{row['episode_id']:04d}"
        r=json.loads((folder/'receipt.json').read_text());assert r['index_fingerprint']==index['fingerprint'] and r['windows']==row['windows']
        assert all(sha(folder/k)==v for k,v in r['files'].items());records.append(r)
    metadata=dict(original['metadata'],coordinate_units='m',coordinate_frame='world',
        history_offsets_s=[round(i*.05,8) for i in range(-15,1)],future_offsets_s=[round(i*.05,8) for i in range(1,16)],
        parent_manifest_sha256=sha(parent/'manifest.json'),evaluation_cases_sha256=sha(root/'evaluation-cases.json'),
        tracks=dict(source='visible_current_material_points_with_oracle_rigid_link_poses',version='scene-motion-v1',
            geometry_resolution=512,policy_rgb_resolution=128,candidate_seed=42,global_grid=[4,6],candidates_per_cell=8,
            candidates_per_target_part=32,history='15 past plus current; early history masked; historical occlusion is oracle',
            labels='anchor-relative world displacement; 15 past / 15 future; supervision only',gripper='palm and both fingers, separately articulated'))
    write(root/'manifest.json',dict(schema='4dmae.scene_windows.v1',metadata=metadata,splits=original['splits']))
    assert sum(r['windows'] for r in records)==sum(release['windows'].values())
    write(root/'release.json',dict(status='ready',manifest_sha256=sha(root/'manifest.json'),
        episodes=release['episodes'],windows=release['windows'],source_arrays_verified=True,records=records))
    print(json.dumps(dict(status='ready',episodes=release['episodes'],windows=release['windows'])),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['initialize','export','finalize'])
    p.add_argument('--parent',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--worker',type=int,default=0);p.add_argument('--workers',type=int,default=8);p.add_argument('--limit',type=int)
    a=p.parse_args()
    if a.stage=='initialize':initialize(a.parent,a.root)
    elif a.stage=='finalize':finalize(a.parent,a.root)
    else:export(a.parent,a.root,a.worker,a.workers,a.limit)


if __name__=='__main__':main()
