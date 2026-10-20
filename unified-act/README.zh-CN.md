# 统一 ACT v1

已实现共用 ACT 观察编码、点条件融合、原生动作策略头、动作条件动力学头与可选历史补全头。后续各任务使用同一 `UnifiedACT` 类；只允许数据适配器改变相机、关节/动作维度、物理时间、坐标系、标定、训练集统计和预测范围。本轮不启动训练，不申请集群，不声称新的策略或预测性能。

[在线结构与实验对照](https://peiqil.com/dynamic-robot-bench-viewer/unified-act/)；[英文总图 SVG](architecture.svg)、[PDF](architecture.pdf)、[点分支详图](point-branch.svg)。代码在隔离分支 `task/unified-act` 的 `dynamic_robot_bench/models/unified_act/`，不是修改中的 `lehome-flow-interface` 或旧 PointWorld 工作树。

## 共用架构与两个接口

原生核心锁定已安装的 LeRobot 0.4.3 ACT：ResNet-18、512 维、8 heads、FFN 3200、4 层 encoder、1 层 decoder、4 层 CVAE posterior、latent32。当前 RGB 保留原生全空间分辨率；历史每帧每相机池化成 4×4 tokens，使用物理秒的位置编码。LeHome 是 H16、0.5s、三相机、state12、100×12 动作；其他任务不用伪造同样的关节数、控制频率或动作范围。

K 个输入点每点编码 `[当前XYZ/0.5m, 相对当前的过去位移/0.05m, 相对时间秒, 有效mask]`，H16 时为 128 维。共享 MLP `128→128→128→512`，ReLU，99,072 参数；不使用点ID、对象ID或点顺序 embedding。通过记录的 K、world-to-camera，在各历史图像投影位置双线性采样同一 CNN 特征，平均有效相机/时间后线性投影并加到该点 token。这个视觉均值不保留独立的视觉时间槽；运动时间结构仍由 MLP 的各槽显式编码。这是可检验的初始设计，尚无新性能证据。

点 token 在 **ACT encoder 之后、ACT decoder 之前**经带归一化的 cross-attention 调节 memory：`M′=M+tanh(g)Attn(LN(M),LN(P),LN(P))`，gate 初始0.1。它保留原生动作 decoder / head，提供明确的点条件入口。所有点融合变体使用相同位置和容量；未用3NN插值、刚性修正或固定几何先验。

- `policy(observation, targets=None)`：观察→动作 chunk。训练保留原 ACT 的 normalized padded action L1 +10KL；验证取 prior z=0 的真实动作输出，反归一化、排除 padding 后汇总 raw action chunk MSE，同时记录首动作 MSE。MSE 是最终动作误差，不是速度场误差。关节/夹爪混合单位，需同时保留维度统计，不能当作纯角度误差。
- `predict_dynamics(observation, current_queries, future_time, commands, command_time, command_valid)`：观察 + 事先提交的动作→未来点位移。命令只进入点头 memory；不能送入策略或历史补全。此基线称 **ACT-Dynamics**，不是上游 ACT 原本提供的预测能力。各 dynamics 条件共用同一 decoder，使用 normalized point SmoothL1 主目标、EPE/moving EPE 评估。
- `complete_history(observation, current_queries, past_time, shared=...)`：输入部分点的过去轨迹，补全另一组当前锚点的过去。当前锚点允许输入，隐藏过去仅是标签，t0不计损失。过去补全和未来预测是两件不同任务，不能混称。

两个点头结构相同而权重独立：`[queryXYZ/0.5m,time]→MLP128`，对投影至128维的 ACT memory 做4-head cross-attention，LN + FFN128→512→128，linear3×0.05m。没有 query self-attention，因此每128个查询分块与一次性查询在数值误差内一致，能支持数千点。

策略训练的 posterior 会读取未来动作标签；因此点头**重新以 z=0 编码观察**，不使用含 posterior 的策略 memory。补全可回传到共享 ACT encoder，修复旧头只监督前端 token 的问题。代价是额外的观察编码计算，必须记录耗时，不能据相同步数宣称相同算力。

## 与原 ACT 的公平比较

主表保留原 ACT 单帧；ACT-H（RGB-H）提供同等历史帧的视觉基线。运动信息的主要检验是 **ACT-Stationary-Tracks 对 ACT-Tracks**：当前锚点、H、相对时间、有效mask、点数、图像帧、视觉采样算法、网络参数和初始化全部配对，只将过去位移置零；必须在图像采样前改 XYZ。原先会遮掉过去mask的 Geometry 实验仍保留，但不能继续当作纯运动信息消融。代码保留 `geometry` 名称，含义已升级为 stationary control。

不同条件的数据、episode/family split、train-only统计、预训练 backbone、ACT核心初值、sample顺序、seed、有效batch、optimizer、调度、precision、更新步数、验证频率、验证窗口和选模规则锁定；不得把其他任务的架构换成 DiT/GRU 后横向比较增益。ACT-H 和点条件增加的信息/有效参数应明确报告，单帧 ACT 不具备相同输入信息。Stationary/Tracks 才是同容量运动信息对照。原生 ACT 和所有扩展模型都分配公共扩展模块，但被绕过的模块不会获得梯度，不把分配参数数目冒充有效容量相同。

补全默认 OFF。先使用 detached 头检查补全质量：actor 梯度不受其影响，独立 RNG 不消耗策略随机序列，独立clip不影响actor。通过开发集质量门槛后才比较 bounded 共享：每次完整累积16个microbatch分别取得主目标和补全的共享梯度，`α=min(1,0.1||gprimary||/||gaux||)`，头梯度另训，实际共享范数比上限0.1。它避免固定λ后期漂移，但不保证无梯度冲突或有性能增益。日志报告原始loss、实际权重、范数比、cosine和分开clip前范数。不得只按标量loss百分比解释训练影响。

建议首轮配对组：ACT、ACT-H、ACT-Stationary、ACT-Tracks，aux均OFF；之后 Tracks+detached、Tracks+bounded。所有组使用共同预注册的小任务、训练步数和验证规则。当前配置 steps=0，保留训练hold。未启动新正式训练或短训。

## 统一接入与迁移状态

`configs/unified-act/task-registry.json` 指定全部任务的公共模型工厂与数据接入边界。`data.py` 的 LeHome adapter 直接读冻结缓存，增加已记录的因果相机标定；RGB组不打开points.npz或trajectory.npz。`pointworld.py` 能将当前PointWorld RGB-D窗口和显式原始已提交命令接成 ACT-Dynamics；支持实际多相机，保留 shifted XYZ 与对应 shifted extrinsics。

旧 PointWorld 把当前点重复11次不是历史；机器人计划点云也不等于原始控制命令。旧 bowling/hook-pull 的完整 RGB/点历史比较，需要从原始记录导出真实因果历史及命令。新 `ContractDataset` 使用 `obs__`、`condition__`、`target__` 命名空间、逐样本SHA、family分组和split，拒绝把干预命令当专家策略示范。附 `data-contract.json`。旧模型/权重/入口作为legacy复现保留，不批量改写其他agent工作树；后续新实验必须指向公共工厂，未完成导出的任务不能标为“已完成全量训练迁移”。

## 运行与验证

依赖 extra `unified-act` 固定 torch2.7.0/torchvision0.22.0/lerobot0.4.3；优先复用已验环境，不在他人环境全局安装。预训练视觉权重通过 `imagenet` 路径加载，不在构造时联网下载。配置中的数据路径要换为实际私人目录。

```bash
python -m dynamic_robot_bench.models.unified_act.runner preflight --config configs/unified-act/lehome-preflight.json
python -m unittest discover -s tests -p 'test_unified_act*.py' -v
```

`dynamic-bench-model` 同一入口支持显式 `train`/`evaluate`，未实现调度器或自动申请GPU。train具备固定epoch采样顺序、全microbatch梯度累积、raw动作验证、验证集选模、严格recipe/代码/data指纹的optimizer/RNG恢复。中断保留最近完整checkpoint，后续未保存更新可重复；不写入半个累积更新。train入口本轮未做真实优化器更新或长程resume验收，因此不能视作正式训练验收通过。

已通过与未验证项以 `validation.json` 和 `real-data-check.json` 为准。CPU结构检查不能证明B200/BF16数值、闭环策略质量、完整跨任务导出正确性或最终效率。
