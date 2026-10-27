"""Render saved trajectory windows and geometry without physics steps."""
import argparse, hashlib, inspect, json, subprocess
from pathlib import Path
import numpy as np
import h5py
from PIL import Image
from export_scene import array

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    import gymnasium as gym
    import mani_skill.envs
    import imageio_ffmpeg
    from mani_skill.envs.tasks.tabletop.pull_cube_tool import PullCubeToolEnv
    from benchmarks.pull_cube_tool.common import read_tree,at
    source_hash=hashlib.sha256(Path(inspect.getfile(PullCubeToolEnv)).read_bytes()).hexdigest()
    assert source_hash=='ece01ba3fd851268874fdbcefbfbc0a8ea833c31293cff6343fd46eaff929a1a'
    index=json.loads((a.source/'index.json').read_text());record=next(r for r in index['records'] if r['episode_id']==416)
    with h5py.File(a.source/'raw/trajectory.h5','r') as f:states=read_tree(f['traj_416/env_states'])
    env=gym.make('PullCubeTool-v1',num_envs=1,obs_mode='rgb+depth+segmentation',reward_mode='none',control_mode='pd_joint_pos',render_mode='rgb_array',sim_backend='cpu',render_backend='gpu',max_episode_steps=1200,sensor_configs={'shader_pack':'default','width':512,'height':512})
    base=env.unwrapped;env.reset(seed=record['seed']);bodies={}
    for name,obj in base.scene.actors.items():bodies[int(obj._objs[0].per_scene_id)]=obj
    for obj in base.agent.robot.get_links():bodies[int(obj._objs[0].entity.per_scene_id)]=obj
    ids=sorted(bodies);reports=[]
    try:
        for anchor in [255,510,765,988]:
            frames=np.arange(anchor-127,anchor+33);poses=[];depth=[];segments=[];geometry=None;pose_error=0
            ff=imageio_ffmpeg.get_ffmpeg_exe()
            writer=subprocess.Popen([ff,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','512x512','-framerate','20','-i','-','-an','-c:v','libx264','-crf','16','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(a.output/f'clip-{anchor}.mp4')],stdin=subprocess.PIPE)
            try:
                for t in frames:
                    base.set_state_dict(at(states,int(t)))
                    restored=base.get_state_dict()
                    for name in ['cube','l_shape_tool']:pose_error=max(pose_error,float(np.max(np.abs(array(restored['actors'][name])[0,:7]-states['actors'][name][t,:7]))))
                    poses.append(np.stack([array(bodies[i].pose.to_transformation_matrix())[0] for i in ids]))
                    raw=base._get_obs_sensor_data(apply_texture_transforms=False)['base_camera']
                    params={k:array(v)[0] for k,v in base._sensors['base_camera'].get_params().items()}
                    rgb=np.clip(array(raw['Color'])[0,:,:,:3]*255,0,255).astype(np.uint8)
                    pos=array(raw['Position'])[0,:,:,:3].astype(np.float32)
                    seg=array(raw['Segmentation'])[0,:,:,1].astype(np.uint8)
                    writer.stdin.write(rgb.tobytes());depth.append(-pos[:,:,2]);segments.append(seg)
                    if t==anchor:
                        xyz=pos@params['cam2world_gl'][:3,:3].T+params['cam2world_gl'][:3,3]
                        live=(seg!=0)&(pos[:,:,2]<-.01)&np.isfinite(xyz).all(-1)
                        cv=xyz@params['extrinsic_cv'][:3,:3].T+params['extrinsic_cv'][:3,3];proj=cv@params['intrinsic_cv'].T
                        uv=proj[:,:,:2]/np.maximum(proj[:,:,2:],1e-9)
                        geometry=dict(xyz=xyz,segmentation=seg.astype(np.int32),valid=live,uv=uv,**params)
                        Image.fromarray(rgb).save(a.output/f'frame-{anchor}.png')
                writer.stdin.close();assert writer.wait()==0
            finally:
                if writer.poll() is None:writer.terminate();writer.wait()
            assert pose_error<1e-5
            pose_array=np.asarray(poses)
            np.savez_compressed(a.output/f'clip-{anchor}.npz',physical_frames=frames,body_ids=ids,body_poses=pose_array,depth=np.asarray(depth),segmentation=np.asarray(segments),**params)
            np.savez_compressed(a.output/f'frame-{anchor}.npz',body_ids=ids,body_poses=pose_array[112:143],physical_frames=frames[112:143],**geometry)
            report=dict(anchor=anchor,first=int(frames[0]),last=int(frames[-1]),frames=len(frames),max_pose_error=pose_error)
            reports.append(report);print(json.dumps(report),flush=True)
        (a.output/'render-verification.json').write_text(json.dumps(dict(episode=416,seed=record['seed'],fps=20,physics_steps=0,task_sha256=source_hash,clips=reports),indent=2)+'\n')
    finally:env.close()

if __name__=='__main__':main()
