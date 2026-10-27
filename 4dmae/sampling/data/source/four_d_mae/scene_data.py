"""Original RGB/actions with stateless sparse material tracks from geometry sidecars."""
import bisect
from collections import OrderedDict
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset
from .data import WindowDataset,validate_batch,sha256
from .scene_sampling import SamplingConfig,sample_points,material_tracks

GEOMETRY_FIELDS=('pixel','body','local','cell','global_pool','poses')


class SceneDataset(Dataset):
    epoch_keys=True

    def __init__(self,manifest,split,policy,sampling=None):
        self.path=Path(manifest).resolve();self.split=split;self.policy=policy
        self.sampling=SamplingConfig(**(sampling or {}));self.cache=OrderedDict()
        c=policy.get('model',{})
        if policy['name'] not in ('4dmae','egowam') or c.get('arm','B5') not in ('B3','B4','B5','G'):
            raise ValueError('Scene data is an explicit history-policy experiment')
        if (c.get('history',16)!=16 or c.get('input_points',64)!=self.sampling.condition_points or
                c.get('query_points',64)!=self.sampling.query_points):
            raise ValueError('Scene sampling and model point/history counts differ')
        base_policy=dict(name='egowam',model={**c,'arm':'B0'})
        self.base=WindowDataset(manifest,split,base_policy,schema='4dmae.scene_windows.v1')
        self.manifest=self.base.manifest;self.ends=self.base.ends
        meta=self.manifest['metadata']
        if meta.get('coordinate_frame')!='world' or meta.get('coordinate_units')!='m':raise ValueError('Scene frame must be world metres')
        if meta.get('history_offsets_s')!=[round(i*.05,8) for i in range(-15,1)]:raise ValueError('Wrong scene history times')
        if meta.get('future_offsets_s')!=[round(i*.05,8) for i in range(1,16)]:raise ValueError('Wrong scene future times')
        self.rows=self.manifest['splits'][split]
        self.folders=[(self.path.parent/r['path']).resolve() for r in self.rows]
        if any(not f.is_relative_to(self.path.parent) for f in self.folders):raise ValueError('Geometry path escapes dataset')
        o,t=self[0];validate_batch({k:v[None] for k,v in o.items()},{k:v[None] for k,v in t.items()},policy)

    def __len__(self):return len(self.base)

    def __getstate__(self):return {**self.__dict__,'cache':OrderedDict()}

    def geometry(self,part):
        if part in self.cache:
            value=self.cache.pop(part);self.cache[part]=value;return value
        folder=self.folders[part];value={k:np.load(folder/(k+'.npy'),mmap_mode='r',allow_pickle=False) for k in GEOMETRY_FIELDS}
        bodies=json.loads((folder/'bodies.json').read_text())
        value['groups']=np.array([b['group'] for b in bodies],np.uint8);value['parts']=np.array([b['part'] for b in bodies],np.uint8)
        expected=self.ends[part]-(self.ends[part-1] if part else 0)
        if any(len(value[k])!=expected for k in GEOMETRY_FIELDS if k!='poses'):raise ValueError('Geometry window count differs')
        if len(value['poses'])<expected+15:raise ValueError('Missing future rigid poses')
        self.cache[part]=value
        # Keep only mmap handles, not copies. A tiny LRU would reopen thousands
        # of PFS files per optimizer step under uniformly shuffled windows.
        return value

    def selection(self,index,epoch=0,mode=None):
        part=bisect.bisect_right(self.ends,index);tick=index-(self.ends[part-1] if part else 0)
        geo=self.geometry(part);body=geo['body'][tick];local=geo['local'][tick]
        poses=geo['poses'][tick]
        candidate={k:geo[k][tick] for k in GEOMETRY_FIELDS if k!='poses'}
        candidate.update(xyz=np.einsum('nij,nj->ni',poses[body,:3,:3],local)+poses[body,:3,3],
                         group=geo['groups'][body],part=geo['parts'][body],**{'global':candidate['global_pool']})
        episode=self.rows[part]['episode_ids'][0]
        sampling=replace(self.sampling,mode=mode) if mode is not None else self.sampling
        selected=sample_points(candidate,sampling,epoch=epoch if self.split=='train' else 0,episode=episode,tick=tick)
        if mode=='holdout' and selected['fallback']:
            raise ValueError('A batch-balanced holdout window has no eligible target; cannot silently break the batch ratio')
        return geo,candidate,selected,tick

    def __getitem__(self,index):
        key=index if isinstance(index,tuple) else (index,0)
        index,epoch=key[:2];mode=key[2] if len(key)>2 else None
        if not 0<=index<len(self):raise IndexError(index)
        o,t=self.base[index];geo,candidate,s,tick=self.selection(index,epoch,mode)
        ci,qi=s['condition'],s['query'];ids=np.r_[ci,qi]
        past=np.arange(tick-15,tick+1);future=np.arange(tick+1,tick+16)
        times=np.r_[np.maximum(past,0),future]
        xyz=material_tracks(candidate['local'][ids],candidate['body'][ids],geo['poses'],times)
        nc=len(ci);delta=xyz-xyz[:,15:16,:];live=np.broadcast_to(past>=0,(len(ids),16)).copy()
        history=np.where(live[:nc,:,None],xyz[:nc,:16],0).astype(np.float32)
        o.update(history_xyz=torch.from_numpy(history),history_valid=torch.from_numpy(live[:nc]))
        t.update(c_future=torch.from_numpy(delta[:nc,16:]),c_future_valid=torch.ones((nc,15),dtype=torch.bool),
            q_anchor=torch.from_numpy(xyz[nc:,15]),q_past=torch.from_numpy(np.where(live[nc:,:15,None],delta[nc:,:15],0)),
            q_past_valid=torch.from_numpy(live[nc:,:15]),q_future=torch.from_numpy(delta[nc:,16:]),
            q_future_valid=torch.ones((len(qi),15),dtype=torch.bool))
        return o,t

    def fingerprint(self):
        out=self.base.fingerprint();out['sampling']=self.sampling.to_dict()
        for folder in self.folders:
            for name in [k+'.npy' for k in GEOMETRY_FIELDS]+['bodies.json','camera.npz']:
                file=folder/name;out['files'][str(file.relative_to(self.path.parent))]=sha256(file)
        return out

    def preflight(self):
        self.base.preflight()
        for part in range(len(self.rows)):
            g=self.geometry(part);live=g['pixel']>=0
            if not np.isfinite(g['poses']).all() or not np.isfinite(g['local'][live]).all():raise ValueError('Nonfinite geometry')
            if (g['body'][live]<0).any() or (g['body'][live]>=len(g['groups'])).any():raise ValueError('Invalid rigid-body index')
            if (g['global_pool'].sum(1)<self.sampling.condition_points+self.sampling.query_points).any():raise ValueError('Too few scene candidates')
            begin=self.ends[part-1] if part else 0
            for i in (begin,(begin+self.ends[part]-1)//2,self.ends[part]-1):
                o,t=self[i];validate_batch({k:v[None] for k,v in o.items()},{k:v[None] for k,v in t.items()},self.policy)

    def statistics(self,flow_statistics_source='q_future'):
        if self.split!='train' or flow_statistics_source!='q_future':raise ValueError('Scene stats require fixed train query futures')
        self.preflight();result=self.base.statistics();count=0;total=np.zeros(3);square=np.zeros(3);low=np.full(3,np.inf);high=-low
        diagnostics=dict(windows=0,holdout=0,fallback=0,scene_hits_target=0,removed=0,targets={str(k):0 for k in range(4)})
        for index in range(len(self)):
            g,c,s,tick=self.selection(index,0);q=s['query']
            track=material_tracks(c['local'][q],c['body'][q],g['poses'],np.arange(tick+1,tick+16))
            x=(track-c['xyz'][q,None]).reshape(-1,3).astype(np.float64)
            if not np.isfinite(x).all():raise ValueError('Nonfinite scene future')
            count+=len(x);total+=x.sum(0);square+=(x*x).sum(0);low=np.minimum(low,x.min(0));high=np.maximum(high,x.max(0))
            diagnostics['windows']+=1;diagnostics['holdout']+=int(s['mode']=='holdout');diagnostics['fallback']+=int(s['fallback'])
            diagnostics['scene_hits_target']+=int(s['scene_hits_target']>0);diagnostics['removed']+=s['removed'];diagnostics['targets'][str(s['target_group'])]+=1
        mean=total/count;std=np.sqrt(np.maximum(square/count-mean*mean,0)).clip(.01)
        result.update(flow_mean=mean.tolist(),flow_std=std.tolist(),flow_min=low.tolist(),flow_max=high.tolist())
        if self.sampling.mode=='mixed' and self.sampling.batch_balance and diagnostics['fallback']:
            raise ValueError('Exact batch mixing requires an eligible target in every preserved window; review sampling-audit before training')
        self.sampling_diagnostics=diagnostics
        return result
