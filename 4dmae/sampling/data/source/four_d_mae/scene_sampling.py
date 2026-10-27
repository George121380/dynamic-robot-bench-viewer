"""Stateless paired scene/holdout point sampling. No simulator or model imports.

Candidate IDs are unique current-frame pixels. ``global`` marks the stratified
scene pool; supplemental object candidates are used only for target queries.
Groups: 0 background/arm, 1 cube, 2 tool, 3 articulated gripper.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import numpy as np


@dataclass(frozen=True)
class SamplingConfig:
    mode: str = 'mixed'
    holdout_probability: float = .5
    condition_points: int = 12
    query_points: int = 12
    target_query_points: int = 3
    seed: int = 42
    batch_balance: bool = True

    def __post_init__(self):
        if self.mode not in ('scene','holdout','mixed'):
            raise ValueError('Sampling mode must be scene, holdout or mixed')
        if type(self.batch_balance) is not bool:raise ValueError('batch_balance must be boolean')
        if not 0 <= self.holdout_probability <= 1:
            raise ValueError('Invalid holdout probability')
        for key in ('condition_points','query_points','target_query_points','seed'):
            v=getattr(self,key)
            if type(v) is not int or v < (0 if key=='seed' else 1):
                raise ValueError('Invalid sampling integer: '+key)
        if self.target_query_points>self.query_points:
            raise ValueError('Target queries exceed total queries')

    def to_dict(self):return asdict(self)


def rng(seed,epoch,episode,tick,stream):
    key=json.dumps([int(seed),int(epoch),str(episode),int(tick),stream],separators=(',',':'))
    return np.random.default_rng(int.from_bytes(hashlib.blake2b(key.encode(),digest_size=16).digest(),'little'))


def stratified(indices,cells,count,generator):
    """Random cell ordering, then round-robin without replacement within cells."""
    indices=np.asarray(indices,dtype=np.int64)
    if len(indices)<count:raise ValueError('Insufficient distinct scene candidates')
    if count==0:return np.empty(0,np.int64)
    labels=np.unique(cells[indices]);generator.shuffle(labels)
    pools=[generator.permutation(indices[cells[indices]==c]).tolist() for c in labels]
    chosen=[]
    while len(chosen)<count:
        for pool in pools:
            if pool:chosen.append(pool.pop())
            if len(chosen)==count:break
    return np.asarray(chosen,np.int64)


def spread(indices,xyz,parts,count,generator):
    """Stochastic farthest-point selection, covering visible gripper parts first."""
    indices=np.asarray(indices,np.int64)
    if len(indices)<count:raise ValueError('Insufficient target candidates')
    groups=np.unique(parts[indices]);generator.shuffle(groups)
    chosen=[]
    for part in groups[:count]:
        pool=indices[parts[indices]==part]
        chosen.append(int(generator.choice(pool)))
    while len(chosen)<count:
        pool=indices[~np.isin(indices,chosen)]
        distance=((xyz[pool,None]-xyz[np.asarray(chosen)][None])**2).sum(-1).min(-1)
        if len(groups)==1 and len(chosen)==2:
            # Three rigid-body anchors should span a triangle when the visible
            # surface permits it, rather than three positions along one edge.
            axis=xyz[chosen[1]]-xyz[chosen[0]]
            area=np.square(np.cross(xyz[pool]-xyz[chosen[0]],axis)).sum(-1)
            if area.max()>1e-16:distance=area
        # Random tie order avoids a pixel-order preference on planar surfaces.
        order=generator.permutation(len(pool))
        chosen.append(int(pool[order[np.argmax(distance[order])]]))
    return np.asarray(chosen,np.int64)


def sample_points(candidates,config,*,epoch=0,episode=0,tick=0):
    c=config if isinstance(config,SamplingConfig) else SamplingConfig(**config)
    pixel=np.asarray(candidates['pixel']);live=pixel>=0
    ids=np.flatnonzero(live);groups=np.asarray(candidates['group']);cells=np.asarray(candidates['cell'])
    global_ids=ids[np.asarray(candidates['global'],bool)[ids]]
    if len(np.unique(pixel[ids]))!=len(ids):raise ValueError('Duplicate current-frame material candidates')
    if len(global_ids)<c.condition_points+c.query_points:
        raise ValueError('Global pool cannot supply disjoint C and Q')
    qrng=rng(c.seed,epoch,episode,tick,'query')
    eligible=[g for g in (1,2,3) if (groups[ids]==g).sum()>=c.target_query_points and
              (groups[global_ids]!=g).sum()>=c.condition_points+c.query_points-c.target_query_points]
    target=int(qrng.choice(eligible)) if eligible else 0
    if target:
        target_ids=ids[groups[ids]==target]
        q_target=spread(target_ids,np.asarray(candidates['xyz']),np.asarray(candidates['part']),c.target_query_points,qrng)
        other=global_ids[groups[global_ids]!=target]
        q_other=stratified(other,cells,c.query_points-c.target_query_points,qrng)
        query=np.concatenate((q_target,q_other))
        qrng.shuffle(query)
    else:
        query=stratified(global_ids,cells,c.query_points,qrng)
    available=global_ids[~np.isin(global_ids,query)]
    scene=stratified(available,cells,c.condition_points,rng(c.seed,epoch,episode,tick,'condition'))
    holdout=c.mode=='holdout' or (c.mode=='mixed' and rng(c.seed,epoch,episode,tick,'mode').random()<c.holdout_probability)
    holdout=bool(holdout and target)
    condition=scene.copy();removed=(groups[scene]==target) if holdout else np.zeros(len(scene),bool)
    if removed.any():
        refill=available[(groups[available]!=target)&~np.isin(available,scene[~removed])]
        condition[removed]=stratified(refill,cells,int(removed.sum()),rng(c.seed,epoch,episode,tick,'refill'))
    assert len(np.unique(np.concatenate((condition,query))))==c.condition_points+c.query_points
    assert not holdout or not (groups[condition]==target).any()
    return dict(condition=condition,query=query,scene_condition=scene,target_group=target,
                mode='holdout' if holdout else 'scene',fallback=not bool(target),
                removed=int(removed.sum()),scene_hits_target=int((groups[scene]==target).sum()) if target else 0)


def material_tracks(local,body,poses,ticks):
    """Point-major world positions from per-tick rigid-link poses, no occlusion mask."""
    transforms=poses[np.asarray(ticks)[:,None],np.asarray(body)[None]]
    return (np.einsum('tnij,nj->nti',transforms[...,:3,:3],local)+transforms[...,:3,3].transpose(1,0,2)).astype(np.float32)
