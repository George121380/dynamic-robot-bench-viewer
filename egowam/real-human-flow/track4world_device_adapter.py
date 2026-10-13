"""Published Track4World/DA3: current-frame queries and observed-history replay.

The native 3D head is preserved. Camera poses express its endpoints in one
reference camera frame. No measured scale, VIO, smoothing or GT is supplied.
"""
import argparse
import gc
import hashlib
import inspect
import json
import math
import re
import sys
import time
import types
import textwrap
from pathlib import Path

import numpy as np


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(2**20), b''): h.update(b)
    return h.hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def load_model(source, checkpoint, device):
    import torch
    sys.path[:0] = [str(source), str(source.parent)]
    # These optional exports/externally supplied pose alignment are not invoked
    # by inference_v2. Avoid loading their rendering/colmap dependencies.
    def unavailable(*a, **kw):
        raise RuntimeError('optional export/input-pose alignment is disabled')
    for name, member in [('depth_anything_3.utils.export', 'export'),
                         ('depth_anything_3.utils.pose_align', 'align_poses_umeyama')]:
        module = types.ModuleType(name);setattr(module, member, unavailable)
        if member=='align_poses_umeyama':module.batch_align_poses_umeyama=unavailable
        sys.modules[name] = module
    for name,member in [('track4world.nets.external.pi3.models.pi3','Pi3'),
                        ('track4world.nets.external.pi3x.models.pi3x','Pi3X')]:
        module=types.ModuleType(name)
        class DisabledBackbone:
            def __init__(self,*a,**kw):raise RuntimeError('This trial selects only the official DA3 backbone')
            @classmethod
            def from_pretrained(cls,*a,**kw):raise RuntimeError('Alternate backbone is disabled in the DA3 trial')
        setattr(module,member,DisabledBackbone);sys.modules[name]=module
    import track4world.nets.model as upstream
    cpu_precision=None
    if device=='cpu':
        api_module=sys.modules[upstream.DepthAnything3.__module__]
        api_source=textwrap.dedent(inspect.getsource(upstream.DepthAnything3.forward))
        assert 'autocast_dtype = torch.float16' in api_source
        api_source=api_source.replace('autocast_dtype = torch.float16',
            "autocast_dtype = torch.bfloat16 if image.device.type == 'cpu' else torch.float16")
        namespace=dict(api_module.__dict__)
        exec(compile(api_source,api_module.__file__,'exec'),namespace)
        upstream.DepthAnything3.forward=namespace['forward']
        cpu_precision=hashlib.sha256(api_source.encode()).hexdigest()
    # Published Track4World contains the complete single DA3-Giant backbone.
    # Build its architecture once, then require a strict complete weight load.
    original = upstream.DepthAnything3.from_pretrained
    upstream.DepthAnything3.from_pretrained = lambda *a, **kw: upstream.DepthAnything3('da3-giant')
    code = Path(upstream.__file__).read_text()
    adaptation = None
    if device != 'cuda':
        code = code.replace('.cuda()', '.to(_execution_device)')
        code = re.sub(r"device=(['\"])cuda(?::0)?\1", f"device='{device}'", code)
        code = re.sub(r"device_type=(['\"])cuda\1", f"device_type='{device}'", code)
        if device=='cpu':
            code=code.replace('dtype=torch.float16)', 'dtype=torch.bfloat16)')
        upstream.__dict__['_execution_device'] = torch.device(device)
        if device=='mps':
            import torch.nn.functional as F
            original_interpolate=F.interpolate
            original_pool=F.adaptive_avg_pool2d
            def portable_pool(input,output_size):
                if input.device.type=='mps':
                    return original_pool(input.cpu(),output_size).to(input.device)
                return original_pool(input,output_size)
            F.adaptive_avg_pool2d=portable_pool
            original_attention=F.scaled_dot_product_attention
            def portable_attention(q,k,v,*a,**kw):
                if q.device.type=='mps' and q.shape[-1]<32:
                    dim=q.shape[-1];vdim=v.shape[-1]
                    # Zero padding preserves QK^T and V exactly. Explicit
                    # scale retains the trained head dimension, while allowing
                    # MPS's supported attention kernel to avoid the N^2 buffer.
                    q=F.pad(q,(0,64-dim));k=F.pad(k,(0,64-dim));v=F.pad(v,(0,64-vdim))
                    kw['scale']=kw.get('scale') or dim**-.5
                    return original_attention(q,k,v,*a,**kw)[...,:vdim]
                return original_attention(q,k,v,*a,**kw)
            F.scaled_dot_product_attention=portable_attention
            def portable_interpolate(input,*a,**kw):
                # Same PyTorch area operator on CPU for the MPS kernel's
                # unsupported non-divisible sizes; never substitute bilinear.
                mode=kw.get('mode',a[2] if len(a)>2 else 'nearest')
                if input.device.type=='mps' and mode=='area':
                    return original_interpolate(input.cpu(),*a,**kw).to(input.device)
                return original_interpolate(input,*a,**kw)
            upstream.__dict__['_portable_interpolate']=portable_interpolate
            code=code.replace('F.interpolate(', '_portable_interpolate(')
        exec(compile(code, upstream.__file__, 'exec'), upstream.__dict__)
        adaptation = hashlib.sha256(code.encode()).hexdigest()
    config = json.loads((source/'track4world/config/eval/v1.json').read_text())
    try:
        model = upstream.Track4World(**config['model'], seqlen=16,
                                    use_3d=True, use_model='depthanythingv3')
    finally:
        upstream.DepthAnything3.from_pretrained = original
    weights = torch.load(checkpoint, map_location='cpu', weights_only=True, mmap=True)
    matched = model.load_state_dict(weights, strict=True, assign=True)
    print('STRICT WEIGHTS', matched, flush=True)
    del weights;gc.collect()
    model.eval().to(device)
    for p in model.parameters(): p.requires_grad_(False)
    return model, {'strict_weights': str(matched),
                   'upstream_model_sha256': sha(upstream.__file__),
                   'device_adapter_sha256': adaptation,
                   'CPU_frontend_precision': 'BF16 autocast; native FP32 geometry heads' if device=='cpu' else None,
                   'CPU_frontend_adapter_sha256':cpu_precision,
                   'MPS_area_pooling': 'same PyTorch operator on CPU' if device=='mps' else None,
                   'MPS_attention': 'zero-pad short Q/K/V heads to 64; preserve original attention scale' if device=='mps' else None}


def run(args):
    import cv2
    import torch
    import torch.nn.functional as F
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    if args.device == 'mps': torch.mps.set_per_process_memory_fraction(.65)
    args.output.mkdir(parents=True, exist_ok=True)
    model, loading = load_model(args.source.resolve(), args.checkpoint, args.device)
    checkpoint_sha = sha(args.checkpoint)
    warmup = None
    for folder in args.inputs:
        out = args.output/folder.name;out.mkdir(exist_ok=True)
        if (out/'status.json').exists(): continue
        data = dict(np.load(folder/'input.npz'))
        selection = np.arange(len(data['rgb']))
        if args.tail: selection = selection[-args.tail:]
        images = data['rgb'][selection]
        queries = data['queries'][:, 1:].copy()
        T,H,W = images.shape[:3]
        ratio = args.short_side/min(H,W)
        nh,nw = [int(round(v*ratio/8)*8) for v in [H,W]]
        resized = np.stack([cv2.resize(im, (nw,nh), interpolation=cv2.INTER_LINEAR) for im in images[::-1]])
        q = (queries+.5)*[nw/W,nh/H]-.5
        video = torch.from_numpy(resized).permute(0,3,1,2)[None].float().to(args.device)
        def sync():
            if args.device == 'cuda': torch.cuda.synchronize()
            elif args.device == 'mps': torch.mps.synchronize()
        # Save the geometry's own intrinsics; no per-frame independent MoGe.
        backbone_forward = model.backbone.inference_v2
        captures = []
        def capture(*a, **kw):
            result = backbone_forward(*a, **kw)
            captures.append({k: result[k].detach().float().cpu().numpy()
                             for k in ['intrinsics', 'extrinsics']})
            return result
        model.backbone.inference_v2 = capture
        with torch.inference_mode(),torch.autocast(device_type=args.device,dtype=torch.float16,enabled=args.device!='cpu'):
            if warmup is None:
                sync();start = time.perf_counter()
                model.forward_sliding(video[:,:2],iters=4,is_training=False,tracking3d=True)
                sync();warmup=time.perf_counter()-start
                captures.clear()
                print('WARMUP', warmup, flush=True)
            sync();start=time.perf_counter()
            raw = model.forward_sliding(video,iters=4,is_training=False,tracking3d=True)
            sync();elapsed=time.perf_counter()-start
        model.backbone.inference_v2 = backbone_forward
        flow2, confidence, _, _, flow3, _, points, mask, _, world_points, poses = raw
        print('OUTPUT SHAPES', folder.name, [list(x.shape) for x in [flow2,confidence,flow3,points,mask,poses]], flush=True)
        assert flow2.shape[1]>=T and flow3.shape[1]>=T
        assert len(captures)==1, 'multiple geometry chunks require explicit frame alignment'
        def sample(values):
            grid=torch.tensor(q,device=values.device,dtype=values.dtype)
            grid = (grid+.5)/torch.tensor([nw,nh],device=grid.device,dtype=grid.dtype)*2-1
            grid=grid[None,None].expand(T,1,-1,-1)
            return F.grid_sample(values[:T].float(),grid.float(),align_corners=False).squeeze(2).permute(0,2,1).cpu().numpy()
        delta_uv=sample(flow2[0]);prob=sample(confidence[0])
        camera=sample(flow3[0].float().cpu()+points[:1].float().cpu())
        source_mask=sample(mask[:1].expand(T,-1,-1,-1))[...,0]
        uv=(delta_uv+q)[::-1]
        uv=(uv+.5)*[W/nw,H/nh]-.5
        camera=camera[::-1].copy();prob=prob[::-1].copy()
        c2w=poses[:T].float().cpu().numpy()[::-1].copy()
        # DA3's joint geometry has one uncalibrated scale. All native head
        # endpoints use that same scale; no fitted/GT scale is introduced.
        world=np.einsum('tij,tnj->tni',c2w[:,:3,:3],camera)+c2w[:,None,:3,3]
        reference=np.linalg.inv(c2w[-1])
        world=world@reference[:3,:3].T+reference[:3,3]
        c2w=np.einsum('ij,tjk->tik',reference,c2w)
        w2c=np.linalg.inv(c2w)
        valid=(prob[...,0]>.5)&(prob[...,1]>.5)&(source_mask[::-1]>2)
        valid &= np.isfinite(camera).all(-1)&(camera[...,2]>0)
        valid &= (uv[...,0]>=0)&(uv[...,0]<W)&(uv[...,1]>=0)&(uv[...,1]<H)
        intr=captures[0]['intrinsics'][0,:T][::-1].copy()
        # DA3 internally aligns to a 14-pixel patch grid.
        dh,dw=nh//14*14,nw//14*14
        intr[:,0]*=W/dw;intr[:,1]*=H/dh
        intr[:,0,2]+=.5*W/dw-.5;intr[:,1,2]+=.5*H/dh-.5
        cloud=world_points[0].permute(1,2,0).float().cpu().numpy()[::8,::8].reshape(-1,3)
        cloud=cloud@reference[:3,:3].T+reference[:3,3]
        colors=resized[0,::8,::8].reshape(-1,3)
        finite=np.isfinite(cloud).all(1);cloud=cloud[finite];colors=colors[finite]
        timestamps=data['timestamp'][selection]
        np.savez_compressed(out/'tracks3d.npz',uv=uv,world_xyz=world,camera_xyz=camera,
            valid=valid,probability=prob,world_to_camera=w2c,intrinsics=intr,
            timestamp=timestamps,source_index=data['source_index'][selection],
            queries=data['queries'],selection=selection,cloud=cloud,cloud_colors=colors)
        np.savez_compressed(out/'joint_geometry.npz',
            points=points[:T].permute(0,2,3,1).float().cpu().numpy()[::-1],
            confidence=mask[:T,0].float().cpu().numpy()[::-1],intrinsics=intr,
            world_to_camera=w2c,timestamp=timestamps)
        status={'method':'Track4World + DA3-Giant, native 3D head',
            'input_protocol':'reverse observed history; first reversed frame is current query frame; no t>t0',
            'input_frames':T,'input_resolution':[nh,nw],'source_resolution':[H,W],
            'requested_queries':len(q),'computation':'dense prediction sampled at fixed current query pixels',
            'checkpoint_sha256':checkpoint_sha,'device':args.device,'torch':torch.__version__,
            'model_s':elapsed,'warmup_s_reference':warmup,'iterations':4,
            'output':'native forward_sliding 3D head; no post-projection/temporal alignment/smoothing',
            'visibility_gate':'visibility >0.5 AND confidence >0.5 AND current geometry confidence >2; raw probabilities retained',
            'scale':'joint model-normalized relative scale; not measured meters',
            'pose':'joint DA3 estimated poses, reference=current-query camera; no Aria VIO',
            'valid_fraction_excluding_query':float(valid[:-1].mean()),
            'query_uv_max_error_px':float(np.max(np.linalg.norm(uv[-1]-queries,axis=-1))),
            'gt_error':None,**loading}
        write(out/'status.json',status)
        print('DONE',folder.name,json.dumps(status),flush=True)
        del raw,video;gc.collect()
        if args.device=='mps':torch.mps.empty_cache()


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--device',choices=['cuda','mps','cpu'],default='cuda')
    p.add_argument('--short-side',type=int,default=448)
    p.add_argument('--tail',type=int,default=0)
    p.add_argument('inputs',type=Path,nargs='+')
    run(p.parse_args())
