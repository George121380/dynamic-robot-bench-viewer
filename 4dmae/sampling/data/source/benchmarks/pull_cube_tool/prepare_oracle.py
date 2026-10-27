"""Immutable oracle-track derivative of the accepted official RGB/action release."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import time
import h5py
import numpy as np
from .common import sha, write
from .oracle import point_bank, window_columns, HISTORY


def export_episode(args):
    parent, root, row = args
    relative = Path('windows')/f"episode-{row['episode_id']:04d}"
    source, dest = parent/relative, root/relative
    dest.mkdir(parents=True)
    inherited = []
    for name in ('observation.rgb','observation.state','targets.action','targets.action_valid'):
        old, new = source/(name+'.npy'), dest/(name+'.npy')
        os.link(old,new)
        assert os.path.samefile(old,new)
        inherited.append(new.name)
    with h5py.File(parent/'raw/trajectory.h5','r') as f:
        group = f[f"traj_{row['episode_id']}/env_states/actors"]
        actors = {name:group[name][:] for name in point_bank()}
    columns = window_columns(actors,point_bank(),row['windows'])
    for name, value in columns.items():
        assert len(value) == row['windows'] and np.isfinite(value).all()
        np.save(dest/(name+'.npy'),value,allow_pickle=False)
    receipt = dict(episode_id=row['episode_id'],split=row['split'],windows=row['windows'],
        inherited_hardlinks=inherited, files={name+'.npy':sha(dest/(name+'.npy')) for name in columns})
    write(dest/'receipt.json',receipt)
    return receipt


def prepare(parent, root, workers=8):
    start = time.monotonic()
    release = json.loads((parent/'release.json').read_text())
    assert release['status'] == 'ready' and release['manifest_sha256'] == sha(parent/'manifest.json')
    parent_manifest = json.loads((parent/'manifest.json').read_text())
    index = json.loads((parent/'index.json').read_text())
    suite = json.loads((parent/'evaluation-cases.json').read_text())
    assert suite['manifest_sha256'] == sha(parent/'manifest.json')
    root.mkdir(parents=True,exist_ok=False)
    for old, new in [('manifest.json','parent-manifest.json'),('index.json','index.json'),
                     ('evaluation-cases.json','evaluation-cases.json')]:
        os.link(parent/old,root/new)
    (root/'raw').mkdir()
    os.link(parent/'raw/trajectory.h5',root/'raw/trajectory.h5')
    bank = point_bank()
    write(root/'point-bank.json',dict(seed=42,objects={k:v.tolist() for k,v in bank.items()},
        c_indices=list(range(32)),q_indices=list(range(32,64))))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(export_episode,[(parent,root,r) for r in index['records']]))
    meta = dict(parent_manifest['metadata'], coordinate_units='m',coordinate_frame='world',
        history_offsets_s=[round(i*.05,8) for i in range(1-HISTORY,1)],
        future_offsets_s=[round(i*.05,8) for i in range(1,HISTORY)],
        parent_manifest_sha256=sha(parent/'manifest.json'),
        evaluation_cases_sha256=sha(root/'evaluation-cases.json'),
        point_bank_sha256=sha(root/'point-bank.json'),
        tracks=dict(source='privileged_simulator_rigid_actor_poses',version='oracle-flow-v1',
            points_c=64,points_q=64,points_per_object_per_set=32,visibility_filtered=False,
            sampling='seed42 area-weighted true exterior surfaces; disjoint persistent C/Q identities',
            history='15 past plus current; missing past zero with invalid mask',
            labels='world displacement from current anchor; 15 past / 15 future; never observations'))
    manifest = dict(parent_manifest, metadata=meta)
    # Exact same split order and episode/window identities as the parent release.
    assert manifest['splits'] == parent_manifest['splits']
    assert sum(r['windows'] for r in records) == sum(release['windows'].values())
    write(root/'manifest.json',manifest)
    from four_d_mae.data import WindowDataset
    policies = [dict(name=name,model=dict(arm=arm,state_dim=9,action_dim=8,chunk=32,history=16))
                for name,arm in [('egowam','B1'),('4dmae','B5')]]
    statistics = [WindowDataset(root/'manifest.json','train',policy).statistics('q_future')
                  for policy in policies]
    assert statistics[0] == statistics[1], 'Paired normalization mismatch'
    WindowDataset(root/'manifest.json','validation',policies[1]).preflight()
    write(root/'training-statistics.json',statistics[0])
    write(root/'release.json',dict(status='ready',manifest_sha256=sha(root/'manifest.json'),
        parent_manifest_sha256=meta['parent_manifest_sha256'],episodes=release['episodes'],
        windows=release['windows'],inherited_arrays='same inode; parent data unmodified',
        evaluation_cases_sha256=meta['evaluation_cases_sha256'],records=records,
        seconds=time.monotonic()-start))
    print(json.dumps(dict(status='ready',episodes=len(records),windows=release['windows'],
                         seconds=time.monotonic()-start)),flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent',type=Path,required=True)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--workers',type=int,default=8)
    a=p.parse_args()
    prepare(a.parent.resolve(),a.root.resolve(),a.workers)
