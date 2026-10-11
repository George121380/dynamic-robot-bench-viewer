# 交互动力学 Benchmark 简要说明

已实现四个 P0 协议、20 个模式，基础 60/60 rollout 及额外独立物理参数碰撞链 19/19 通过小样本验收。复用原生 Panda/PhysX 环境；没有训练模型。任务清单见 [Inventory](task_inventory.json)，完整命令见 [实现说明](README.zh.md)，实际模式 GIF 见 [检查页](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/)。[English](BENCHMARK.en.md)。

## 任务与样本

- **ToolContactRelease-v1**：L 工具接触、动量传递、解除。正样本为有效拉动及接触后滑动；负样本为 near miss、错误方向／不足拉动。操作目标为真实接触且负 X 拉动超过 4 cm。
- **HookPullDynamics-v1**：复用同一 L 工具，比较有效挂接、错过、无效接触、抬升／侧移脱钩。操作目标同上；挂接状态是接触＋速度跟随＋负 X 进展的近似标签。
- **CollisionChain-v1**：握杆推 A，真实 A→B 或 A→B→C 碰撞传播；正样本包括传播后独立运动，负样本包括偏置 miss、5 kg／高摩擦 B 导致弱传播。三体目标要求接触链、按顺序起动、C 移动超过 1.5 cm，且机器人／工具未直接碰 B/C。
- **FreeMotionInterception-v1**：球在干预前已运动，比较成功、提前、空间错过、迟到、转向与无干预。操作目标为真实拦截接触且速度变化超过 0.02 m/s；转向模式另要求超过 45°。

`mode_verified` 表示指定模式确实触发，负样本也可以通过；`task_success` 独立表示物理目标达成，旧 `success` 仅是前者兼容别名。模式门槛、失败记录和实际数值见 [验收](VALIDATION.zh.md)。

## 随机化、划分与真值

尺度、质量、摩擦、恢复系数、初始布局／速度、工具动作速度／方向、接触偏置和释放时刻按任务随机化并保存。碰撞链可独立采样 A/B/C 的物理参数；失败模式的参数覆盖单独保存。ID、OOD Geometry（尺寸）、OOD Physics（参数范围）、OOD Composition（完整三体组合）具有明确 holdout。先按 scene/trajectory family 划分，再切窗口。

每帧保存原生 RGB-D、校准、机器人状态和实际提交指令；privileged 分组保存固定局部点、持续 IDs、由真实位姿变换的世界 XYZ 轨迹、速度、每物理子步接触／冲量／位置、事件、phase、逐帧位移进度与成功标签。物体速度／质量／未来姿态不进入模型输入。手 link 参考点使用近似包围盒；球、工具、刚体使用解析几何点。

三种诊断各有三个 seed：隐藏速度、相同完整初态而不同动作、不同接触历史。严格 Hidden Velocity 需要移除当前 Oracle 点；Contact History 是明确记录误差的近似匹配，使用完整 pre-anchor history。所有分支均经物理积分，匹配指标和 held/changed variables 有记录。

## 统一评价

Object/Target/Moving-object ADE/FDE、物体级误差、传播准确率、phase-wise ADE、配对动作响应误差及 ID/OOD gap。没有显式 contact head 时，接触时间误差返回 null。模型窗口支持 H0/H-self/H-all、按持续点遮蔽和按 object_id 遮蔽全部 link；未来动作仅使用预提交控制，不输入未来真实机器人轨迹。

验收：69/69 CPU 回归、20/20 固定 seed 数组重现、5/5 在线／离线一致、9/9 物理诊断对通过。OOD 仅验收选定正模式；尚未进行大规模统计、原 Isaac Sim 全流程 GPU 回归或神经模型实验。P1 新门／抽屉及搬运滑移扩展暂未实现，原有任务路径保留。
