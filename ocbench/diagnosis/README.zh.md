# Bowling 效果差：模型失败诊断

**结论：Bowling v3 主要学到了抑制静止瓶误动，尚未可靠预测球–瓶–瓶传播。最直接的两处问题是：当前选模目标奖励保守预测，且入射球轨迹在第一次碰撞前已经偏离。** 模型结构、训练分布和时间粒度也有明显不匹配，但尚无单因素实验可以把失败唯一归因于它们。

本次核对最新 PointWorld v3 代码、全点指标、13 次验证记录、原生数据及展示子集；重新计算验证集静止基线，并做按轨迹重采样的误差分析。**未运行新的模型训练、GPU 推理，也未更换旧实验 checkpoint。** 另对最早三个 CPU 专家示范做了 15 条控制器诊断，必须与学习模型成绩分开。无新 PR，分析代码在 benchmark 独立分支。

## 1. 先确定差在哪里

同一批 30 条新测试、4 秒预测：

- 全瓶 ADE：v2 **4.13 cm** → v3 **2.00 cm**；完全不动基线 **1.54 cm**。
- 运动瓶 ADE：**5.34 → 5.23 cm**；不动基线 **5.46 cm**。v3 相对不动仅改善 **2.32 mm / 4.25%**。
- 运动瓶 FDE：**11.83 → 14.08 cm**，末帧恶化。
- 派生倒瓶检出：v2 **53 TP / 116 FP / 23 FN**；v3 **0 / 0 / 76**。这些是从预测点刚体拟合得到的诊断，仿真真值仍使用引擎倾倒状态。
- 30 条共 300 瓶，其中 **95 个运动、205 个静止**；不能只看整体 ADE。v3 静止误动率 25.6% 是先按轨迹平均；逐瓶为 44/205，分母不同。

按 18 条运动轨迹成对 bootstrap，v3 相对不动的运动 ADE 改善 95% 区间 **0.27–4.59 mm**（10,000 次、固定 seed）。这是已查看数据上的探索性分析；小幅点误差改善与完全漏掉倒瓶可以同时成立，不能因此称动态预测成功。

![真实双视角 / GT / v2 / v3：seed3004](https://peiqil.com/dynamic-robot-bench-viewer/pointworld/bowling-v3/seed3004.gif)

该例真值有 7 瓶运动、6 瓶倾倒；展示每瓶 45 点，v3 各瓶最大平均位移仅 **0.58–0.72 cm**，运动瓶真值为 **3.11–24.83 cm**。这些展示子集数值只解释画面，全点成绩来自独立报告，未用展示抽样代替评测。

## 2. 证据最强：选模会淘汰有动态响应的模型

实际公式：`0.5 × (运动瓶 ADE + 全瓶 ADE) + 2 cm × 静止误动率`，越低越好。

- 被选择的 **step1500**：验证运动 ADE **5.44 cm**，FDE **13.71 cm**，倒瓶 **0 TP / 0 FP / 48 FN**，分数 **4.37 cm**。
- **step2750**：运动 ADE **5.14 cm**，FDE **10.79 cm**，倒瓶 **24 TP / 19 FP / 24 FN**，分数 **5.10 cm**。后期不是从未产生动态响应，而是响应伴随更多误动，被当前公式淘汰。
- 本次从原验证 GT 重新算出的**完全静止基线分数为 3.82 cm，比全部 13 个验证 checkpoint 更好**。这不是实际选中了静止 baseline，而是说明目前衡量方式允许“什么都不动”获得更好的目标值。

建议预先固定新的验证协议：同时报告运动瓶 ADE/FDE、倒瓶 precision/recall 和静止误动，采用明确的折中或最低动态性能门槛。避免简单换成只追求 recall，否则会退回 v2 大量误报。不能用这批已查看测试重新挑 checkpoint；下一轮新留出再确认。删除误动惩罚也不保证 step2750 胜出，因为全瓶 ADE 项仍偏保守。

## 3. 上游球运动预测已经错了

18 条有碰撞的测试，首次真实球–瓶接触前：

- 球点 ADE：v2 **7.01 cm** → v3 **7.89 cm**。
- 最后一个接触前输出的可见球点质心误差：**11.99 → 14.11 cm**。它不是拟合球心；这是对应物理点集的差，不能直接当作中心或法向接触误差。
- 球半径 **4.25 cm**。这样的入射轨迹误差足以让“撞上谁、什么时候撞、是否擦过”失去可靠性；后续多次传播会受影响。没有直接从预测点计算接触真值。

真实未来机器人路径的独立诊断仍漏掉 **76/76** 倒瓶；同一主模型换成真实路径也没有恢复。**机器人计划偏差不是目前唯一瓶颈**；这不证明它完全无关。需要在数据修正、训练容量、动作映射和传播机制之间继续区分。

## 4. 为何容易落到保守解：事实和假设分开

**数据／优化事实：** 206 条训练中仅 94 条有运动瓶，训练瓶–时刻有 **12.8%** 超过 1 cm 位移，87.2% 尚未运动或始终不动；碰撞前早期点也被计入不动。v3 采样整条 episode 均匀，平均损失权重为球 42.2%、运动瓶 18.9%、静止瓶 23.9%、背景 15.0%。权重质量不等于梯度贡献。2 cm Huber 会截断大残差的梯度幅度，在精确命中与 miss 的分支难以辨识时，可能更偏向常见小运动；不是证明 Huber 必然导致失败。v2 的运动加权仍有大量误报，所以只调一个权重不够。

**结构事实：** 这轮使用 small-DROID，PointTransformer 联合处理当前场景点与机器人计划点；一个 head 一次输出 10 个未来点偏移。它有跨点交互能力，不能说模型“没有 attention”。但没有显式被动物体速度状态、逐步碰撞求解或 contact/phase loss；已记录 contact 标签没有进入这轮训练。跨物体运动传播和刚体旋转需要从点回归中隐式学到。206 条、单种子、约 51M 可训练参数不足以判断结构上限，且尚未提供训练子集过拟合检验。

**时间事实：** 500 Hz 求解器接触，模型仅每 **0.4 s** 输出一次，一次预测 **4 s**。直接输出长序列、缺少阶段监督，使接触时刻和传播顺序缺少训练约束。先测试更短窗口和接触附近密集监督，才能判断影响，不能仅凭采样频率断言其无法预测末帧。

**History 事实：** `context_frames=1`；编码器只读取 scene 第 0 帧，重复 11 次当前点并不构成历史。所有 query 选在推球前，球速近零。因此这次并没有验证你的 **4D MAE + H-all / masking**；单帧与历史的差异不能用它回答。加入过去全是静止的帧也不一定有帮助。需新增推出后、接触前／后 query，使用同一当前几何和动作的速度／接触历史配对，并让模型读取真实历史。

已有跨设备输入、点 ID、时间、权重恢复和 416 份全点预测核对通过，支持“不是一个已知的展示／标签错位造成全部失败”，但不等于排除了所有实现 bug。真值深度、固定物理、单训练 seed 等限制保留。

## 5. 建议下一轮按机制排查

1. **先做 8–16 条训练轨迹过拟合检查**：固定窗口，分别观察球轨迹、运动瓶 FDE、倒瓶召回和静止误报。若训练样本都学不会，先查动作编码、损失、归一化和梯度；若能学会而新场景失败，再扩大覆盖。尚未执行。
2. **拆开三段：机器人→球、球→一瓶、一瓶→另一瓶**。用简化 CollisionChain 和短期查询诊断；球短期入射预测达到厘米级之前，不把整排 4 秒结果当唯一目标。逐物体、逐 phase 宏平均，并保持负样本。
3. **重设验证折中并分层采样**：hit/miss、正中/擦边、一次/多次传播；提高真正接触后的运动瓶时刻的覆盖，同时监督未接触的静止点。所有阈值在下一轮测试前冻结。
4. **针对研究目标增加历史**：推出后 query 做 H0/H-self/H-all 和 upstream object masking，保持当前点、RGB-D、未来命令、split 相同。Oracle 速度／接触只用于标签或明确的诊断上界，不能进入主模型输入。
5. **再做传播能力诊断**：单独提供真实球运动的 Oracle 条件可以隔离下游问题，但属于不可部署上界，需单列；若球已准而瓶仍不动，再尝试 contact/phase 辅助监督、刚体约束或递推表示。不能把该上界计入主成绩。

## 6. 最早专家 GIF 的零分是另一件事

早期 smoke 的 seed0/1/2 是 **8/0/0 瓶**，不是网络预测。所有三条原始 qpos/qvel/actions 本次重新运行与旧 HDF5 逐位一致。

- seed1：随机瞄准理想线到最近瓶中心仍相距 **12.0 cm**；原始夹爪释放后实际 heading 38.7°，通过头瓶那一行时横向偏 **18.1 cm**。只把瞄准改为头瓶中心，同一 reset 从 **0 → 8 瓶**。
- seed2：计划 heading **−9.2°**，释放后实际 **+36.8°**，约 **46.0°** 偏差，横向偏 **42.6 cm**。瞄准／侧偏／姿态的四个小对照均未救回，接触执行具有明显敏感性。
- 把所有扰动去掉也不是稳定修复：combined 的结果 **0/6/0**，seed0 反而从 8 掉到 0。不能把调三条 seed 当优化成功。

这说明专家负样本和接触差异确实存在，数据需要分层；但 v3 的 30 条有 18 条运动、76 个倒瓶，**无法用“专家本来就没打中”解释模型全部漏检**。

## 证据和复现

机器记录 [bowling_failure.json](bowling_failure.json) 含原报告 SHA256、验证曲线、新基线及 bootstrap；[专家对照](bowling_expert_diagnosis.json) 单列。脚本只读现有 PointWorld 文件，未修改其代码、数据或测试选择：

```bash
.runtime/ocbench-cpu/bin/python tools/analyze_bowling_model_failure.py --pointworld-root /path/to/PointWorld --output docs/benchmark_subset/bowling_failure.json
.runtime/ocbench-cpu/bin/python tools/analyze_ocbench_bowling.py --source results/ocbench-bowling/acceptance-004 --output results/ocbench-bowling/new-diagnosis --render
```

PointWorld 依据：`reports/bowling-v3-results.json`、`bowling-v3-diagnostic-results.json`、`bowling-v3-contact-diagnosis.json`、`bowling-v3-data-audit.json`、`bowling-v2-data-audit.json`；`benchmark_adapters/run_bowling_v3.py`、`collect_bowling.py`、`prepare_bowling_v3.py`、`pointworld/base.py`、`scene_featurizer.py`。训练提交 `ef870090`，本次只读 checkout `2d45b414`。官方 [PointWorld](https://github.com/NVlabs/PointWorld) 与 [Bowling 专家源码](https://github.com/seohongpark/ocbench/blob/6939a1e84f7ce9dbdd20c9f80d4cf335e8f83b49/ocbench/oracles/primitives/bowling.py)。

[完整模型 GIF / 30 新测试](https://peiqil.com/dynamic-robot-bench-viewer/pointworld/bowling-v3/) · [English](README.en.md)。
