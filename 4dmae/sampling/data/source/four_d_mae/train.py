"""CPU/CUDA/DDP trainer with explicit global batch and exact step-boundary resume."""
import contextlib
import copy
import fcntl
from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import time

import numpy as np
import torch
from torch import nn
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, Subset

from .data import open_dataset, validate_batch
from .policy import build_policy
from .loss_reduction import accumulation_scales, reduce_components


@dataclass(frozen=True)
class TrainConfig:
    steps: int = 100000
    seed: int = 42
    global_batch_size: int = 64
    accumulation_steps: int = 1
    lr: float = 1e-4
    weight_decay: float = 1e-4
    betas: tuple = (.9, .999)
    warmup_steps: int = 500
    lr_schedule: str = "cosine"
    vision_init_path: str | None = None
    vision_init_sha256: str | None = None
    flow_statistics_source: str = "all_required"
    clip_grad_norm: float = 1.
    precision: str = "float32"
    ema: bool = False
    ema_power: float = .75
    workers: int = 0
    save_every: int = 5000
    validate_every: int = 1000
    validation_samples: int = 256
    log_every: int = 10
    threads: int = 2

    def __post_init__(self):
        if self.flow_statistics_source not in ("all_required", "q_future"):
            raise ValueError("Unknown flow statistics source")
        if self.lr_schedule not in ('constant', 'cosine'):
            raise ValueError('lr_schedule must be constant or cosine')
        if bool(self.vision_init_path) != bool(self.vision_init_sha256):
            raise ValueError('Visual initialization needs both an explicit local path and SHA256')
        if self.vision_init_sha256 and (len(self.vision_init_sha256) != 64 or
                any(x not in '0123456789abcdef' for x in self.vision_init_sha256)):
            raise ValueError('Invalid visual initialization SHA256')
        for name in ("steps", "global_batch_size", "accumulation_steps", "save_every", "validate_every",
                     "validation_samples", "log_every", "threads", "workers", "warmup_steps", "seed"):
            value = getattr(self, name)
            minimum = 0 if name in ("workers", "warmup_steps", "seed") else 1
            if type(value) is not int or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        if self.seed >= 2 ** 32:
            raise ValueError("seed must be below 2**32")
        for name in ("lr", "weight_decay", "clip_grad_norm", "ema_power"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (name != "weight_decay" and value == 0):
                raise ValueError("Invalid finite optimizer setting: " + name)
        if len(self.betas) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v < 1 for v in self.betas):
            raise ValueError("Adam betas must be two finite values in [0,1)")
        if type(self.ema) is not bool:
            raise ValueError("ema must be boolean")
        if self.precision not in ("float32", "bfloat16"):
            raise ValueError("Supported precision: float32 or CUDA bfloat16")


def seed_all(seed):
    random.seed(seed); np.random.seed(seed % (2 ** 32)); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def rng_state(device):
    n = np.random.get_state()
    return {"python": random.getstate(), "numpy": [n[0], n[1].tolist(), n[2], n[3], n[4]],
            "torch": torch.get_rng_state(),
            "cuda": torch.cuda.get_rng_state(device) if device.type == "cuda" else None}


def restore_rng(state, device):
    random.setstate(state["python"])
    n = state["numpy"]
    np.random.set_state((n[0], np.asarray(n[1], dtype=np.uint32), n[2], n[3], n[4]))
    torch.set_rng_state(state["torch"])
    if state["cuda"] is not None:
        torch.cuda.set_rng_state(state["cuda"], device)


def move(batch, device):
    if isinstance(batch, dict):
        return {k: move(v, device) for k, v in batch.items()}
    if isinstance(batch, (tuple, list)):
        return type(batch)(move(v, device) for v in batch)
    return batch.to(device, non_blocking=True)


def atomic_save(value, path):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    torch.save(value, temp)
    os.replace(temp, path)


def code_fingerprint():
    root = Path(__file__).parent
    digest = hashlib.sha256()
    for file in sorted(root.rglob("*.py")):
        digest.update(str(file.relative_to(root)).encode()); digest.update(file.read_bytes())
    return digest.hexdigest()


class GlobalBatchSampler:
    """One deterministic global permutation; checkpoint step determines the cursor.

    Only the final incomplete global batch of an epoch is dropped. Loader workers
    perform no randomness; their prefetch therefore cannot change resumed samples.
    """
    def __init__(self, size, config, world=1, rank=0, start=0, end=None, *, epoch_keys=False, sampling=None):
        self.size, self.c, self.world, self.rank, self.start = size, config, world, rank, start
        self.epoch_keys=epoch_keys
        self.sampling=sampling
        self.end = config.steps if end is None else end
        self.per_epoch = size // config.global_batch_size
        divisor = world * config.accumulation_steps
        if not self.per_epoch or config.global_batch_size % divisor:
            raise ValueError("Dataset must cover a global batch; global batch must divide world_size * accumulation_steps")
        self.micro = config.global_batch_size // divisor

    def __len__(self):
        return (self.end - self.start) * self.c.accumulation_steps

    def __iter__(self):
        epoch, permutation = None, None
        local = self.micro * self.c.accumulation_steps
        for step in range(self.start, self.end):
            current = step // self.per_epoch
            if epoch != current:
                epoch = current
                permutation = torch.randperm(self.size, generator=torch.Generator().manual_seed(self.c.seed + epoch)).tolist()
            offset = (step % self.per_epoch) * self.c.global_batch_size + self.rank * local
            for microstep in range(self.c.accumulation_steps):
                begin = offset + microstep * self.micro
                indices=permutation[begin:begin + self.micro]
                if self.epoch_keys and self.sampling and self.sampling.get('mode')=='mixed' and self.sampling.get('batch_balance',True):
                    size=self.c.global_batch_size
                    n=int(round(size*self.sampling.get('holdout_probability',.5)))
                    positions=range(begin%size,begin%size+len(indices))
                    modes=['holdout' if (j+1)*n//size>j*n//size else 'scene' for j in positions]
                    yield [(i,epoch,m) for i,m in zip(indices,modes)]
                else:
                    yield [(i,epoch) for i in indices] if self.epoch_keys else indices


class LossModule(nn.Module):
    def __init__(self, policy, config=None):
        super().__init__(); self.policy = policy; self.config = config

    def forward(self, observation, targets, scales=None):
        losses = self.policy.compute_loss(observation, targets)
        return losses if scales is None else reduce_components(losses, scales, self.config)


def training_statistics(dataset, policy, source, identity):
    """Reuse a completed full-data audit only under exact content/code identity."""
    cache_path=dataset.path.parent/'statistics-cache.json'
    if cache_path.exists():
        cache=json.loads(cache_path.read_text())
        key=dict(data=identity['train'],code=identity['code'],policy=policy,flow_source=source)
        if cache.get('key')==key:
            digest=hashlib.sha256(json.dumps(cache['statistics'],sort_keys=True).encode()).hexdigest()
            if cache.get('statistics_sha256')!=digest:raise ValueError('Corrupt precomputed statistics')
            if hasattr(dataset,'sampling'):
                dataset.sampling_diagnostics=cache['sampling_diagnostics']
            return cache['statistics']
    return dataset.statistics(source)


class EMA:
    """DP's warmup decay, plus explicit buffer copies for non-DP backbones."""
    def __init__(self, policy, power):
        self.model = copy.deepcopy(policy).eval().requires_grad_(False)
        self.step_count = 0
        self.power = power

    @torch.no_grad()
    def update(self, policy):
        step = max(0, self.step_count - 1)
        decay = min(.9999, 1 - (1 + step) ** -self.power) if step > 0 else 0.
        for a, b in zip(self.model.parameters(), policy.parameters()):
            if b.requires_grad:
                a.mul_(decay).add_(b, alpha=1 - decay)
            else:
                a.copy_(b)
        for a, b in zip(self.model.buffers(), policy.buffers()):
            a.copy_(b)
        self.step_count += 1


@torch.no_grad()
def validate(policy, dataset, config, device, seed, samples):
    # Report fixed-seed offline action error. This is not a task success estimate.
    state = rng_state(device)
    was_training = policy.training
    cudnn_tf32=torch.backends.cudnn.allow_tf32
    torch.backends.cudnn.allow_tf32=False
    policy.eval(); seed_all(seed)
    ids = np.linspace(0, len(dataset) - 1, min(samples, len(dataset)), dtype=int).tolist()
    loader = DataLoader(Subset(dataset, ids), batch_size=min(16, len(ids)), num_workers=0,
                        generator=torch.Generator().manual_seed(seed))
    error, count = 0., 0
    try:
        for observation, targets in loader:
            validate_batch(observation, targets, config)
            observation, targets = move((observation, targets), device)
            prediction = policy.predict_action(observation)
            valid = targets["action_valid"]
            squared = torch.where(valid[..., None], (prediction - targets["action"]).float().square(), 0.)
            if not torch.isfinite(squared).all():
                raise ValueError("Nonfinite validation prediction")
            error += squared.sum().item(); count += valid.sum().item() * prediction.shape[-1]
    finally:
        torch.backends.cudnn.allow_tf32=cudnn_tf32
        policy.train(was_training); restore_rng(state, device)
    return {"validation_action_mse": error / max(count, 1), "validation_windows": len(ids)}


@contextlib.contextmanager
def run_directory(output, resume):
    """Only rank zero owns files; a nonblocking lifetime lock rejects two writers."""
    if int(os.environ.get("RANK", 0)) != 0:
        yield
        return
    output = Path(output)
    if resume is None:
        output.mkdir(parents=True, exist_ok=False)
    elif not (output / "run.json").exists():
        raise ValueError("Resume requires the original run directory")
    with (output / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Run directory is already in use") from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def reconcile_resume_output(output, step):
    """Reject rollback over exports; archive metrics written after the checkpoint."""
    if any(int(path.stem.split("-")[-1]) > step for path in output.glob("policy-*.pt")):
        raise ValueError("Refusing to resume an older checkpoint over newer policy exports")
    log = output / "metrics.jsonl"
    if log.exists():
        original = log.read_bytes()
        retained = []
        for line in original.splitlines(keepends=True):
            try:
                record = json.loads(line)
                if record["step"] <= step:
                    retained.append(line if line.endswith(b"\n") else line + b"\n")
            except (ValueError, KeyError, TypeError):
                pass  # A crash can leave a partial final line; preserve it in the archive.
        content = b"".join(retained)
        if content != original:
            (output / f"metrics-before-resume-{time.time_ns()}.jsonl").write_bytes(original)
            temporary = output / "metrics.jsonl.tmp"
            temporary.write_bytes(content)
            os.replace(temporary, log)


def run(config, data, output, *, device="auto", resume=None, stop_after=None):
    TrainConfig(**config.get("training", {}))
    with run_directory(output, resume):
        try:
            return _run(config, data, output, device=device, resume=resume, stop_after=stop_after)
        finally:
            if dist.is_initialized():
                dist.destroy_process_group()


def _run(config, data, output, *, device="auto", resume=None, stop_after=None):
    if not config.keys() <= {"policy", "training", "sampling"} or not config["policy"].keys() <= {"name", "model"}:
        raise ValueError("Unknown recipe fields")
    c = TrainConfig(**config.get("training", {}))
    if stop_after is not None and stop_after < 1:
        raise ValueError("stop_after must be positive")
    sampling=config.get('sampling')
    config = {"policy": config["policy"], "training": json.loads(json.dumps(asdict(c)))}
    if sampling is not None:
        from .scene_sampling import SamplingConfig
        config['sampling']=SamplingConfig(**sampling).to_dict()
    world, rank, local = (int(os.environ.get(k, default)) for k, default in
                          (("WORLD_SIZE", 1), ("RANK", 0), ("LOCAL_RANK", 0)))
    device = ("cuda" if torch.cuda.is_available() else "cpu") if device == "auto" else device
    device = torch.device(device)
    if device.type not in ("cpu", "cuda"):
        raise ValueError("Only CPU and CUDA are supported")
    if device.type == "cuda":
        device = torch.device("cuda", local if world > 1 or device.index is None else device.index)
        torch.cuda.set_device(device)
    if c.precision == "bfloat16" and (device.type != "cuda" or not torch.cuda.is_bf16_supported()):
        raise ValueError("bfloat16 requires a supported CUDA device")
    if world > 1:
        dist.init_process_group("nccl" if device.type == "cuda" else "gloo")
    torch.set_num_threads(c.threads)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    seed_all(c.seed)
    output = Path(output)
    train = open_dataset(data, "train", config["policy"],config.get('sampling'))
    validation = open_dataset(data, "validation", config["policy"],config.get('sampling')) if "validation" in train.manifest["splits"] else None
    end = c.steps if stop_after is None else min(c.steps, stop_after)
    fingerprints = [None]
    if rank == 0:
        fingerprints[0] = {"train": train.fingerprint(), "validation": validation.fingerprint() if validation else None,
                           "code": code_fingerprint()}
    if world > 1:
        dist.broadcast_object_list(fingerprints, src=0)
    identity = fingerprints[0]
    model = build_policy(config["policy"])
    if c.vision_init_path and resume is None:
        from .initialization import initialize_vision
        initialize_vision(model, c.vision_init_path, c.vision_init_sha256)
    if world > 1 and device.type == "cuda":
        model = nn.SyncBatchNorm.convert_sync_batchnorm(model)
    statistics = [training_statistics(train,config['policy'],c.flow_statistics_source,identity) if rank == 0 else None]
    if rank == 0 and validation:
        validation.preflight()
    if rank == 0 and hasattr(train,'sampling_diagnostics') and resume is None:
        (output/'sampling-audit.json').write_text(json.dumps(dict(epoch=0,split='train',
            sampling=config['sampling'],counts=train.sampling_diagnostics),indent=2)+'\n')
    if world > 1:
        dist.broadcast_object_list(statistics, src=0)
    model.set_statistics(statistics[0]); model.to(device)
    ema = EMA(model, c.ema_power) if c.ema else None
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=c.lr,
                                  weight_decay=c.weight_decay, betas=c.betas)
    step, saved = 0, None
    if resume:
        saved = torch.load(resume, map_location="cpu", weights_only=True)
        if (saved.get("schema") != "4dmae.training.v1" or saved["config"] != config or
                saved["identity"] != identity or saved["world_size"] != world or saved["device_type"] != device.type):
            raise ValueError("Resume requires unchanged source, data, recipe, world size and device type")
        if saved["statistics"] != statistics[0]:
            raise ValueError("Training statistics changed")
        model.load_state_dict(saved["model"], strict=True)
        # DP's native normalizer reconstructs parameters on the checkpoint device.
        # Reapply the target device before restoring Adam state / building DDP.
        model.to(device); optimizer.load_state_dict(saved["optimizer"])
        if ema:
            ema.model.load_state_dict(saved["ema"], strict=True); ema.model.to(device); ema.step_count = saved["ema_step"]
        step = saved["step"]
        if step >= end:
            raise ValueError("Resume target must exceed the saved step")
    sampler = GlobalBatchSampler(len(train), c, world, rank, step, end,epoch_keys=getattr(train,'epoch_keys',False),sampling=config.get('sampling'))
    # A separate generator keeps DataLoader iterator creation out of model RNG.
    loader = DataLoader(train, batch_sampler=sampler, num_workers=c.workers, pin_memory=device.type == "cuda",
                        generator=torch.Generator().manual_seed(c.seed + rank), persistent_workers=c.workers > 0)
    wrapped = LossModule(model, config["policy"])
    if world > 1:
        wrapped = DDP(wrapped, device_ids=[device.index] if device.type == "cuda" else None,
                      broadcast_buffers=False, find_unused_parameters=True)
    if rank == 0:
        metadata = {"config": config, "identity": identity, "statistics": statistics[0],
                    "world_size": world, "device_type": device.type, "microbatch_per_rank": sampler.micro,
                    "parameters": sum(p.numel() for p in model.parameters()),
                    "versions": {name: importlib.metadata.version(name) for name in
                                 (("torch", "torchvision", "numpy", "einops", "timm", "overrides", "huggingface-hub") +
                                  (("diffusers", "robomimic", "zarr", "numcodecs", "omegaconf", "six")
                                   if config["policy"]["name"] == "diffusion_policy" else ()))},
                    "data_metadata": train.manifest["metadata"]}
        if resume:
            if json.loads((output / "run.json").read_text()) != metadata:
                raise ValueError("Output directory belongs to a different run")
            reconcile_resume_output(output, step)
        else:
            (output / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        with (output/'hardware-events.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(time_unix=time.time(),resume_step=step,
                device=str(device),gpu=torch.cuda.get_device_name(device) if device.type=='cuda' else None,
                world_size=world,bitwise_cross_hardware_guarantee=False))+'\n')
    seed_all(c.seed + rank)
    if saved:
        restore_rng(saved["rng_by_rank"][rank], device)
    iterator = iter(loader)
    started = time.monotonic()
    model.train()
    while step < end:
        optimizer.zero_grad(set_to_none=True)
        # Step-indexed schedule: resuming does not reset or extend the schedule.
        multiplier = (step + 1) / max(1, c.warmup_steps) if step < c.warmup_steps else (
            1. if c.lr_schedule == 'constant' else .5 * (1 + math.cos(
                math.pi * (step - c.warmup_steps) / max(1, c.steps - c.warmup_steps))))
        for group in optimizer.param_groups:
            group["lr"] = c.lr * multiplier
        metrics = {}
        batches = [next(iterator) for _ in range(c.accumulation_steps)]
        for observation, targets in batches:
            validate_batch(observation, targets, config["policy"])
        scales = accumulation_scales(config["policy"], batches, device)
        for micro, (observation, targets) in enumerate(batches):
            observation, targets = move((observation, targets), device)
            sync = wrapped.no_sync() if world > 1 and micro + 1 < c.accumulation_steps else contextlib.nullcontext()
            with sync:
                with torch.autocast(device.type, dtype=torch.bfloat16, enabled=c.precision == "bfloat16"):
                    losses = wrapped(observation, targets, scales[micro])
                    loss = losses["total"]
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite training loss")
                loss.backward()
            for key, value in losses.items():
                metrics[key] = metrics.get(key, 0.) + value.detach().float()
        norm = nn.utils.clip_grad_norm_(model.parameters(), c.clip_grad_norm, error_if_nonfinite=True)
        optimizer.step(); step += 1
        if ema:
            ema.update(model)
        if step % c.log_every == 0 or step == end:
            if world > 1:
                for value in metrics.values():
                    dist.all_reduce(value); value.div_(world)
            if rank == 0:
                line = {"event": "train", "step": step, "loss": {k: v.item() for k, v in metrics.items()},
                        "grad_norm_rank0": norm.item(), "lr": optimizer.param_groups[0]["lr"],
                        "elapsed_s": time.monotonic() - started}
                with (output / "metrics.jsonl").open("a") as stream:
                    stream.write(json.dumps(line) + "\n")
                print(json.dumps(line), flush=True)
        if validation and (step % c.validate_every == 0 or step == end):
            # Eval on rank 0 with unwrapped eval-mode networks: no DDP/SyncBN collectives.
            if rank == 0:
                result = {"event": "validation", "step": step,
                          **validate(ema.model if ema else model, validation, config["policy"], device,
                                     c.seed + 10000, c.validation_samples)}
                with (output / "metrics.jsonl").open("a") as stream:
                    stream.write(json.dumps(result) + "\n")
                print(json.dumps(result), flush=True)
            if world > 1:
                dist.barrier()
        if step % c.save_every == 0 or step == end:
            states = [None] * world
            if world > 1:
                dist.all_gather_object(states, rng_state(device))
            else:
                states[0] = rng_state(device)
            if rank == 0:
                checkpoint = {"schema": "4dmae.training.v1", "config": config, "model": model.state_dict(),
                              "ema": ema.model.state_dict() if ema else None, "ema_step": ema.step_count if ema else 0,
                              "optimizer": optimizer.state_dict(), "step": step, "world_size": world,
                              "device_type": device.type, "rng_by_rank": states, "identity": identity,
                              "statistics": statistics[0], "data_metadata": train.manifest["metadata"]}
                atomic_save(checkpoint, output / "last.pt")
                export = {k: checkpoint[k] for k in ("schema", "config", "model", "ema", "step", "statistics", "data_metadata")}
                atomic_save(export, output / f"policy-{step:06d}.pt")
            if world > 1:
                dist.barrier()
    return output / "last.pt"
