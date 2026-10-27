"""Visible current-frame candidates and oracle material tracking, at 512 pixels.

The extra camera shares the official camera pose/FOV. It does not replace the
128-pixel policy camera or advance physics. Each articulated link has its own pose.
"""
import copy
import numpy as np
from four_d_mae.scene_sampling import rng

CAPACITY=352


def array(value):
    return value.detach().cpu().numpy() if hasattr(value,'detach') else np.asarray(value)


class SceneGeometry:
    def __init__(self,env):
        from mani_skill.sensors.camera import Camera
        self.base=env.unwrapped
        config=copy.copy(self.base._sensors['base_camera'].config)
        config.uid='motion_geometry';config.width=config.height=512
        if config.intrinsic is not None:
            config.intrinsic=np.array(config.intrinsic,copy=True)
            config.intrinsic[:2]*=4
        self.camera=Camera(config,self.base.scene)
        self.refresh_bodies()

    def refresh_bodies(self):
        entries=[]
        for name,obj in self.base.scene.actors.items():
            group={'cube':1,'l_shape_tool':2}.get(name,0)
            entries.append((name,int(obj._objs[0].per_scene_id),group,group,obj))
        for link in self.base.agent.robot.get_links():
            name=link.name
            part=(4 if name.startswith('panda_leftfinger') else 5 if name.startswith('panda_rightfinger')
                  else 3 if name.startswith('panda_hand') else 0)
            entries.append((name,int(link._objs[0].entity.per_scene_id),3 if part else 0,part,link))
        entries.sort(key=lambda x:x[0]);self.entries=entries
        self.bodies=[dict(name=n,segmentation_id=s,group=g,part=p) for n,s,g,p,_ in entries]
        self.ids=np.array([s for _,s,_,_,_ in entries])
        self.groups=np.array([g for _,_,g,_,_ in entries],np.uint8)
        self.parts=np.array([p for _,_,_,p,_ in entries],np.uint8)

    def poses(self):
        return np.stack([array(obj.pose.to_transformation_matrix())[0] for *_,obj in self.entries]).astype(np.float32)

    def candidates(self,*,episode,tick,seed=42):
        self.base.scene.update_render();self.camera.capture()
        raw=self.camera.get_obs(rgb=False,depth=False,position=True,segmentation=True,apply_texture_transforms=False)
        pos=array(raw['Position'])[0,:,:,:3].astype(np.float32)
        seg=array(raw['Segmentation'])[0,:,:,1].astype(np.int32)
        params={k:array(v)[0] for k,v in self.camera.get_params().items()}
        live=(seg!=0)&(pos[:,:,2]<-.01)&np.isfinite(pos).all(-1)
        unknown=set(np.unique(seg[live]))-set(self.ids)
        if unknown:raise ValueError('Unmapped visible body IDs: '+str(unknown))
        h,w=seg.shape;yy,xx=np.indices((h,w));cell=(yy*4//h)*6+xx*6//w
        generator=rng(seed,0,episode,tick,'candidate_pool');chosen=[]
        for c in range(24):
            pool=np.flatnonzero(live&(cell==c))
            chosen.extend(generator.choice(pool,min(8,len(pool)),replace=False).tolist())
        global_count=len(chosen)
        # Supplemental candidates do not change the global C / non-target Q law.
        for part in (1,2,3,4,5):
            sids=self.ids[self.parts==part]
            pool=np.flatnonzero(live&np.isin(seg,sids))
            pool=pool[~np.isin(pool,chosen)]
            chosen.extend(generator.choice(pool,min(32,len(pool)),replace=False).tolist())
        pixel=np.asarray(chosen,np.int32);n=len(pixel)
        if n>CAPACITY:raise AssertionError(n)
        body=np.array([{s:i for i,s in enumerate(self.ids)}[s] for s in seg.ravel()[pixel]],np.int16)
        point=pos.reshape(-1,3)[pixel]
        xyz=point@params['cam2world_gl'][:3,:3].T+params['cam2world_gl'][:3,3]
        poses=self.poses();r=poses[body,:3,:3];translation=poses[body,:3,3]
        local=np.einsum('ni,nij->nj',xyz-translation,r).astype(np.float32)
        result=dict(pixel=np.full(CAPACITY,-1,np.int32),body=np.zeros(CAPACITY,np.int16),
                    local=np.zeros((CAPACITY,3),np.float32),cell=np.zeros(CAPACITY,np.uint8),
                    global_pool=np.zeros(CAPACITY,bool))
        result['pixel'][:n]=pixel;result['body'][:n]=body;result['local'][:n]=local
        result['cell'][:n]=cell.ravel()[pixel];result['global_pool'][:global_count]=True
        # Check the camera convention on the actual selected material anchors.
        cv=xyz@params['extrinsic_cv'][:3,:3].T+params['extrinsic_cv'][:3,3]
        uv=(cv@params['intrinsic_cv'].T);uv=uv[:,:2]/uv[:,2:]
        residual=uv-np.stack((pixel%w,pixel//w),-1)
        projection_error=float(np.abs(residual-np.median(residual,0)).max())
        if projection_error>.03:raise ValueError('Geometry projection mismatch')
        return result,dict(candidates=n,global_candidates=global_count,projection_error_px=projection_error),params

    def unpack(self,candidates,poses=None):
        poses=self.poses() if poses is None else poses
        body=candidates['body'];local=candidates['local']
        xyz=np.einsum('nij,nj->ni',poses[body,:3,:3],local)+poses[body,:3,3]
        return dict(candidates,xyz=xyz,group=self.groups[body],part=self.parts[body],**{'global':candidates['global_pool']})


class SceneHistory:
    """Observe link poses each control tick; sample current geometry at replanning."""
    def __init__(self,env,sampling,episode):
        from four_d_mae.scene_sampling import SamplingConfig
        self.geometry=SceneGeometry(env);self.episode=episode;self.tick=-1;self.buffer=[]
        self.sampling=SamplingConfig(**{**sampling,'mode':'scene'})

    def observe(self):
        self.tick+=1;self.buffer.append(self.geometry.poses())
        self.buffer=self.buffer[-16:]

    def observation(self):
        from four_d_mae.scene_sampling import sample_points,material_tracks
        raw,_,_=self.geometry.candidates(episode=self.episode,tick=self.tick)
        c=self.geometry.unpack(raw,self.buffer[-1])
        s=sample_points(c,self.sampling,episode=self.episode,tick=self.tick)
        ids=s['condition'];poses=np.stack(self.buffer);n=len(poses)
        xyz=material_tracks(c['local'][ids],c['body'][ids],poses,np.arange(n))
        history=np.zeros((len(ids),16,3),np.float32);valid=np.zeros((len(ids),16),bool)
        history[:,-n:]=xyz;valid[:,-n:]=True
        return dict(history_xyz=history,history_valid=valid)
