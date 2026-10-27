"""Check information boundaries and report coverage without assuming sampler superiority."""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
from build_samples import Scene, CONFIG

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
modes=['random','dino','holdout:cube','holdout:tool','holdout:gripper']
result={'future_independent_selection':True,'dino_features_affect_selection':False,
        'gripper_includes_palm_fingers_and_pads':True,'coverage':{},'minimum_finger_pixel_separation':None}
min_separation=float('inf');feature_changes=0
for frame in CONFIG['frames']:
    s=Scene(a.root,frame)
    before={(m,seed):s.choose(m,seed) for m in modes for seed in CONFIG['seeds']}
    # Invalidating all future poses must not alter any selected index.
    s.z['body_poses'][16:]=np.nan
    for (mode,seed),(c,q) in before.items():
        c2,q2=s.choose(mode,seed)
        assert np.array_equal(c,c2) and np.array_equal(q,q2)
    for name in ['panda_hand','panda_leftfinger','panda_leftfinger_pad','panda_rightfinger','panda_rightfinger_pad']:
        assert next(b for b in s.bodies.values() if b['name']==name)['group']=='gripper'
    frame_stats={}
    for mode in ['random','dino']:
        counts=Counter()
        for seed in CONFIG['seeds']:
            for idx in np.concatenate(before[mode,seed]):
                counts[s.bodies[int(s.seg.ravel()[idx])]['group']]+=1
        frame_stats[mode]={'mean_points_per_seed':{k:v/len(CONFIG['seeds']) for k,v in counts.items()}}
    result['coverage'][str(frame)]=frame_stats
    for seed in CONFIG['seeds']:
        q=before['holdout:gripper',seed][1]
        for part in CONFIG['object_holdout']['gripper_parts']:
            ids=np.asarray([i for i in q if s.bodies[int(s.seg.ravel()[i])]['part']==part])
            assert len(ids)<=3
            if len(ids)>1 and part!='palm':
                distances=np.linalg.norm(s.uv[ids,None]-s.uv[None,ids],axis=-1)
                distances[np.diag_indices(len(ids))]=np.inf
                min_separation=min(min_separation,float(distances.min()))
    s.features=np.zeros_like(s.features)
    for seed in CONFIG['seeds']:
        old=np.concatenate(before['dino',seed]);new=np.concatenate(s.choose('dino',seed))
        feature_changes+=int(set(old)!=set(new))
assert feature_changes>0
result['dino_features_affect_selection']=True
result['feature_ablation_changed_sets']=feature_changes
result['minimum_finger_pixel_separation']=min_separation
result['interpretation']='Coverage is descriptive for one demonstration; this is not a performance comparison.'
(a.root/'qa/causal-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
