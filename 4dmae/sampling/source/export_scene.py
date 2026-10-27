"""Restore three saved states and export visible material points; no physics stepping."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import h5py
from PIL import Image


def array(x):
    return x.detach().cpu().numpy() if hasattr(x, 'detach') else np.asarray(x)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--size', type=int, default=512)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    import gymnasium as gym
    import mani_skill.envs
    import inspect
    from mani_skill.envs.tasks.tabletop.pull_cube_tool import PullCubeToolEnv
    from benchmarks.pull_cube_tool.common import read_tree, at
    source_sha = hashlib.sha256(Path(inspect.getfile(PullCubeToolEnv)).read_bytes()).hexdigest()
    assert source_sha == 'ece01ba3fd851268874fdbcefbfbc0a8ea833c31293cff6343fd46eaff929a1a'
    index = json.loads((args.source/'index.json').read_text())
    record = next(r for r in index['records'] if r['episode_id'] == 416)
    with h5py.File(args.source/'raw/trajectory.h5', 'r') as f:
        states = read_tree(f['traj_416/env_states'])
    env = gym.make('PullCubeTool-v1', num_envs=1, obs_mode='rgb+depth+segmentation', reward_mode='none',
        control_mode='pd_joint_pos', render_mode='rgb_array', sim_backend='cpu',
        render_backend='gpu', max_episode_steps=1200,
        sensor_configs={'shader_pack':'default', 'width':args.size, 'height':args.size})
    base = env.unwrapped
    report = dict(episode=416, seed=record['seed'], frames=[255,510,765], resolution=args.size,
        environment_commit='95ea99d4eaad36477823d97077ab935caeb73359', task_source_sha256=source_sha,
        source_trajectory_sha256=index['config']['files']['trajectory.h5'],
        physics_steps=0, time_step_s=.05, position_source='raw float32 Position texture (metres)',
        coordinate_frame='fixed simulator world', frame_reports=[])
    try:
        env.reset(seed=record['seed'])
        bodies = {}
        for name, obj in base.scene.actors.items():
            ent = obj._objs[0]
            sid = int(ent.per_scene_id)
            group = 'cube' if name == 'cube' else 'tool' if name == 'l_shape_tool' else 'background'
            bodies[sid] = (obj, dict(id=sid, name=name, group=group, part=group,
                                    kind=str(obj.px_body_type)))
        for link in base.agent.robot.get_links():
            name = link.name
            sid = int(link._objs[0].entity.per_scene_id)
            part = ('left_finger' if name.startswith('panda_leftfinger') else
                    'right_finger' if name.startswith('panda_rightfinger') else
                    'palm' if name.startswith('panda_hand') else 'arm')
            bodies[sid] = (link, dict(id=sid, name=name,
                group='gripper' if part != 'arm' else 'robot', part=part, kind='articulation_link'))
        ids = sorted(bodies)
        report['bodies'] = [bodies[i][1] for i in ids]
        print(json.dumps({'bodies':report['bodies']}), flush=True)
        for frame in report['frames']:
            poses = []
            state_error = 0.
            for t in range(frame-15, frame+16):
                base.set_state_dict(at(states,t))
                restored = base.get_state_dict()
                for name in ('cube','l_shape_tool'):
                    state_error = max(state_error, float(np.abs(array(restored['actors'][name])[0,:7]-states['actors'][name][t,:7]).max()))
                poses.append(np.stack([array(bodies[i][0].pose.to_transformation_matrix())[0] for i in ids]))
            base.set_state_dict(at(states, frame))
            raw = base._get_obs_sensor_data(apply_texture_transforms=False)['base_camera']
            cam = base._sensors['base_camera']
            params = {k:array(v)[0] for k,v in cam.get_params().items()}
            rgb = np.clip(array(raw['Color'])[0,:,:,:3]*255,0,255).astype(np.uint8)
            pos = array(raw['Position'])[0,:,:,:3].astype(np.float32)
            seg = array(raw['Segmentation'])[0,:,:,1].astype(np.int32)
            xyz = pos @ params['cam2world_gl'][:3,:3].T + params['cam2world_gl'][:3,3]
            live = (seg != 0) & (pos[:,:,2] < -.01) & np.isfinite(xyz).all(-1)
            unknown = set(np.unique(seg[live]).tolist()) - set(ids)
            assert not unknown, ('Unmapped visible bodies', unknown)
            cv = xyz @ params['extrinsic_cv'][:3,:3].T + params['extrinsic_cv'][:3,3]
            projected = cv @ params['intrinsic_cv'].T
            uv = projected[:,:,:2] / np.maximum(projected[:,:,2:], 1e-9)
            yy,xx = np.indices(seg.shape)
            pixel_offset = uv[live]-np.stack((xx,yy),-1)[live]
            offset = np.median(pixel_offset,axis=0)
            projection_error = float(np.abs(pixel_offset-offset).max())
            assert projection_error < .02, projection_error
            assert state_error < 1e-5, state_error
            np.savez_compressed(args.output/f'frame-{frame}.npz', xyz=xyz, segmentation=seg,
                valid=live, uv=uv, body_ids=ids, body_poses=np.stack(poses),
                physical_frames=np.arange(frame-15,frame+16), **params)
            Image.fromarray(rgb).save(args.output/f'frame-{frame}.png')
            row=dict(frame=frame, valid_pixels=int(live.sum()),
                visible_pixels={str(i):int(((seg==i)&live).sum()) for i in ids},
                max_state_pose_error=state_error, max_projection_error_px=projection_error,
                pixel_center_offset=offset.tolist())
            report['frame_reports'].append(row)
            print(json.dumps(row), flush=True)
        (args.output/'scene.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:
        env.close()


if __name__ == '__main__':
    main()
