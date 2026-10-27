"""Frozen current-frame DINO features for point selection only."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from torchvision import transforms

REVISION = '7764ea0f912e53c92e82eb78a2a1631e92725fc8'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--prepare-only', action='store_true')
    a = p.parse_args()
    torch.set_num_threads(2)
    model = torch.hub.load('facebookresearch/dinov2:'+REVISION, 'dinov2_vits14_reg',
        trust_repo=True, skip_validation=True, pretrained=True).eval()
    model.requires_grad_(False)
    checkpoint = Path(torch.hub.get_dir())/'checkpoints/dinov2_vits14_reg4_pretrain.pth'
    evidence = dict(model='DINOv2 ViT-S/14 with registers', repository_commit=REVISION,
        checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        input_size=[224,224], patch_grid=[16,16], feature_dim=384,
        frozen=True, inputs='current RGB frame only', training_updates=0, device='cpu')
    if a.prepare_only:
        print(json.dumps(evidence),flush=True)
        return
    preprocess = transforms.Compose([transforms.Resize((224,224), interpolation=transforms.InterpolationMode.BICUBIC,
        antialias=True), transforms.ToTensor(), transforms.Normalize((.485,.456,.406),(.229,.224,.225))])
    with torch.inference_mode():
        for frame in (255,510,765):
            x = preprocess(Image.open(a.root/'raw'/f'frame-{frame}.png').convert('RGB'))[None]
            feat = model.forward_features(x)['x_norm_patchtokens'][0]
            feat = torch.nn.functional.normalize(feat,dim=-1)
            assert tuple(feat.shape) == (256,384)
            np.save(a.root/'raw'/f'dino-{frame}.npy',feat.float().numpy(),allow_pickle=False)
            print('features',frame,list(feat.shape),flush=True)
    (a.root/'qa/dino.json').write_text(json.dumps(evidence,indent=2)+'\n')


if __name__ == '__main__':
    main()
