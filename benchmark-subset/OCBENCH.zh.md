# OCBench：重点加入 Bowling

**结论：将 Bowling 作为 CollisionChain 之后优先追加的公开交互任务。** 首轮受控诊断仍使用 FreeMotion、Tool Contact/Release 和 CollisionChain；Bowling 增加球–瓶、瓶–瓶碰撞、倾倒、旋转和自由运动，适合验证模型能否预测机器人未直接触碰的下游物体。

2026-10-12 已完成源码／发布清单检查、官方验证轨迹第一条的状态读取与深度重渲染，以及 CPU seed 0/1/2 三条新采 rollout。它是**任务选型＋深度／物理小样本入口**，没有训练模型、接入共享评估 runner、构造严格 hidden-state 配对或运行 MJWarp。分支 task/benchmark-subset-v1；无 PR，未合并私人 main。

[English](OCBENCH.en.md) · [RGB-D / 3D / contact GIF 页面](https://peiqil.com/dynamic-robot-bench-viewer/ocbench/) · [28 项 Inventory 与证据](ocbench.json) · [数值验收](ocbench_validation.json)

## 为什么 Bowling 值得加
机器人先推动球，球离开机器人后滚向球瓶；球–瓶碰撞和瓶–瓶碰撞可以引起平移、旋转、倾倒。与 2–3 方块受控碰撞链相比，Bowling 有 11 个动态刚体和更复杂的接触拓扑。重点应是预测 **10 个球瓶**，尤其是机器人没有直接接触、且预测起点尚未运动的球瓶，而不只是球的轨迹。

推荐先截取球进入球瓶区域前后 0.2/0.5/1.0 秒窗口，比较 H-self/H-all，并遮蔽球或上游球瓶的历史；所有模型保留相同当前几何、查询点、预提交动作与预算。只预测球或平均所有静止点，会掩盖跨物体预测失败。除逐物体 persistent-point ADE/FDE、moving-object ADE 外，建议报告倾倒数量／身份、旋转误差、传播顺序和阶段误差。没有 contact head 时，只按真实接触标注划阶段，不从点预测强推接触时刻。

这些是**后续实验设计**，尚无 Bowling 模型成绩或历史必要性证据。OCBench 专家的 non-Markovian 属性是动作生成过程的性质，不能直接当作隐藏物理状态实验。默认状态观测明确含球线速度／角速度，做 Hidden Velocity 时必须排除它们；当前 RGB、点历史与机器人 proprio 可以作为可见输入，真实物体速度只放 privileged。

## 环境、控制与原判定
- 官方 ID：`bowling-task1-v0`（MJWarp）；`bowling-cpu-task1-v0`（CPU）；`visual-bowling-cpu-task1-v0`（三视角 RGB）。**Bowling 没有 lite 版本**。本项目没有新注册重复环境。
- UR5e＋Robotiq 2F-85；7 维归一化 joint-delta action：6 个机械臂关节＋夹爪。臂关节 delta 比例为 0.18/0.18/0.18/0.36/0.36/0.36 rad，夹爪为归一化 opening 增量，比例 0.12（不是 0.12 rad）。形状虽与 Panda 的 7D 相同，控制语义不同，不能直接拼接训练。
- 默认控制 50 Hz、物理 500 Hz、500 controls／10 秒；球半径 0.0425 m、10 个球瓶。状态观测 102D，完整 qpos/qvel 为 91D/80D。官方 visual 用 front、side、wrist 各 224² RGB；这次 smoke 用 front 160² RGB-D。
- 球瓶局部竖直轴的世界 Z 分量小于 0.75 时记为倾倒，标志累积保留；每新倒一瓶奖励 0.1，最多回报 1.0。**上游 `success` 始终 false**，不能将其作为该任务成功率。报告 pins_knocked／return；若研究另定义全倒成功，单独命名，不改官方判定。
- 初始球 XY、整体球瓶阵列 XY、机器人初态有随机化；CPU primitive 随机化推球方向／速度、接近位置、高度、夹爪、姿态等。质量、摩擦和几何并未由本次 smoke 随机化，明确的 OOD physics/geometry/composition split 尚未实现。
- 场景有不可见的边界墙与限制夹爪前进的平面。训练／评价要记录此结构，不能把边界触碰后的行为解释为普通无边界桌面动力学。

## 官方数据与深度
发布 revision `fd771640f7a47879d8b06657fe05389641b5bff9` 的 Bowling 为 **10,000 train／1,000 validation episodes**，每条 500 controls。训练 NPZ 3,470,914,682 bytes，验证 NPZ 346,792,143 bytes；此为发布清单，不代表全部下载到项目。

实际读取官方验证 NPZ 的 ZIP/NPY 片段，确认：
- observations float32 [501000,102]、actions [500000,7]；
- **qpos [500000,91]、qvel [500000,80]**，完整广义坐标／速度按 action 前时间保存；这不是包含 ctrl／act／warm-start 的完整 integration snapshot；
- 不含 RGB、depth 或 camera calibration。官方未发布 Bowling visual 数据；有 visual 环境不等于有 visual 数据包。
- 第一条 500 状态已读取，选其中 30 帧恢复 qpos/qvel，使用匹配资产的 CPU MuJoCo 新渲染 RGB＋metric Z-depth。读取约 1.80 MB 的 HTTP ranges，没有下载 3.47 GB 训练库，也没有执行 pickle。未校验整个压缩包 SHA256／CRC，不能称全库验收。
- observations 每条多一个终止观测，但 qpos/qvel 没有额外终止状态；本次只渲染帧 0–499，不凭空补第 500 帧。动作与稀疏图像分别对齐，不能把两种长度直接 zip。
- 官方 `load_dataset` 只返回标准 BC 字段，会丢弃 qpos/qvel。重渲染应直接读取 raw NPZ，保留附加字段。
- 从同一恢复状态新渲染 RGB 与 depth 配对使用。CPU/MJWarp 数值实现不完全一致；恢复原状态不等于重跑动作能复现 GPU 轨迹。原包无 RGB，没有像素匹配证据。
- 原状态重渲染可获得物体位姿／持续点；**不能据此恢复原 MJWarp 的真实接触事件或 force**。本次官方轨迹不导出此类接触真值；新采 CPU 数据才记录实时求解器接触。

![官方 Bowling 验证轨迹：RGB / Z-depth](https://peiqil.com/dynamic-robot-bench-viewer/ocbench/media/official-val-episode0-rgb-depth.gif)

**深度：已验证原状态重渲染；也可新采仿真 RGB-D，不需要模型估计。** 单位米，camera-axis Z。背景 far-plane 7 m 不代表可反投影的真实表面，已在 valid 中排除。Mac 渲染器报告缺少 ARB_clip_control；四个样本初帧的地面射线检查最大误差约 0.037 mm。这是地面／标定数值检查，不是所有网格、遮挡或像素的完备审计。该 GIF 30 帧均匀选取、每帧播放 100 ms，约 3.33× 加速。

## 本次 CPU 物理与身份验证
seed 0/1/2 均健康运行 500 controls，分别击倒 **8/0/0** 瓶。seed 0 记录球–pin_0/2/5 和 11 类瓶–瓶碰撞 pair；seed 1/2 未出现球–瓶或瓶–瓶接触，得分零，是保留的自然负样本。这里没有把零分解释为人为保证的 Near Miss，也没有宣称已覆盖所有失败原因。seed 0 没有任何机器人–球瓶 contact：机器人–球接触在 2.752–3.318 s，首次球–瓶 4.046 s，首次瓶–瓶 4.104 s。上述区间为第一／最后观测，不把中间间隙当连续接触；这直接支持解除后自由运动再传播的样本有效性。

每条保存 501 帧刚体状态、101 帧 RGB-D（10 Hz）、2 ms 求解器 contact samples（500 Hz）。11 个对象各绑定 24 个固定 body-local 物理点；球为固定球面采样，球瓶为固定编译网格顶点。点从同一 body pose 运输，IDs 不随时间重采样，局部坐标回转误差小于 4e-16 m。点覆盖可遮挡表面，不是逐帧可见深度点云；未包含机器人 link 点。

使用原控制逻辑，将 nstep=10 拆成十次 mj_step 以记录接触。seed 0 对照上游标准步进，qpos/qvel/actions 逐步完全一致；固定 seed 再跑完全一致。没有 teleport、插值外力或冻结下游球瓶。接触来自 active MuJoCo constraints 与 mj_contactForce 的法向分量 >1e-6 N；时间为求解器积分前状态，分辨率 2 ms。contact-events 对连续样本分段并标明左／右删失；只导出法向 force，**不将 force×dt 称为真实 impulse**。

![新采 seed 0：RGB / 持续 XYZ / 求解器接触](https://peiqil.com/dynamic-robot-bench-viewer/ocbench/media/seed0-dynamics.gif)

**深度：该新采 rollout 原生保存 RGB-D（米、Z-depth）；此 GIF 展示 RGB、固定 XYZ 和 contact。**

![新采 seed 1：零分样本](https://peiqil.com/dynamic-robot-bench-viewer/ocbench/media/seed1-dynamics.gif)

**深度：该新采零分 rollout 同样保存 RGB-D；不是给旧视频补估计深度。** 全部三个 seed 的 RGB–depth GIF 见在线页面。

## 实际文件与复现命令
- `tools/fetch_ocbench_bowling_prefix.py`：锁定发布 revision，只读取第一条验证轨迹所需数值片段。
- `tools/ocbench_bowling_smoke.py`：Bowling 专用 CPU smoke／原状态重渲染，绕开上游通用 CPU generator 缺少 Bowling 路由的问题。
- `tools/visualize_ocbench_bowling.py`：真实 RGB、持续 XYZ、500 Hz 接触 timeline 和 onset/release intervals。
- `tasks/ocbench_bowling/requirements-cpu.txt`：锁定运行依赖。完整数值产物保留在本机 ignored results，不随 Git 或公开网站上传。

在本分支 checkout 执行：

```bash
uv venv --python 3.12 .runtime/ocbench-cpu
uv pip install --python .runtime/ocbench-cpu/bin/python -r tasks/ocbench_bowling/requirements-cpu.txt
.runtime/ocbench-cpu/bin/python tools/fetch_ocbench_bowling_prefix.py --output results/ocbench-bowling/release-prefix
.runtime/ocbench-cpu/bin/python tools/ocbench_bowling_smoke.py --output results/ocbench-bowling/run --release-prefix results/ocbench-bowling/release-prefix --seeds 0 1 2
.runtime/ocbench-cpu/bin/python tools/visualize_ocbench_bowling.py --root results/ocbench-bowling/run
```

Linux 无桌面时，可在这些命令前设置 `MUJOCO_GL=egl`；该后端本次未验收。命令是小样本生成／验收，不是模型在线／离线评估命令。

新采 HDF5：`model_visible/` 包含 RGB、depth、valid、K、OpenCV world_to_camera、frame_ids、时间、14D robot proprio（6 joint pos＋6 joint vel＋gripper joint pos/vel）及实际提交的 7D action。`privileged/` 包含完整状态、body poses、持续点／IDs、倾倒状态、奖励和真实 contacts。官方重渲染的 sensor `sample.npz` 和 `privileged.npz` 分开保存。14D proprio 的夹爪位置为原始关节值，不等于官方 observation 的归一化 opening。

这些专家动作是逐步根据状态产生并在每个 step 前提交的命令。它们可用于离线条件切片，但本次**没有证明未来整段命令事先固定**；严格 action-counterfactual 需要从 query state 预提交同一 action chunk 再分支运行，不能偷用未来真实机器人轨迹或专家 future privileged decision。

## OCBench 其余任务
Inventory 已收录五类、28 个完整 task IDs 及官方视频来源，详情见 ocbench.json；**其他 27 项没有本次深度／物理验收**，不加入 44 项已验收深度计数。

- block：8 项，single task1；double/triple task1–2；quadruple task1–3。支持搬运、堆叠／多物体配置，可作 Grasp/Release 后续测试，普通成功示范不保证接触释放难例。
- chamber：7 项，easy task1–3；medium/hard task1–2。抽屉、窗、按钮锁和方块的关节／组合交互较有价值，优先于加入更多普通 Pick&Place。
- hanoi：6 项，single/double/triple 各 task1–2。几何约束与高精度插套，留到稳定 tracking 和 articulated link IDs 后。
- switch：6 项，3x3/4x4/5x5 各 task1–2。邻接灯色切换属于离散规则，不是物体之间物理碰撞传播，不优先验证 interaction dynamics。
- bowling：1 项，本次重点。没有 lite／现成 visual Bowling 数据，不应照搬项目页“所有 8 组合”的笼统说明。

## 成熟度、限制与后续门槛
OCBench 首版软件 2026-10-04 发布，论文 2026-10-05 提交；截至检查约一周，不能将其称为大量独立使用、长期验证或无隐藏 bug。公开 issue #2 报告新 mujoco-warp 下 switch 4x4/5x5 contact buffer overflow；报告中的 Bowling 未超该 buffer，但**这不是我们的 GPU 验收**。后续 MJWarp 采集需锁版本、检查 overflow、核对每 world 的碰撞与评分。

尚缺：训练 adapter、完整 family split、受控 physics/geometry randomization、严格 hidden velocity／action pairs、共享 online/offline metrics、官方全数据哈希／终止态／CPU–GPU 重放验证。已有评估器和三个核心任务未改动；这次 smoke 通过不等于完整 benchmark 接入或模型泛化证明。

首轮保持原三个核心任务；下一轮先加 Bowling 的球瓶目标窗口作为外部互动测试，再扩展其他 OCBench 家族。这样既能用受控任务排查模型，也能检查效果是否迁移到公开的复杂碰撞场景。

## 原始依据
[项目页](https://seohong.me/projects/ocbench/)；[论文](https://arxiv.org/abs/2610.07056)；[源码与 MIT 许可证](https://github.com/seohongpark/ocbench/tree/6939a1e84f7ce9dbdd20c9f80d4cf335e8f83b49)；[Bowling 实现](https://github.com/seohongpark/ocbench/blob/6939a1e84f7ce9dbdd20c9f80d4cf335e8f83b49/ocbench/envs/bowling_env.py)；[发布数据](https://huggingface.co/datasets/seohongpark/ocbench/tree/fd771640f7a47879d8b06657fe05389641b5bff9/full/bowling-task1-v0)；[MJWarp collector](https://github.com/seohongpark/ocbench/blob/6939a1e84f7ce9dbdd20c9f80d4cf335e8f83b49/impls/envs/streaming_data.py)；[已报告 contact overflow](https://github.com/seohongpark/ocbench/issues/2)。底层机器人资产沿用上游各自许可证；没有重新分发第三方 mesh 或发布训练结果。

