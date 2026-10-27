"""Causal world-coordinate surface tracks from the pinned task's rigid actors.

Full surfaces are privileged simulator observations, not camera-visible tracks.
C and Q have persistent, disjoint object-local identities; labels are displacement
from the current anchor. This module is shared by export and online evaluation.
"""
from collections import deque
import numpy as np

HISTORY = 16
OBJECTS = ('cube', 'l_shape_tool')


def surface_rectangles(object_name):
    """Return (origin, edge_u, edge_v) rectangles tiling only the exterior."""
    if object_name == 'cube':
        rectangles = []
        for axis in range(3):
            others = [i for i in range(3) if i != axis]
            for side in (-.02, .02):
                origin = np.full(3, -.02); origin[axis] = side
                u, v = np.zeros(3), np.zeros(3)
                u[others[0]], v[others[1]] = .04, .04
                rectangles.append((origin, u, v))
        return np.asarray(rectangles)
    if object_name != 'l_shape_tool':
        raise ValueError(object_name)
    # Union of the handle and hook boxes. Never sample their internal faces.
    polygon = np.array([(0,-.025),(.2,-.025),(.2,.1),(.15,.1),(.15,.025),(0,.025)])
    rectangles = []
    for z in (-.025, .025):
        for x, y, dx, dy in [(0,-.025,.2,.05),(.15,.025,.05,.075)]:
            rectangles.append(([x,y,z],[dx,0,0],[0,dy,0]))
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        rectangles.append(([a[0],a[1],-.025],[*(b-a),0],[0,0,.05]))
    return np.asarray(rectangles)


def point_bank(seed=42):
    rng = np.random.default_rng(seed)
    bank = {}
    for name in OBJECTS:
        rectangles = surface_rectangles(name)
        areas = np.linalg.norm(np.cross(rectangles[:,1], rectangles[:,2]), axis=-1)
        selected = rectangles[rng.choice(len(areas), 64, p=areas/areas.sum())]
        uv = rng.random((64,2))
        points = selected[:,0] + uv[:,0,None]*selected[:,1] + uv[:,1,None]*selected[:,2]
        bank[name] = points.astype(np.float32)
    return bank


def world_points(actor_state, local_points):
    state = np.asarray(actor_state, np.float64)
    q = state[...,3:7]
    if not np.isfinite(state).all() or not np.allclose(np.linalg.norm(q,axis=-1), 1, atol=2e-5):
        raise ValueError('Finite actor poses with wxyz unit quaternions required')
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    xyz = np.asarray(local_points, np.float64)
    v, w = q[...,None,1:], q[...,None,:1]
    t = 2*np.cross(v, xyz)
    return (xyz + w*t + np.cross(v,t) + state[...,None,:3]).astype(np.float32)


def track_sets(actors, bank):
    points = {name:world_points(actors[name], bank[name]) for name in OBJECTS}
    return tuple(np.concatenate([points[name][...,sl,:] for name in OBJECTS], axis=-2)
                 for sl in (slice(0,32),slice(32,64)))


def history_at(track, ticks):
    ticks = np.asarray(ticks)
    indices = ticks[...,None] + np.arange(1-HISTORY,1)
    valid = np.broadcast_to((indices >= 0)[...,None,:], (*ticks.shape, track.shape[-2], HISTORY)).copy()
    xyz = np.swapaxes(track[np.maximum(indices,0)], -3, -2)
    return np.where(valid[...,None],xyz,0).astype(np.float32), valid


def window_columns(actors, bank, windows):
    c, q = track_sets(actors, bank)
    ticks = np.arange(windows)
    if windows + HISTORY - 1 > len(c):
        raise ValueError('Incomplete future labels')
    history, history_valid = history_at(c,ticks)
    past, past_valid = history_at(q,ticks)
    future_ids = ticks[:,None]+np.arange(1,HISTORY)
    future_valid = np.ones((windows,64,HISTORY-1),bool)
    return {
        'observation.history_xyz':history, 'observation.history_valid':history_valid,
        'targets.q_anchor':q[:windows],
        'targets.q_past':np.where(past_valid[...,:-1,None],past[...,:-1,:]-q[:windows,:,None,:],0),
        'targets.q_past_valid':past_valid[...,:-1],
        'targets.q_future':np.swapaxes(q[future_ids],1,2)-q[:windows,:,None,:],
        'targets.q_future_valid':future_valid,
        'targets.c_future':np.swapaxes(c[future_ids],1,2)-c[:windows,:,None,:],
        'targets.c_future_valid':future_valid.copy(),
    }


class OracleHistory:
    def __init__(self, bank):
        self.bank, self.frames = bank, deque(maxlen=HISTORY)

    def observe(self, actors):
        self.frames.append(track_sets(actors,self.bank)[0])
        xyz, valid = history_at(np.stack(self.frames),np.asarray(len(self.frames)-1))
        return dict(history_xyz=xyz, history_valid=valid)
