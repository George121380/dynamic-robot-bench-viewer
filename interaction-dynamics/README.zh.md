# Interaction-Aware 4D Dynamics：实现与验收
本轮在既有 Benchmark 上新增四个交互协议，复用 ManiSkill 的 Panda、桌面、工具、球和控制器。原有任务注册、传送带 runner 和深度流程保留。代码在 `task/interaction-dynamics-v1`；未合并私人 main，无 PR。最终数量与失败记录以 [validation.json](validation.json) 为准；下面明确区分接口、物理验收与模型成绩。

[English](README.en.md) · [逐任务 Inventory](task_inventory.json) · [免登录 GIF](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/) · [既有深度报告](../benchmark_tasks/DEPTH_RUN.zh.md)

## Step 0：现有代码与缺口
检查发生在实现前，基线为 `c39a8799`。旧目录的 42 个可视化条目包括汇总条目和数据集，不能视为 42 个统一可运行环境。

- 已实现：`match_and_pick_from_conveyor`（Isaac Sim、双 X5、移动支撑面／抓取）；`push_puck_collision`（独立分支 `9985d495`，MuJoCo、UR5e、机器人→A→B）。
- ManiSkill 诊断已存在 `PullCubeTool-v1`、`PokeCube-v1`、`RollBall-v1`、`PushT-v1`、`PickCube-v1` 和手指关节诊断。前五种分别覆盖 L 工具拉动、握杆推方块、滚动、偏心推动及抓放；不把诊断录像统一视为策略成功。
- PhysMani 已有 16 个原生任务复现／数据路径：旋转目标、移动抓取、移动插入、按钮和运动容器，另有 PhysMani 汇总条目。
- RoboCasa 的八个条目已跑通原状态 RGB-D 重渲染：OpenDrawer、PanTransfer、CloseFridge、SlideDishwasherRack、StackBowlsCabinet、CoffeeSetupMug、SlideToasterOvenRack、StirVegetables。尚无本轮统一在线策略 adapter。
- ToolHang、AdroitHandHammer 原状态重放；RLBench reach_and_drag、sweep_to_dustpan_of_size 原生专家 RGB-D；MOVi-C、CoPhy、Physion、CLEVRER 是离线数据／生成入口。TurnFaucet-v1 匹配资产仍受阻，旧 GIF 为 v0。
- 旧 evaluator 包含 ADE/FDE 和历史输入实验，但模型、两对象布局及原机器人 recorder 有具体假设。新 Panda 数据使用显式版本化接口，复用评价约定和现有 WebSocket 传输；没有强行修改双 X5 recorder。

主要缺口是三体传播、运动中拦截的正负模式、真正固定局部点身份、每物理子步接触、可观察状态匹配的诊断对及明确参数 holdout。详细 42 项清单保存在 Inventory JSON，历史状态未被改写。

## 任务、模式与判定
新注册 ID 使用独立名称；上游原任务 ID 和原生成功判据未修改。`mode_verified` 表示指定正／负模式实际出现；旧 `success` 保留为其兼容别名。`task_success` 单独记录物理操作目标是否达成，负样本可能是 mode_verified=true、task_success=false，不能把两者混用。它不是原环境策略分数。环境创建后必须通过 `simulation.prepare` 做物理握持、设置场景并提交整段计划；单独 Gym reset 仅建立原生基础场景。

### Tool–Object Contact & Release
`tool_contact_release` / `ToolContactRelease-v1` 继承 PullCubeTool，使用原生 L 形工具和方块。
- engage_pull：真实工具接触，目标沿负 X 拉动超过 4 cm。
- near_miss：工具经过而无目标力接触，目标位移小于 5 mm。
- contact_release：短暂动量传递；最后接触早于结束至少 0.5 s，释放后目标仍移动超过 3 mm。
- failed_engagement：真实接触，但没有达到负 X 4 cm 拉动目标。允许弱运动／错误方向运动，不等于完全静止。

### Hook & Pull
`hook_pull` / `HookPullDynamics-v1` 复用同一个 L 工具环境与几何，避免重复资产和控制器。
- successful_engagement：几何挂接并拉动超过 4 cm。
- hook_miss：无力接触、目标静止。
- ineffective_contact：有真实接触但未达到拉动目标。
- detachment：先接触及移动，抬升／侧移脱钩，最后接触早于结束至少 0.5 s。

没有 weld、虚拟吸附或物体随工具的位姿写入。“有效挂接”要求负 X 进展超过 5 mm，再判断接触期间的速度跟随，是明确标注的近似标签；接触真值仍来自求解器。

### Multi-Object Collision Chain
`collision_chain` / `CollisionChain-v1` 扩展 PokeCube 场景，保留物理握持的 peg，增加独立 B／C 刚体。
- direct_push：机器人操控 peg 推 A，B 放在传播路径外。
- two_body：工具→A→B，B 位移超过 1.5 cm。
- three_body：工具→A→B→C，真实 A–B、B–C 接触且运动起点顺序 A<B<C。
- near_miss：A 接近偏置 B，但无 A–B 力接触；B 位移小于 5 mm。
- failed_propagation：A–B 有接触，B 位移小于 1 cm。B 使用显式 5 kg／摩擦 0.8 模式覆盖，而非冻结状态。
- collision_free_motion：A–B 碰撞后解除接触，B 自由运动。

检查机器人／工具没有直接接触 B/C，排除伪传播。场景规模目前固定原生 A box，B/C 支持 box、cylinder；OOD composition 保留混合顺序作为 holdout。

### Free-Motion Interception
`free_motion_interception` / `FreeMotionInterception-v1` 扩展 RollBall，记录前设置球线速度及一致滚动角速度，之后全部由 PhysX 积分。
- interception／early：手与球实际碰撞，改变预先存在的自由运动。
- missed／late：因位置或动作时间错过，球持续运动且无机器人–球力接触。
- redirection：接触后有效移动速度的方向相对初速度改变超过 45°。
- no_intervention：同样运动初态，不干预。

目标球的点是解析球面点；panda_hand 的点是随真实 link 位姿变换的局部包围盒参考点，明确标为近似表面，不能当作手指或精确机器人网格点。

## 数据接口与泄漏边界
HDF5 `interaction-dynamics-v1`：5.5 s，每条 110 个 20 Hz 控制指令、111 帧观测、550 个 100 Hz 接触子步。每对象默认 12 个固定点。

- `observation/`：当前 RGB uint8、depth_m float32 米、intrinsic、world_to_camera（OpenCV convention）、time、robot_state（Panda 9 qpos＋9 qvel）。
- `action/command[N,7]`：实际提交的归一化 pd_ee_delta_pose 指令，顺序 dx,dy,dz,rx,ry,rz,gripper。平移／旋转是机器人根坐标系中的 delta，原生控制器缩放；gripper −1 关闭、+1 打开。本轮旋转指令为零。指令数值不等于实际 TCP 速度。
- `privileged/`：poses[T,O,7]（XYZ＋WXYZ）、velocities[T,O,6]（线／角速度）、local_points[O,P,3]、points[T,O,P,3]、point_ids、object_ids、link_ids、初始原生状态快照、physics_time、contact_state、impulse_Ns、force_N、contact_locations、phase、progress_displacement_m[T,O]（相对第一帧的位置位移）。
- ID 恒定且局部点只采样一次；世界点用每帧真实物体姿态变换。Link ID 为手 link 的原生索引；普通独立 actor 为 −1。
- 接触标签来自 SAPIEN CPU PhysX 每子步实际求解器点；任一点冲量 >1e−7 Ns 判为力接触。全部 raw contact points／separations 仍保留，正 separation 不用于否决求解器接触。初始持续接触被标为 left-censored，不误计新 onset。
- 成对冲量按 pair 方向归一；raw contact point 冲量保留引擎方向。force 是 impulse／物理 dt 的平均量，不是额外力传感器。
- motion onset 是位移超过 5 mm 的 20 Hz 标签；coupled_motion、engagement 和 phase 是基于真实接触及速度的近似标签，不能声称引擎提供了几何约束状态。

`model_window` 仅返回当前 RGB-D／校准／proprioception、当前点、允许的过去点及事先提交的未来指令。H0 无历史；H-self 只保留指定目标（默认 ID 1）；H-all 保留全部相关物体。point masking 遮住选中点的整段过去，object masking 按物理 object_id 遮住整对象的所有 link 过去，H-self 同样按 object_id 选中全部 link。固定当前点是可选 Oracle 输入设定，`include_current_points=False` 可移除此字段；不能把 Oracle 输入成绩直接当作纯 RGB 感知性能。速度、质量、接触、未来轨迹、成功标签均不在模型请求中；同一个文件的 privileged 分组只由 GT evaluator 读取。

## History 与 Counterfactual
每对记录 pair_id、type、held／changed variables、完整初态摘要、action ID、未来差异、当前 RGB/depth/proprio/pose 匹配误差及 accepted 标志。所有 history/future 都实际积分，状态写入仅发生在记录开始之前。

- Hidden velocity：运动球与静止球在 anchor=20 的当前姿态／图像匹配、未来动作相同，速度不同。逐字段比较全部非历史模型输入，Oracle 当前点的几微米差异会使默认 strict 标志为 false；移除当前 Oracle 点后可得到严格配对。RGB-D 匹配单独记录，不能据此声称所有输入严格相同。
- Action counterfactual：工具拉动和经过不接触，从相同完整 native initial state 开始，只改变事先提交动作；anchor=0。
- Contact history：一次早期真实拦截后继续运动，对照分支在当前球位姿静止，机器人状态匹配、未来动作相同；anchor=80。额外验证 A 在 anchor 前有真实目标接触、B 没有。
- 原工具式 contact-history 首次试验因当前可见状态不匹配被拒绝，保留 diagnostics-001 证据；不混入有效 pair。

同样观测却不同未来，用来检验 history；完全相同初态而不同动作，用来检验 action conditioning。模型是否学习了这些能力仍需后续训练／消融。本轮只实现和验收数据及接口。

诊断评价使用完整 pre-anchor history：例如 contact_history 调用 `model_window(path,80,history=80,future=30)`，才能覆盖早期真实接触；普通随机 window 默认 history=10。需要严格 Hidden Velocity 当前输入时，设置 `include_current_points=False`；在线入口对应 `--no-oracle-current-points`，预测器须支持此设定。stationary/CV smoke 需要当前点。

## Randomization 与 Split
保存 seed、family、完整配置、随机数值、mode overrides、运行时版本和源码 SHA。ID 尺度 0.94–1.06、目标质量 0.055–0.075 kg、摩擦 0.018–0.028、恢复系数 0.08–0.18；工具质量 0.10–0.13 kg、握持接触摩擦 0.8。布局、间距、角度、接触偏置、速度、动作起点和释放时刻亦随机化，真实指令和读数均保存。
- ID：新 family/seed，相同参数范围。family 的稳定 SHA 分到 train/validation/test，再切窗口；同一场景不同模式属于同 family。
- OOD Geometry：尺度 1.25–1.40，和 ID 尺度不重叠；目前是尺寸 holdout，不宣称任意新形状。
- OOD Physics：质量 0.13–0.17 kg、摩擦 0.045–0.055、恢复系数 0.45–0.60，不在 ID 范围。
- OOD Composition：只用于 collision_chain 的 three_body；box→cylinder→box，ID family0 为全 box、family1 为 box→cylinder→cylinder。组件出现过，完整组合未出现。拒绝把已见过的两体前缀误标为 composition OOD。
所有 OOD 只进入 test。诊断 pair 单独 diagnostic split。批量生成时至少使用两个 ID families，才能覆盖 composition 的训练组件。smoke 是验收样本，不是足够的正式训练集。

可选 `--independent-object-physics` 只用于 collision_chain：A/B/C 的质量、摩擦、恢复系数独立采样，2／3 物体模式保持相同 A/B 参数；工具请求速度 0.30–0.34 m/s、撞击角 ±0.025 rad 另行随机化。ID／OOD Physics 范围和基础配置一致，失败传播仍用显式 B 参数覆盖。该配置具有独立 family 标识，基础配置保留原重现性；新增 18 条 ID＋1 条 OOD Physics 全部通过。

## 可复现命令
需要 Linux CPU 原生 ManiSkill/SAPIEN 运行时和 Panda/table assets；已验证版本是 ManiSkill 3.0.1、SAPIEN 3.0.3、NumPy 2.0.2、Gymnasium 1.4.0。Python 依赖可用 `pip install -e '.[interaction,transport]'`；资产按 ManiSkill 原生下载机制安装。CPU 软件 Vulkan 如下，已有运行时可直接使用其 python；不占 GPU。

```bash
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=2
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --seeds 0 1 2 --families 2 --strict --output data/interaction_dynamics/id-run
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --tasks collision_chain --modes three_body --domain OOD_composition \
  --seeds 0 --strict --output data/interaction_dynamics/ood-composition
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --tasks collision_chain --independent-object-physics --seeds 0 1 2 \
  --strict --output data/interaction_dynamics/independent-physics
python -m dynamic_robot_bench.interaction.diagnostics \
  --seed 0 --strict --output data/interaction_dynamics/diagnostics-run
python -m dynamic_robot_bench.interaction.visualize \
  --input data/interaction_dynamics/id-run --output results/interaction-gallery
```

选择 `--tasks`／`--modes` 可单独生成各模式；OOD_geometry／OOD_physics 同样使用 `--domain`。每次使用新的 output；程序拒绝覆盖原数据。`tasks/interaction_dynamics/default.json` 保存默认协议及验收配置；它是可审查的配置说明，CLI 参数是实际运行入口。

## Online / Offline Evaluation
复用现有 XPolicyLab WebSocket RPC 的 observation/action envelope，预测端 `get_action` 返回 `{"points":...}`；返回点不会被当作机器人控制执行。先提交整段控制计划，在未来物理积分之前调用预测器，再积分和评价。
```bash
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --tasks collision_chain --modes three_body --seeds 0 \
  --online-predictor dynamic_robot_bench.interaction.baselines:stationary \
  --prediction-anchor 20 --prediction-future 70 --strict \
  --output data/interaction_dynamics/online-run
python -m dynamic_robot_bench.interaction.evaluate \
  --episode data/interaction_dynamics/online-run/ID_collision_chain_family000000_seed0_three_body.h5 \
  --prediction data/interaction_dynamics/online-run/ID_collision_chain_family000000_seed0_three_body.prediction.npz \
  --anchor 20 --future 70 --output results/interaction-metrics.json
python tools/validate_interaction_dynamics.py \
  --input data/interaction_dynamics/id-run --output results/interaction-validation.json
```
实际模型服务：设置 `INTERACTION_XPOLICY_ROOT` 指向项目已安装 transport、`INTERACTION_MODEL_URL` 为服务地址，使用 `--online-predictor dynamic_robot_bench.interaction_transport:websocket`。本地 smoke server：`python -m dynamic_robot_bench.interaction_transport --port 19875`。

指标包括 Object／Target／Moving-object ADE/FDE、per-object、motion propagation、phase-wise ADE、pair difference-of-differences response error、ID/OOD gap。没有显式 contact head 时 onset/release 为 null，不能从位置距离杜撰；显式 contact_probability 可按观测时间网格评价并报告未匹配事件，精确 native 接触 GT 始终保存。stationary／constant_velocity 只是可复现接口 smoke，不能作为训练后的 World Model 成绩。

## 实现文件与范围
- `interaction/config.py,environments.py,simulation.py`：参数 holdout、四注册环境、物理准备、预提交控制、100 Hz 真值。
- `geometry.py,data.py`：固定点、原子 HDF5、schema audit、输入屏蔽、family 切分。
- `diagnostics.py,evaluate.py,baselines.py,visualize.py`：物理诊断对、统一指标、接口 smoke、真实 GIF。
- `tasks/interaction_dynamics/runner.py`／`interaction_transport.py`：显式任务入口／既有服务连接。
- `tests/test_interaction_dynamics.py,test_interaction_transport.py`：旋转点运输、输入未来泄漏、split 泄漏、metric 和真实 WebSocket。
- 测试证据、运行路径与 GIF 数量见 validation.json 和 [VALIDATION.zh.md](VALIDATION.zh.md)。

已知限制：仅 CPU 单环境、小样本稳定性；接触有求解器短暂抖动，未经稳定接触窗口平滑；primitive 资产、基本随机范围；hand 是近似参考表面。没有加入 P1 新门／抽屉 link 或搬运滑移模式，保留已有 PickCube／关节／RoboCasa 路径。没有训练神经网络、没有修改旧 conveyor policy evaluator，也没有把旧不同机器人 schema 合并为同一种数据。

上游依据：[PullCubeTool](https://github.com/haosulab/ManiSkill/blob/v3.0.1/mani_skill/envs/tasks/tabletop/pull_cube_tool.py)、[PokeCube](https://github.com/haosulab/ManiSkill/blob/v3.0.1/mani_skill/envs/tasks/tabletop/poke_cube.py)、[RollBall](https://github.com/haosulab/ManiSkill/blob/v3.0.1/mani_skill/envs/tasks/tabletop/roll_ball.py)。实际安装源码 SHA 保存在每条 metadata；以安装源码与运行记录为验收依据。

