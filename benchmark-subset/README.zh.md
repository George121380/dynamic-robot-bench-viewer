# 模型首轮迭代：Benchmark 子集建议
建议先使用 **FreeMotionInterception-v1、ToolContactRelease-v1、CollisionChain-v1** 三个物理任务家族，按“自身历史 → 动作与接触 → 跨物体传播”的顺序迭代。只保留两个时选 **FreeMotion + CollisionChain**；只跑一个排查数据与模型链路时选 FreeMotion。保留既有 PullCubeTool 300 条 pilot 作回归。此结论是选型建议，**尚未在新任务上训练模型或证明 MAE 能改善未来预测**。

状态：2026-10-11 完成目录、数据、验收及既有实验复核；分支 `task/benchmark-subset-v1`，无 PR，未合并私人 main。环境代码沿用 `16c9aef`，本轮只新增 review JSON、双语文档及静态选型页生成器，不改任务或评估器。PhysMani 使用 `ab23d05` 与已发布的 2026-10-10 03:31 UTC 快照，不把快照中的运行状态当作当前实时状态。

[English](README.en.md) · [免认证选型页（含 GIF）](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-subset/) · [45 项机器可读取舍](review.json) · [既有交互验收](../interaction-dynamics/VALIDATION.zh.md) · [既有深度验收](../benchmark-tasks/depth/)

## 为什么先选这三个
研究需要分别判断历史、动作、跨物体信息是否帮助预测，而不仅是“历史重建变好”。三者使用同一 Panda、ManiSkill、7 维预提交 pd_ee_delta_pose 指令、20 Hz 观察／控制与 100 Hz 接触记录，完整 RGB-D、持续点和接触字段已经小样本验收。先保持机器人、坐标、控制语义和 schema 一致，有助于判断模型改动的作用。

上一轮工具任务实验已有警示：项目根目录 `dev/experiments/history-supervision-round3/REPORT.md` 的三个训练 seed 7/17/27 中，验证选中模型的目标测试 ADE 为 B3 0.397±0.024 mm、C3 0.405±0.036 mm；C/B 收益为 −0.0085 mm，家族 bootstrap 95% CI [−0.0221,+0.0046]，各 seed 收益方向不同。历史补全已经学会，但未来收益尚不稳定。它是旧 PullCubeTool pilot 的探索性结果，**不是新任务成绩**。原测试集已多轮查看，下一轮应建立新的冻结测试家族。

### 1. FreeMotionInterception：先验证 History
目标在机器人触碰前已有速度；同时保留 interception、missed、early、late、redirection、no_intervention。优先比较 H0 与 H-self 的接触前预测；恒速基线帮助判断网络是否只是在做速度外推。随后报告干预时机和接触后的方向／速度误差，防止自由运动部分掩盖碰撞后的失败。

已验收的 hidden-velocity 球诊断适合开发，但必须公平定义当前查询点。现有配对 RGB-D／proprio／未来指令可严格匹配；Oracle 当前点存在约 0.39–1.04 µm 的差异。主 point ablation 给所有分支相同类型的当前 P0 输入，明确其配对近似误差。严格 RGB-only 设置移除 P0 时，H0 不能同时失去随机采样 point_id 对应的空间定义，否则比较还包含点身份初始化的差别。可用物体中心／位姿指标或共享的固定查询定义解决；这一训练 adapter 尚未实现／验收。

[RGB + XYZ 点轨迹 + 接触 GIF](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/media/ID_free_motion_interception_family000000_seed0_interception.gif) — **原生仿真深度真值，单位米**。

### 2. ToolContactRelease：验证动作、接触与解除
保留 engage_pull、near_miss、contact_release、failed_engagement，预测目标方块。相同初态不同预提交动作的 action-counterfactual 已验收；比较“有接触／无接触／无效接触”和解除后的运动。动作输入始终是事先提交的控制指令，不能用未来实际 TCP 轨迹替代。

HookPullDynamics 使用同一个 L 工具环境，success/miss/ineffective 三类与该协议高度重合；首轮不作为独立任务计数。需要几何脱离难例时再加入其 detachment 模式。原 PullCubeTool 300 条 pilot 保留回归；上游 PullCubeTool、PokeCube、RollBall 的公开示范可以补充覆盖，但成功示范本身不保证历史必要性或负样本平衡。

[RGB + XYZ 点轨迹 + 接触 GIF](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/media/ID_tool_contact_release_family000000_seed0_contact_release.gif) — **原生仿真深度真值，单位米**。

### 3. CollisionChain：主跨物体任务
采用已验收的 `--independent-object-physics` 配置，A/B/C 质量、摩擦和恢复系数独立采样；覆盖 direct_push、two_body、three_body、near_miss、failed_propagation、collision_free_motion。B/C 运动由真实 A–B、B–C 碰撞传播，验收排除了工具／机器人直接推动 B/C。

重点预测 **B（object_id=2）和 C（object_id=3）**，而非默认 ID 1 的 A。在 B/C 尚未开始运动、上游物体已运动的窗口比较 H-self/H-all，再遮蔽 A 或工具的过去。所有分支保留相同当前几何和查询点，只改变历史可见性；否则 H-all 收益也可能来自当前场景信息不同。分别报告 B/C 的 per-object ADE、运动传播顺序和阶段误差，不能被 A／工具或静止点平均值稀释。

当前诊断生成器没有已验收的“链中上游速度不同、当前可见几何及未来动作相同”配对。这是最值得下一步补充的诊断，不能把现有球诊断当作链式证明。历史打乱只是输入消融，不能称为物理有效 counterfactual。

[RGB + XYZ 点轨迹 + 接触 GIF](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/media/ID_collision_chain_family000000_seed0_three_body.gif) — **原生仿真深度真值，单位米**。

该 GIF 展示基础 profile 的 three_body 验收样本；独立物理参数批次的数值验收单独保存，不把此图当作该批次录像。

## 数据能否直接用
- 基础 acceptance-006：三个核心任务合计 **48 条／9 个 scene families，train/validation/test=42/0/6**。FreeMotion 是 18/0/0；Tool 是 12/0/0；Chain 是 12/0/6。四协议全量为 60 条／12 个 families。
- independent-physics-002 碰撞链另有 **18 条 ID（12/6/0）**，另有 1 条 OOD Physics。它补充了链的 validation，却没有补齐工具、自由运动任务的三方划分。
- 两种物理 profile 的 family 字符串不同，会独立哈希；相同基础 seed/family 的布局和控制可能共享来源。首轮固定一个 profile，或在数据整理中新增父场景分组，避免相关变体跨 split。该父场景字段尚未实现。
- 旧 40 个可获取深度条目已跑通 39 个独立样本，共 468 帧；这些通常是 12 帧读取／重渲染 smoke，**不是完整训练 rollout**，也不自动证明 persistent-point／contact adapter 已完成。
- RoboCasa 八项已重放原始状态生成 RGB-D，但尚未验收动作重新执行的物理一致性、link 绑定点和接触 GT。PhysMani RGB-D 与官方 Dataset 读取路径更成熟；全 16 任务合计 12/12 资产、32 条 expert/WM 包、发布 3DFA 3,200 条评估已有证据，持续点 GT 未验收。不能将“能读深度”等同于“可直接混入当前 point-world-model 训练”。

## 第一轮怎样迭代（建议，未执行）
1. 先只用 ID、一个确定的物理 profile。每个任务枚举 100 个 `(family,seed)` 场景家族，4/6/6 模式合计 **1,600 条候选 rollout**。以已有 family 哈希规则预期约 70/20/10 划分，生成前检查实际覆盖；不是保证恰好 70/20/10。所有模式、配对和同源变体先分组再切窗口。失败轨迹、验收标准与拒收原因全部保留。
2. 现有 9 对诊断用于开发；建议另建每类约 30 对未看过的 hidden-velocity、action-counterfactual、contact-history 配对。新增上游隐藏速度 chain pair 需单独实现和逐字段匹配验收。这个数量是起步预算，不是统计功效保证。
3. 按任务、正负模式、运动和接触事件平衡采样，报告 0.2/0.5/1.0 s 时距。窗口覆盖碰撞前、接触建立、接触解除和后续自由运动；不以大量静止点压低平均误差。2/3 目标数混合 batch 需要明确 entity-valid mask。
4. 固定当前输入、未来控制、模型规模、训练预算和验证选 checkpoint 规则：H0 → H-self → H-all → H-all + MAE；再做 point/object history masking。先确认 H-self 在 FreeMotion 有效，再看 H-all 对 B/C 的作用，最后看 MAE 是否改善未来指标。历史重建误差单独报告。
5. 三个训练 seeds、按 scene family 做成对差异及区间；报告 stationary/CV、moving-target B/C、phase-wise、动作响应和之后的 ID/OOD gap。没有 contact head 时不从点轨迹强推接触时刻。三个 seeds 仍只提供有限重复证据。
6. 泛化第二步再加：PushT 的偏心推动／旋转；OOD Physics、OOD Geometry、OOD Composition。OOD 必须冻结 held-out 范围／组合，不能只换 seed。

现有采集接口可以先生成选定任务。以下是已有入口的 **小样本命令**，本轮未执行；不是 1,600 条正式计划的替代，Linux 运行时要求见 [实现文档](../interaction-dynamics/README.zh.md)：
```bash
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --tasks free_motion_interception tool_contact_release --seeds 0 1 2 \
  --families 2 --strict --output data/interaction_dynamics/subset-dev-free-tool
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --tasks collision_chain --independent-object-physics --seeds 0 1 2 \
  --families 2 --strict --output data/interaction_dynamics/subset-dev-chain
```
当前 runner 没有 B/C target selector CLI；训练／输入 adapter 需调用 `model_window(...,target_id=2)` 或 `target_id=3`，并在评价报告显式筛选对应 per-object 指标。不能把上面的默认 H-self online smoke 当作完成 B/C 消融。

## 后续公开任务怎样选
- **PushT-v1**：最先追加。非对称 T 几何和偏心接触补充当前 cube/ball 中不足的旋转与力矩；仍在 ManiSkill 中，接口改动小。
- **PhysMani**：先选 `pick_moving_target_on_the_table` 与 `push_moving_button` 两个基础任务，正常／高速成对验证。两者比旋转插入、容器放置更容易隔离动态感知和动作时机。只有高速完全排除训练时，才能把它称为速度 OOD。原官方 16-task policy 成功率与本项目 point forecast 误差分开；先补持续点及控制 adapter。官方开放任务和训练数据见 [PhysMani](https://github.com/vLAR-group/PhysMani)，本地进展使用 [已发布快照](https://peiqil.com/dynamic-robot-bench-viewer/physmani/progress.json)。
- **RoboCasa**：先 OpenDrawer，再 CloseFridge，用滑动／铰链两类关节约束验证 per-link 点。SlideDishwasherRack、SlideToasterOvenRack 作为抽屉的替代选择，不一起扩首轮。官方模型状态／场景文件支持数据重放，但不等于本项目新增接触标注已完成；保留官方 pretrain/target 划分、原成功条件和确切版本，见 [官方任务](https://robocasa.ai/docs/build/html/tasks/atomic_tasks.html)、[官方数据格式与划分](https://robocasa.ai/docs/build/html/datasets/using_datasets.html)。
- **Conveyor**：保留 L1 固定带速的外部在线验证。L2/L3 包含语义记忆、双臂及外生带速调度；若未来调度不可见，精确确定性未来不是可辨识目标，需条件化或不确定性评价。
- MOVi-C 可做无动作 representation pretraining，CoPhy/Physion 可做外部被动诊断；这些都不能替代机器人 action-conditioning 主任务。CLEVRER 缺少本项目已验证的像素深度／持续 3D 点 GT，不将模型估计深度当作真实几何监督。

新 P0 任务复用上游常用资产／环境，但新模式和验收器是项目自定义协议。三 seeds、60 条通过说明小样本功能成立，不能保证不存在隐藏 bug，也不等于整个协议已得到社区验证。下一轮应使用冻结数据清单、独立点位姿审计及 fresh families 复验。[ManiSkill 上游任务](https://maniskill.readthedocs.io/en/latest/tasks/table_top_gripper/index.html) 和 [公开 demonstrations](https://huggingface.co/datasets/haosulab/ManiSkill_Demonstrations/tree/main/demos) 可作外部锚点。

## 完整条目取舍
复核范围是原 42 个目录条目（含 PhysMani 总览）加 4 个新协议；合并总览后下面列 **45 个具体条目**。速度变体、数据集和共享物理环境不作为独立任务家族计数。已有数据数量沿用选定版本的注册／轨迹元数据；不表示本机下载了完整公开集。

1. **[match_and_pick_from_conveyor](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#match_and_pick_from_conveyor) — 后续外部验证**。移动支撑、抓取、语义记忆。保留在线外部测试，先 L1 固定带速；L2/L3 的未来外生调度未知时不能要求确定性精确预测。
   - 数据：官方 100 条；项目 v4 20 / v5 3 条合格。
   - [深度：已新采 RGB-D · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#match_and_pick_from_conveyor)。真实 Isaac Sim 场景新采 RGB-D；保持机器人状态，验证传送带运动及传感器，未评测抓取成功。

2. **[push_puck_collision](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#push_puck_collision) — 已有回归**。两物体碰撞、自由滑动。原试采 27 条/受限 y 控制，最新深度 smoke 没有 A-B 碰撞；采用已校准成功批次作回归，核心用新链任务。
   - 数据：项目自采 27 条；无匹配标准公开集。
   - [深度：已新采 RGB-D · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#push_puck_collision)。现有 CollisionEnv 新采深度。该样本因 second_strike 失败，未发生 A–B 碰撞；不是成功示范。

3. **[PandaFingerArticulationDiagnostic-v0](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PandaFingerArticulationDiagnostic-v0) — 链路检查**。link 身份与关节运动。验证 link-bound 点变换，不能当环境操作成功或完整 articulated benchmark。
   - 数据：自定义任务；项目 2 source episodes。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PandaFingerArticulationDiagnostic-v0)。项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。

4. **[RollBall-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#RollBall-v1) — 合并／复用**。推动滚动球。由自由运动家族覆盖；原生从静止开始，不能仅凭 task 名声称其验证隐藏速度。
   - 数据：选定 RL 轨迹元数据 855 episodes。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#RollBall-v1)。项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。

5. **[PullCubeTool-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PullCubeTool-v1) — 已有回归**。标准工具拉动。保留已有 300 条 Oracle pilot 回归和公开来源锚点；不要把旧测试反复当新模型的最终测试。
   - 数据：motionplanning 1,000 episodes。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PullCubeTool-v1)。项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。

6. **[PokeCube-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PokeCube-v1) — 合并／复用**。握杆推单物体。由 CollisionChain 的 direct_push 覆盖；公开示范需筛查绕过 peg 的路径。
   - 数据：选定 RL 轨迹元数据 579 episodes。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PokeCube-v1)。项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。

7. **[PickCube-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PickCube-v1) — 链路检查**。抓取、抬升、释放。仅作相机、动作、抓取数据链路 sanity；成功示范本身通常不足以验证动态历史。
   - 数据：motionplanning 1,000 episodes。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PickCube-v1)。项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。

8. **[PushT-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PushT-v1) — 下一项追加**。偏心接触、平面转动。第一项追加候选：补充当前简单球/方块任务的转动、接触点和非对称几何。
   - 数据：选定 RL 轨迹元数据 719 episodes。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PushT-v1)。项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。

9. **[OpenDrawer](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#OpenDrawer) — 后续外部验证**。平移关节、把手接触。RoboCasa 首选：关节单一、阶段清楚，原状态深度已跑通；需补 link 点、真实接触及动作重放。
   - 数据：human pretrain 100 / target 500；MG 10k；单轨迹原状态 RGB-D 已重渲染，非完整训练 adapter。
   - [深度：已按原状态生成深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#OpenDrawer)。原 XML／状态／相机重渲染；与原视频 RGB MAE 8.25/255。本页 RGB 与 depth 为同次新渲染。

10. **[PanTransfer](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PanTransfer) — 后期扩展**。抓取、搬运、放置。适合以后检验抓持/释放；长程与复合任务引入规划因素，不能借 target 集决定 pretrain 划分。
   - 数据：human target 500；无注册 pretrain／MG；单轨迹原状态 RGB-D 已重渲染，非完整训练 adapter。
   - [深度：已按原状态生成深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PanTransfer)。原 XML／状态／相机重渲染；与原视频 RGB MAE 6.47/255。本页 RGB 与 depth 为同次新渲染。

11. **[CloseFridge](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#CloseFridge) — 后续外部验证**。铰链门、解除接触。RoboCasa 第二项：与抽屉形成平移/转动约束对照；先验收逐 link 点身份。
   - 数据：human pretrain 100 / target 500；MG 10k；单轨迹原状态 RGB-D 已重渲染，非完整训练 adapter。
   - [深度：已按原状态生成深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#CloseFridge)。原 XML／状态／相机重渲染；与原视频 RGB MAE 11.60/255。本页 RGB 与 depth 为同次新渲染。

12. **[SlideDishwasherRack](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#SlideDishwasherRack) — 替代选择**。滑轨关节。与 OpenDrawer 重复平移约束；作替代或后续 fixture 泛化，首轮不同时加入。
   - 数据：human pretrain 100 / target 500；MG 10k；单轨迹原状态 RGB-D 已重渲染，非完整训练 adapter。
   - [深度：已按原状态生成深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#SlideDishwasherRack)。原 XML／状态／相机重渲染；与原视频 RGB MAE 2.96/255。本页 RGB 与 depth 为同次新渲染。

13. **[StackBowlsCabinet](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#StackBowlsCabinet) — 后期扩展**。堆叠、支撑接触。丰富支持约束但多阶段/遮挡较多；在简单接触学习稳定后再加入。
   - 数据：human pretrain 100 / target 500；无 MG；单轨迹原状态 RGB-D 已重渲染，非完整训练 adapter。
   - [深度：已按原状态生成深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#StackBowlsCabinet)。原 XML／状态／相机重渲染；与原视频 RGB MAE 2.65/255。本页 RGB 与 depth 为同次新渲染。

14. **[CoffeeSetupMug](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#CoffeeSetupMug) — 后期扩展**。抓取、容纳与相对位姿。更适合综合操作/视觉泛化；当前主要动态增量有限。
   - 数据：human pretrain 100 / target 500；MG 10k；单轨迹原状态 RGB-D 已重渲染，非完整训练 adapter。
   - [深度：已按原状态生成深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#CoffeeSetupMug)。原 XML／状态／相机重渲染；与原视频 RGB MAE 6.29/255。本页 RGB 与 depth 为同次新渲染。

15. **[SlideToasterOvenRack](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#SlideToasterOvenRack) — 替代选择**。滑轨关节。与 OpenDrawer 重复平移约束；作替代或后续 fixture 泛化，首轮不同时加入。
   - 数据：human pretrain 100＋MG 10k；无 target；单轨迹原状态 RGB-D 已重渲染，非完整训练 adapter。
   - [深度：已按原状态生成深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#SlideToasterOvenRack)。原 XML／状态／相机重渲染；与原视频 RGB MAE 2.99/255。本页 RGB 与 depth 为同次新渲染。

16. **[StirVegetables](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#StirVegetables) — 后期扩展**。多小物体与工具接触。交互丰富，但遮挡、资产和成功判据/接触标注适配更复杂；不作首轮主指标。
   - 数据：human pretrain 100 / target 500；无 MG；单轨迹原状态 RGB-D 已重渲染，非完整训练 adapter。
   - [深度：已按原状态生成深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#StirVegetables)。原 XML／状态／相机重渲染；与原视频 RGB MAE 7.12/255。本页 RGB 与 depth 为同次新渲染。

17. **[ToolHang](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#ToolHang) — 后期扩展**。装配、几何支撑约束。几何关系有价值；先用简单 L 工具隔离挂接，再做完整装配与多资产测试。
   - 数据：robomimic PH 200 条人类成功示范。
   - [深度：已按原状态生成深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#ToolHang)。原 demo_0 完整 MuJoCo 状态重渲染 RGB-D；尚无原 RGB 逐像素对照。

18. **[reach_and_drag](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#reach_and_drag) — 替代选择**。工具拖动/清扫。已有新专家 RGB-D；可作跨引擎工具泛化，但持续点/真实接触及 grasp 语义需验收。
   - 数据：PerAct：每任务 train/val/test 100/25/25。
   - [深度：已新采 RGB-D · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#reach_and_drag)。新采 RLBench 专家示范；任务 Python/TTM 与 PerAct 固定版本相同，未读取作者 Drive 归档。

19. **[MOVi-C](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#MOVi-C) — 可选预训练**。被动多物体运动/遮挡。4D 表征预训练首选辅助：RGB-D 和三维 GT 丰富，但无机器人动作，持续点适配尚需验证。
   - 数据：TFDS 128² v1.0.0：9,737/250/999。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#MOVi-C)。官方 TFRecord 原生深度；数值为 ray distance，反投影前须转 Z。

20. **[CoPhy](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#CoPhy) — 被动诊断**。物理反事实。Blocktower 已新采带深度；适合后续被动物理诊断，不代替机器人动作条件测试。
   - 数据：作者 224² 集约 18 GB＋split 文件。
   - [深度：已新采 RGB-D · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#CoPhy)。仅 Blocktower：作者函数和 URDF 的新 RGB-D 序列；没有执行完整 AB/CD 协议或其他子集。

21. **[AdroitHandHammer-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#AdroitHandHammer-v1) — 后期扩展**。灵巧抓持、撞击。原 D4RL 状态可重渲染，但 26D 控制/手部接触复杂，首轮加入会混淆接口与模型问题。
   - 数据：Minari human-v2：25 episodes / 11,310 steps。
   - [深度：已按原状态生成深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#AdroitHandHammer-v1)。原 D4RL qpos/qvel/board_pos 重渲染；所选 Minari 实文件只有 success，没有完整状态。

22. **[Physion-v1.5-OCP](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#Physion-v1.5-OCP) — 被动诊断**。物体接触预测。可用 Collide 作外部接触诊断；发布 OCP 标签与稠密持续点预测不是同一任务，避免下载全库起步。
   - 数据：7 类 readout train＋test，14 个 zip。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#Physion-v1.5-OCP)。原始 TDW float32 深度和矩阵；同帧 RGB-D 从 1024² 同步步进采样为 256²。

23. **[sweep_to_dustpan_of_size](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#sweep_to_dustpan_of_size) — 替代选择**。工具拖动/清扫。已有新专家 RGB-D；可作跨引擎工具泛化，但持续点/真实接触及 grasp 语义需验收。
   - 数据：PerAct：每任务 train/val/test 100/25/25。
   - [深度：已新采 RGB-D · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#sweep_to_dustpan_of_size)。新采 RLBench 专家示范；任务 Python/TTM 与 PerAct 固定版本相同，未读取作者 Drive 归档。

24. **[CLEVRER](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#CLEVRER) — 被动诊断**。碰撞事件推理。有视频/事件，但无已验收像素深度与持续 3D 点；后续事件诊断，首轮不引入估计深度 GT。
   - 数据：20,000 视频：10k/5k/5k。
   - [深度：现有视频需估计深度](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/)。标准发布无像素深度；对象三维中心标注不等于表面深度。

25. **[TurnFaucet-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#TurnFaucet-v1) — 暂缓／受阻**。旋转关节。匹配 v1 资产/数据未验收，旧 v0 GIF 不是 v1 证据。
   - 数据：当前官方示范注册表未找到 v1。
   - [深度：v1 深度待确认](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/)。匹配 v1 数据／资产尚未验收；v0 GIF 只是动作参考。

26. **[beat_the_rotating_buzz](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#beat_the_rotating_buzz) — 后期扩展**。击打旋转目标。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#beat_the_rotating_buzz)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

27. **[beat_the_rotating_buzz_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#beat_the_rotating_buzz_high_speed) — 后期扩展**。击打旋转目标。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#beat_the_rotating_buzz_high_speed)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

28. **[insert_onto_rotating_peg](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#insert_onto_rotating_peg) — 后期扩展**。旋转 peg 插入。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#insert_onto_rotating_peg)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

29. **[insert_onto_rotating_peg_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#insert_onto_rotating_peg_high_speed) — 后期扩展**。旋转 peg 插入。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#insert_onto_rotating_peg_high_speed)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

30. **[pick_moving_target_on_the_table](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#pick_moving_target_on_the_table) — 后续外部验证**。运动目标抓取。PhysMani 最先选这两类正常/高速任务；先验证点 GT 与时间动作语义，再检验在线时机。高速只有在训练明确排除后才是 speed holdout。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#pick_moving_target_on_the_table)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

31. **[pick_moving_target_on_the_table_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#pick_moving_target_on_the_table_high_speed) — 后续外部验证**。运动目标抓取。PhysMani 最先选这两类正常/高速任务；先验证点 GT 与时间动作语义，再检验在线时机。高速只有在训练明确排除后才是 speed holdout。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#pick_moving_target_on_the_table_high_speed)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

32. **[place_cups_on_rotating_frame](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#place_cups_on_rotating_frame) — 后期扩展**。旋转支架放杯。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#place_cups_on_rotating_frame)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

33. **[place_cups_on_rotating_frame_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#place_cups_on_rotating_frame_high_speed) — 后期扩展**。旋转支架放杯。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#place_cups_on_rotating_frame_high_speed)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

34. **[remove_cups_from_rotating_frame](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#remove_cups_from_rotating_frame) — 后期扩展**。旋转支架取杯。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#remove_cups_from_rotating_frame)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

35. **[remove_cups_from_rotating_frame_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#remove_cups_from_rotating_frame_high_speed) — 后期扩展**。旋转支架取杯。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#remove_cups_from_rotating_frame_high_speed)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

36. **[put_rubbish_in_moving_bin](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#put_rubbish_in_moving_bin) — 后期扩展**。运动容器投放。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#put_rubbish_in_moving_bin)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

37. **[put_rubbish_in_moving_bin_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#put_rubbish_in_moving_bin_high_speed) — 后期扩展**。运动容器投放。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#put_rubbish_in_moving_bin_high_speed)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

38. **[push_moving_button](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#push_moving_button) — 后续外部验证**。运动按钮接触。PhysMani 最先选这两类正常/高速任务；先验证点 GT 与时间动作语义，再检验在线时机。高速只有在训练明确排除后才是 speed holdout。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#push_moving_button)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

39. **[push_moving_button_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#push_moving_button_high_speed) — 后续外部验证**。运动按钮接触。PhysMani 最先选这两类正常/高速任务；先验证点 GT 与时间动作语义，再检验在线时机。高速只有在训练明确排除后才是 speed holdout。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#push_moving_button_high_speed)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

40. **[moving_basketball_in_hoop](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#moving_basketball_in_hoop) — 后期扩展**。移动球/球框投放。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#moving_basketball_in_hoop)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

41. **[moving_basketball_in_hoop_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#moving_basketball_in_hoop_high_speed) — 后期扩展**。移动球/球框投放。保留后续外部动态验证；多阶段抓放/精细几何和脚本驱动运动会掩盖首轮表征与接触问题，速度变体不是独立交互家族。
   - 数据：全 16 任务合计：12/12 资产、32 条采集/WM 包已验收；发布 3DFA 3,200 条评估（2026-10-10 快照）；持续点 GT 未验收。
   - [深度：已读取深度 · 12 帧小样本](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#moving_basketball_in_hoop_high_speed)。项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。

42. **[ToolContactRelease-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/) — 首轮核心**。工具接触、释放、动作条件。验证接触与近失、解除后运动，以及相同初态不同动作；已有工具 pilot 可作回归。
   - 数据：3 seeds、所有模式通过；RGB-D/持续点/接触完整；仅小样本验收。
   - [深度：原生仿真深度真值（米）](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/)。与完整 RGB／持续 XYZ 点／100 Hz 接触数据同步。

43. **[HookPullDynamics-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/) — 合并／复用**。几何挂接、脱钩。与 ToolContactRelease 共享 L 工具和实现；合并为工具家族，可加 detachment，不能算独立研究覆盖。
   - 数据：3 seeds、所有模式通过；RGB-D/持续点/接触完整；仅小样本验收。
   - [深度：原生仿真深度真值（米）](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/)。与完整 RGB／持续 XYZ 点／100 Hz 接触数据同步。

44. **[CollisionChain-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/) — 首轮核心**。跨物体传播、上游历史。首轮跨物体主任务；重点预测 B/C，使用独立 A/B/C 物理参数。上游隐藏速度的链式配对尚未验收。
   - 数据：3 seeds、所有模式通过；RGB-D/持续点/接触完整；仅小样本验收。
   - [深度：原生仿真深度真值（米）](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/)。与完整 RGB／持续 XYZ 点／100 Hz 接触数据同步。

45. **[FreeMotionInterception-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/) — 首轮核心**。运动中拦截、隐藏速度。先验证 H-self 是否优于 H0，再测试动作时机与碰撞后速度；有已验收隐藏速度诊断。
   - 数据：3 seeds、所有模式通过；RGB-D/持续点/接触完整；仅小样本验收。
   - [深度：原生仿真深度真值（米）](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/)。与完整 RGB／持续 XYZ 点／100 Hz 接触数据同步。

## 产物、复现与限制
`docs/benchmark_subset/review.json` 是本轮 45 项的双语结构化来源；`tools/build_benchmark_subset.py` 从该文件输出免认证静态页，复用已有 GIF，显示每项深度状态。生成器不模拟、不采数据、不调用模型：
```bash
python tools/build_benchmark_subset.py --output results/benchmark-subset-site
python -m http.server 8765 --directory results/benchmark-subset-site
```
静态页包含三个实际 RGB/XYZ/contact GIF、45 项搜索／分类、中英文和原任务／深度链接。采集、在线／离线评价沿用 [现有命令](../interaction-dynamics/README.zh.md)，本轮没有重新跑原 69 项物理测试或改变其结果。发布前检查条目、锚点、GIF 和页面交互；验证结果另记 `checks.json`。本轮尚未实现模型训练 adapter、父场景分组、B/C hidden-state chain pair 或新增持续 link 点；它们是进入正式实验前的具体工作项。
