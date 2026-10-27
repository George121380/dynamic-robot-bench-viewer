"""Seeded visible-surface samplers, independent of the policy and its datasets."""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np

CONFIG = dict(schema='point-sampling-preview.v1', episode=416, frames=[255,510,765], seeds=list(range(10)),
    preview_mode='explicit selection; no training mixture is executed',
    proposed_training_mode_weights={'scene':.5,'object_holdout':.5},
    scene=dict(condition_points=12,query_points=12,grid=[4,6],
        selectors=['stratified_random','dino_diversity'],dino_random_points=6,
        dino_feature_distance_weight=.75,dino_spatial_distance_weight=.25),
    object_holdout=dict(points_per_rigid_part=3,background_condition_points=3,
        background_selector='uniform visible static pixels without replacement',
        targets=['cube','tool','gripper'],gripper_parts=['palm','left_finger','right_finger']),
    visibility='current visible surface only',known_information='current RGB, current anchors, C history',
    units='metres',history_frames=16,future_frames=15,dt_s=.05)


class Scene:
    def __init__(self, root, frame):
        self.frame=frame
        self.meta=json.loads((root/'raw/scene.json').read_text())
        z=np.load(root/'raw'/f'frame-{frame}.npz')
        self.z={k:z[k] for k in z.files}
        self.seg=self.z['segmentation'];self.h,self.w=self.seg.shape
        self.live=self.z['valid'].ravel()
        self.xyz=self.z['xyz'].reshape(-1,3)
        self.uv=self.z['uv'].reshape(-1,2)
        self.bodies={x['id']:x for x in self.meta['bodies']}
        self.body_index={int(x):i for i,x in enumerate(self.z['body_ids'])}
        self.features=np.load(root/'raw'/f'dino-{frame}.npy')

    def ids(self,group=None,part=None):
        live=self.live.copy()
        if group is not None:
            body_ids=[i for i,b in self.bodies.items() if b['group']==group and (part is None or b['part']==part)]
            live &= np.isin(self.seg.ravel(),body_ids)
        return np.flatnonzero(live)

    def stratified(self,rng):
        selected=[]
        rows,cols=CONFIG['scene']['grid']
        live=self.live.reshape(self.h,self.w)
        for r in range(rows):
            for c in range(cols):
                y0,y1=r*self.h//rows,(r+1)*self.h//rows
                x0,x1=c*self.w//cols,(c+1)*self.w//cols
                yy,xx=np.nonzero(live[y0:y1,x0:x1])
                if len(yy):
                    i=int(rng.integers(len(yy)))
                    selected.append((int(yy[i])+y0)*self.w+int(xx[i])+x0)
        total=CONFIG['scene']['condition_points']+CONFIG['scene']['query_points']
        assert rows*cols==total, 'Grid must match the preview point budget'
        if len(selected)<total:
            rest=np.setdiff1d(self.ids(),selected)
            selected.extend(rng.choice(rest,total-len(selected),replace=False).tolist())
        assert len(selected)==total
        return np.asarray(selected,dtype=np.int64)

    def feature_ids(self,ids):
        y=ids//self.w;x=ids%self.w
        return np.minimum(y*16//self.h,15)*16+np.minimum(x*16//self.w,15)

    def dino_diversity(self,rng):
        config=CONFIG['scene']
        selected=rng.permutation(self.stratified(rng))[:config['dino_random_points']].tolist()
        candidates=[]
        live=self.live.reshape(self.h,self.w)
        for r in range(16):
            for c in range(16):
                y0,y1=r*self.h//16,(r+1)*self.h//16
                x0,x1=c*self.w//16,(c+1)*self.w//16
                yy,xx=np.nonzero(live[y0:y1,x0:x1])
                if len(yy):
                    j=int(rng.integers(len(yy)))
                    candidates.append((int(yy[j])+y0)*self.w+int(xx[j])+x0)
        cand=np.asarray(candidates,dtype=np.int64)
        feat=self.features[self.feature_ids(cand)]
        uv=self.uv[cand]/np.array([self.w,self.h])
        distance=np.full(len(cand),np.inf)
        def update(idx):
            f=self.features[self.feature_ids(np.asarray([idx]))[0]]
            d=config['dino_feature_distance_weight']*np.clip((1-feat@f)/2,0,1)+config['dino_spatial_distance_weight']*((uv-self.uv[idx]/[self.w,self.h])**2).sum(-1)/2
            np.minimum(distance,d,out=distance)
            distance[np.isin(cand,selected)]=-np.inf
        for idx in selected:update(idx)
        while len(selected)<config['condition_points']+config['query_points']:
            j=int(distance.argmax());assert np.isfinite(distance[j])
            selected.append(int(cand[j]));update(int(cand[j]))
        return np.asarray(selected,dtype=np.int64)

    def spread(self,ids,rng,count=3):
        if len(ids)<=count:return ids.copy()
        xyz=self.xyz[ids].astype(np.float64)
        first=int(rng.integers(len(ids)));selected=[first]
        dist=((xyz-xyz[first])**2).sum(-1);second=int(dist.argmax());selected.append(second)
        if count>=3:
            areas=np.linalg.norm(np.cross(xyz[second]-xyz[first],xyz-xyz[first]),axis=-1)
            areas[selected]=-1
            if areas.max()>1e-12:selected.append(int(areas.argmax()))
        return ids[selected[:count]]

    def choose(self,mode,seed):
        rng=np.random.default_rng(seed)
        if mode in ('random','dino'):
            ids=self.stratified(rng) if mode=='random' else self.dino_diversity(rng)
            ids=rng.permutation(ids)
            n=CONFIG['scene']['condition_points']
            return ids[:n],ids[n:]
        target=mode.split(':')[1]
        sets={}
        for group in ('cube','tool','gripper'):
            parts=CONFIG['object_holdout']['gripper_parts'] if group=='gripper' else [group]
            sets[group]=np.concatenate([self.spread(self.ids(group,part),rng,CONFIG['object_holdout']['points_per_rigid_part']) for part in parts])
        background=self.ids('background')
        background=rng.choice(background,min(len(background),CONFIG['object_holdout']['background_condition_points']),replace=False)
        c=np.concatenate([sets[g] for g in sets if g!=target]+[background])
        return c,sets[target]

    def project(self,xyz):
        e=self.z['extrinsic_cv'];k=self.z['intrinsic_cv']
        cv=xyz@e[:3,:3].T+e[:3,3];p=cv@k.T
        return p[:,:2]/p[:,2:]

    def point(self,idx,role):
        sid=int(self.seg.ravel()[idx]);body=self.bodies[sid];bi=self.body_index[sid]
        transforms=self.z['body_poses'][:,bi].astype(np.float64)
        p=self.xyz[idx].astype(np.float64)
        local=(p-transforms[15,:3,3])@transforms[15,:3,:3]
        track=np.einsum('tij,j->ti',transforms[:,:3,:3],local)+transforms[:,:3,3]
        assert np.max(np.abs(track[15]-p))<1e-5
        return dict(pixel_id=int(idx),body_id=sid,entity=body['group'],part=body['part'],role=role,
            uv=np.round(self.uv[idx],5).tolist(),xyz_m=np.round(p,8).tolist(),
            local_xyz_m=np.round(local,8).tolist(),
            history_uv=np.round(self.project(track[:16]),4).tolist(),
            history_xyz_m=np.round(track[:16],8).tolist(),future_xyz_m=np.round(track[16:],8).tolist())

    def outlines(self,group):
        ids=[i for i,b in self.bodies.items() if b['group']==group]
        mask=np.isin(self.seg,ids).astype(np.uint8)
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        return [cv2.approxPolyDP(c,.7,True)[:,0].tolist() for c in contours if cv2.contourArea(c)>=1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
    output=dict(config=CONFIG,frames=[],samples={})
    verification=dict(same_seed_reproducible=True,different_seed_changes=True,no_cq_overlap=True,
        visible_points_only=True,whole_entity_exclusion=True,gripper_parts_grouped=True,
        history_anchor_roundtrip=True,sample_sets=0,points=0,by_frame={})
    for frame in CONFIG['frames']:
        scene=Scene(root,frame)
        entry=dict(id=frame,time_s=frame*.05,width=scene.w,height=scene.h,
            image=f'frame-{frame}.png',outlines={g:scene.outlines(g) for g in ('cube','tool','gripper')})
        output['frames'].append(entry)
        modes=['random','dino']+['holdout:'+g for g in ('cube','tool','gripper')]
        verification['by_frame'][str(frame)]={}
        for mode in modes:
            fingerprints=[];counts=[]
            for seed in CONFIG['seeds']:
                c,q=scene.choose(mode,seed);c2,q2=scene.choose(mode,seed)
                assert np.array_equal(c,c2) and np.array_equal(q,q2)
                assert len(set(c.tolist()+q.tolist()))==len(c)+len(q)
                assert scene.live[np.r_[c,q]].all()
                if mode.startswith('holdout:'):
                    target=mode.split(':')[1]
                    assert all(scene.bodies[int(scene.seg.ravel()[x])]['group']!=target for x in c)
                    assert all(scene.bodies[int(scene.seg.ravel()[x])]['group']==target for x in q)
                pts=[scene.point(int(x),'C') for x in c]+[scene.point(int(x),'Q') for x in q]
                key=f'{frame}/{mode}/{seed}'
                output['samples'][key]=dict(frame=frame,mode=mode,seed=seed,c_count=len(c),q_count=len(q),points=pts)
                fingerprints.append(hashlib.sha256(np.r_[c,q].tobytes()).hexdigest())
                counts.append([len(c),len(q)])
                verification['points']+=len(pts);verification['sample_sets']+=1
            assert len(set(fingerprints))>1, (frame,mode)
            verification['by_frame'][str(frame)][mode]=dict(counts=counts,unique_seed_results=len(set(fingerprints)))
    (root/'public/samples.json').write_text(json.dumps(output,separators=(',',':'))+'\n')
    (root/'public/sampling-config.json').write_text(json.dumps(CONFIG,indent=2)+'\n')
    (root/'qa/sampling-verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps({k:v for k,v in verification.items() if k!='by_frame'},indent=2))


if __name__=='__main__':main()
