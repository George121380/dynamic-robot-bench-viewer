"""Precomputed windows in memory-mapped NPY shards; no task or simulator imports."""
import bisect
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

OBSERVATION_KEYS = {"rgb", "state", "history_xyz", "history_valid"}
TARGET_KEYS = {"action", "action_valid", "c_future", "c_future_valid", "q_anchor",
               "q_past", "q_past_valid", "q_future", "q_future_valid"}


def required_keys(policy):
    obs, target = {"rgb", "state"}, {"action", "action_valid"}
    if policy["name"] in ("4dmae", "egowam"):
        arm = policy.get("model", {}).get("arm", "B5" if policy["name"] == "4dmae" else "B1")
        if arm not in ("B0", "B1"):
            obs |= {"history_xyz", "history_valid"}
        if arm not in ("B0", "B1", "B2"):
            target |= {"c_future", "c_future_valid"}
        if arm in ("B1", "B4", "B5", "G"):
            target |= {"q_anchor", "q_future", "q_future_valid"}
        if arm in ("B4", "B5", "G"):
            target |= {"q_past", "q_past_valid"}
    return obs, target


def validate_batch(observation, targets, config):
    """Fail on shape/dtype/valid-label errors at the public data boundary."""
    needed_obs, needed_targets = required_keys(config)
    if not needed_obs <= observation.keys():
        raise ValueError(f"Missing observations: {needed_obs - observation.keys()}")
    c = config.get("model", {})
    rgb, state = observation["rgb"], observation["state"]
    b = len(rgb)
    if not b or rgb.dtype != torch.uint8 or rgb.ndim != 5 or rgb.shape[1:3] != (c.get("cameras", 1), 3) or min(rgb.shape[-2:]) < 32:
        raise ValueError("RGB must be uint8 [B,cameras,3,H,W], H/W >= 32")
    if config["name"] == "diffusion_policy" and rgb.shape[-2:] != (c.get("image_height", 128), c.get("image_width", 128)):
        raise ValueError("DP RGB resolution must match the model configuration")
    def check(value, shape, name, mask=None):
        if value.shape != shape or value.dtype != torch.float32:
            raise ValueError(f"{name}: expected float32 {shape}, got {value.dtype} {tuple(value.shape)}")
        if not torch.isfinite(value if mask is None else value[mask]).all():
            raise ValueError(f"{name}: nonfinite valid data")
    def boolean(value, shape, name):
        if value.dtype != torch.bool or value.shape != shape:
            raise ValueError(f"{name}: expected bool {shape}")
    check(state, (b, c.get("state_dim", 18)), "state")
    h = c.get("history", 16)
    if "history_xyz" in needed_obs:
        xyz, valid = observation["history_xyz"], observation["history_valid"]
        if xyz.ndim != 4 or xyz.shape[1] < 1:
            raise ValueError("At least one history point slot required; use all-false validity for an empty set")
        boolean(valid, (b, xyz.shape[1], h), "history_valid")
        check(xyz, (*valid.shape, 3), "history_xyz", valid)
    if targets is None:
        return
    if not needed_targets <= targets.keys():
        raise ValueError(f"Missing targets: {needed_targets - targets.keys()}")
    boolean(targets["action_valid"], (b, c.get("chunk", 40)), "action_valid")
    check(targets["action"], (b, c.get("chunk", 40), c.get("action_dim", 7)), "action", targets["action_valid"])
    if not targets["action_valid"].any(-1).all():
        raise ValueError("Every window must supervise at least one action")
    if "q_anchor" in needed_targets:
        anchor = targets["q_anchor"]
        if anchor.ndim != 3 or anchor.shape[1] < 1:
            raise ValueError("At least one query anchor required")
        check(anchor, (b, anchor.shape[1], 3), "q_anchor")
    for name in ("c_future", "q_past", "q_future"):
        if name in needed_targets:
            n = observation["history_xyz"].shape[1] if name == "c_future" else targets["q_anchor"].shape[1]
            valid = targets[name + "_valid"]
            boolean(valid, (b, n, h - 1), name + "_valid")
            check(targets[name], (b, n, h - 1, 3), name, valid)
    if config["name"] == "diffusion_policy" and not targets["action_valid"].all():
        raise ValueError("Use complete action windows for original DP and matched comparisons")
    if config["name"] == "diffusion_policy" and targets["action"].abs().max() > 1.00001:
        raise ValueError("DP identity-action recipe requires native actions in [-1,1]")
    if (config["name"] in ("egowam", "4dmae") and
            c.get("arm", "B5" if config["name"] == "4dmae" else "B1") == "B1" and
            not c.get("pad_terminal_actions", False) and not targets["q_future_valid"].all()):
        raise ValueError("B1 reference requires complete future windows")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class WindowDataset(Dataset):
    def __init__(self, manifest, split, policy, *, schema='4dmae.windows.v1'):
        self.path = Path(manifest).resolve()
        self.manifest = json.loads(self.path.read_text())
        self.policy = policy
        if self.manifest.get("schema") != schema:
            raise ValueError("Expected schema 4dmae.windows.v1")
        metadata = self.manifest["metadata"]
        dt = metadata.get("control_dt_s", 0)
        if not metadata.get("action_semantics") or not isinstance(dt, (int, float)) or not math.isfinite(dt) or dt <= 0:
            raise ValueError("Declare action_semantics and positive control_dt_s")
        if "history_xyz" in required_keys(policy)[0] or "q_anchor" in required_keys(policy)[1]:
            if metadata.get("coordinate_units") != "m" or not metadata.get("coordinate_frame"):
                raise ValueError("Tracks require a declared fixed coordinate frame in metres")
            h = policy.get("model", {}).get("history", 16)
            past, future = metadata.get("history_offsets_s", []), metadata.get("future_offsets_s", [])
            if (len(past) != h or len(future) != h - 1 or
                    not all(isinstance(v, (int, float)) and math.isfinite(v) for v in past + future) or
                    past[-1] != 0 or not all(v > 0 for v in future)):
                raise ValueError("Explicit history/future slot times must match model.history")
            if any(a >= b for a, b in zip(past + future, (past + future)[1:])):
                raise ValueError("History/future times must be strictly increasing")
        episode_owner = {}
        for split_name, rows in self.manifest["splits"].items():
            for row in rows:
                if not row.get("episode_ids"):
                    raise ValueError("Each shard must declare its source episode_ids")
                for episode in row["episode_ids"]:
                    if episode in episode_owner and episode_owner[episode] != split_name:
                        raise ValueError("Episode leakage across splits: " + episode)
                    episode_owner[episode] = split_name
        self.shards, self.ends, self.files = [], [], []
        signatures = {}
        keys = required_keys(policy)
        for row in self.manifest["splits"].get(split, []):
            folder = (self.path.parent / row["path"]).resolve()
            if not folder.is_relative_to(self.path.parent):
                raise ValueError("Shard path must stay inside the dataset directory")
            shard, count = {}, None
            for section, fields in zip(("observation", "targets"), keys):
                shard[section] = {}
                for key in sorted(fields):
                    file = (folder / f"{section}.{key}.npy").resolve()
                    if not file.is_relative_to(self.path.parent):
                        raise ValueError("Shard column path must stay inside the dataset directory")
                    value = np.load(file, mmap_mode="r", allow_pickle=False)
                    if value.ndim < 1 or (count is not None and len(value) != count):
                        raise ValueError("Shard columns have inconsistent lengths")
                    count = len(value)
                    signature = (value.dtype, value.shape[1:])
                    if signatures.setdefault((section, key), signature) != signature:
                        raise ValueError(f"Inconsistent shard dtype/shape: {section}.{key}")
                    shard[section][key] = value
                    self.files.append(file)
            if not count:
                raise ValueError("Empty shard")
            self.shards.append(shard)
            self.ends.append((self.ends[-1] if self.ends else 0) + count)
        if not self.shards:
            raise ValueError("No shards in split: " + split)
        self.split = split
        observation, targets = self[0]
        validate_batch({k: v[None] for k, v in observation.items()},
                       {k: v[None] for k, v in targets.items()}, policy)

    def __len__(self):
        return self.ends[-1]

    def __getstate__(self):
        # NumPy's memmap pickle serializes its contents. Spawned workers must reopen
        # files instead, so a large dataset never gets copied through worker IPC.
        state = self.__dict__.copy()
        state["shards"] = [{section: {key: str(value.filename) for key, value in arrays.items()}
                            for section, arrays in shard.items()} for shard in self.shards]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.shards = [{section: {key: np.load(file, mmap_mode="r", allow_pickle=False)
                                 for key, file in arrays.items()}
                        for section, arrays in shard.items()} for shard in state["shards"]]

    def preflight(self):
        """Scan all labels/observations, including validation, before any updates."""
        for shard in self.shards:
            for start in range(0, len(shard["observation"]["state"]), 128):
                self._validate_slice(shard, slice(start, start + 128))

    def _validate_slice(self, shard, sl):
        tensors = [{key: torch.from_numpy(np.array(value[sl], copy=True)) for key, value in shard[section].items()}
                   for section in ("observation", "targets")]
        validate_batch(*tensors, self.policy)

    def __getitem__(self, index):
        if not 0 <= index < len(self):
            raise IndexError(index)
        part = bisect.bisect_right(self.ends, index)
        offset = index - (self.ends[part - 1] if part else 0)
        return tuple({k: torch.from_numpy(np.array(v[offset], copy=True)) for k, v in self.shards[part][section].items()}
                     for section in ("observation", "targets"))

    def fingerprint(self):
        return {"manifest": sha256(self.path), "split": self.split, "samples": len(self),
                "files": {str(p.relative_to(self.path.parent)): sha256(p) for p in self.files}}

    def statistics(self, flow_statistics_source="all_required"):
        if flow_statistics_source not in ("all_required", "q_future"):
            raise ValueError("Unknown flow statistics source")
        if flow_statistics_source == "q_future" and "q_future" not in self.shards[0]["targets"]:
            raise ValueError("q_future statistics require query future labels")
        if self.split != "train":
            raise ValueError("Fit statistics on train only")
        moments = {}
        def update(name, values):
            x = np.asarray(values, dtype=np.float64).reshape(-1, values.shape[-1])
            if not len(x):
                return
            if not np.isfinite(x).all():
                raise ValueError("Nonfinite valid training data: " + name)
            if name not in moments:
                moments[name] = [0, np.zeros(x.shape[-1]), np.zeros(x.shape[-1]), x.min(0), x.max(0)]
            s = moments[name]
            s[0] += len(x); s[1] += x.sum(0); s[2] += np.square(x).sum(0)
            s[3] = np.minimum(s[3], x.min(0)); s[4] = np.maximum(s[4], x.max(0))
        for shard in self.shards:
            o, t = shard["observation"], shard["targets"]
            for start in range(0, len(o["state"]), 128):
                sl = slice(start, start + 128)
                self._validate_slice(shard, sl)
                update("state", o["state"][sl])
                update("action", t["action"][sl][t["action_valid"][sl]])
                for name in (("q_future",) if flow_statistics_source == "q_future" else ("c_future", "q_past", "q_future")):
                    if name in t:
                        valid = t[name + "_valid"][sl]
                        if name == "c_future":
                            valid = valid & o["history_valid"][sl][..., -1:]
                        update("flow", t[name][sl][valid])
                if "history_xyz" in o and flow_statistics_source == "all_required":
                    xyz, valid = o["history_xyz"][sl], o["history_valid"][sl]
                    live = valid[..., :-1] & valid[..., -1:]
                    update("flow", (xyz[..., :-1, :] - xyz[..., -1:, :])[live])
        out = {"flow_mean": [0., 0., 0.], "flow_std": [.05, .05, .05]}
        for name, (n, total, square, low, high) in moments.items():
            mean = total / n
            std = np.sqrt(np.maximum(square / n - mean ** 2, 0)).clip(.01)
            out.update({name + "_mean": mean.tolist(), name + "_std": std.tolist(),
                        name + "_min": low.tolist(), name + "_max": high.tolist()})
        return out


def open_dataset(manifest, split, policy, sampling=None):
    schema = json.loads(Path(manifest).read_text()).get("schema")
    if schema == '4dmae.scene_windows.v1':
        from .scene_data import SceneDataset
        return SceneDataset(manifest,split,policy,sampling)
    if sampling is not None:
        raise ValueError('A sampling configuration requires a scene geometry dataset')
    if schema == "4dmae.episodes.v1":
        from .episodes import EpisodeDataset
        return EpisodeDataset(manifest, split, policy)
    return WindowDataset(manifest, split, policy)


def write_shard(folder, observation, targets):
    """Export batched NumPy arrays. The caller defines temporal windows and splits."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    for section, arrays, allowed in (("observation", observation, OBSERVATION_KEYS), ("targets", targets, TARGET_KEYS)):
        if not arrays.keys() <= allowed:
            raise ValueError("Unknown fields in " + section)
        for key, array in arrays.items():
            np.save(folder / f"{section}.{key}.npy", np.asarray(array), allow_pickle=False)
