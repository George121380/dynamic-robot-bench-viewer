# 使用 Flow 的长袖策略模型

**最新训练入口：** [RGB-H/FlowACT 训练配套](training.zh-CN.md) 已加入完整恢复、冻结清单和验证选模；23 项 LeHome 测试通过。下方 500 步结果保留为上一轮单窗口工程记录，不能与新的跨衣服验证指标直接比较。正式训练必须提供冻结 `--manifest`。

**已实现 `FlowACT`、因果在线历史缓存、同步 GT 回放采集、四组对照训练接口。10 项 Flow 专项测试通过。正式训练和 Flow 模型闭环成功率尚未完成。** 这份状态更新替代上一轮“只有设计”的实现状态；旧 RGB ACT 的 14/20 仍只属于公开单帧 checkpoint。

## 模型及对照

代码在 [flow_policy.py](flow_policy.py)。`FlowACT(FlowConfig(mode=...))` 支持同样模块和初始化的四组：

- `rgb_history`：同窗口三相机 RGB 历史、当前实测关节。
- `geometry`：额外输入 K=16 个衣服点的当前世界 XYZ。
- `tracks`：额外输入这 16 个点过去 0.5 秒的三维轨迹，只训练动作目标。
- `tracks_completion`：与 `tracks` 完全相同的推理输入，联合训练其余 48 个点的过去位移补全。

RGB 为 `uint8 [B,16,3,3,480,640]`，依次是 batch、时间、相机、通道、高、宽。共享 Frozen-BN ResNet18、ImageNet 归一化，每相机每帧池化为 4×4 tokens，加空间、相机和负相对时间编码。backbone 分块及 activation checkpointing 控制训练内存。

轨迹为 `float32 [B,16,16,3]`，依次为 batch、点、时间、世界 XYZ（米）。每点输入当前 XYZ、过去相对当前位移、负相对时间和有效性；固定空间尺度 0.5 m。2 层时间 Transformer、2 层点间 Transformer，宽度 256，投影到 512。点 ID 只用于跨帧对应，不编码为语义特征。

12 维关节 token、RGB tokens 和点 tokens 经 2 层共享观测编码器。动作分支使用 4 层 encoder、1 层 decoder、训练期 CVAE posterior（4 层、32 维 latent），输出 `[B,100,12]`。推理 latent 为零，输出反归一化为弧度关节目标；每消费 100 个目标重新规划。`FlowPolicy.reset()` 清空动作队列，`FlowHistory.reset()` 清空观察历史，二者须同时重置。

辅助头在插入动作 posterior **之前**读取共享观测表征。query 是隐藏点当前 XYZ 和 15 个过去时刻，2 层 decoder 输出 `[B,48,15,3]` 的位移。隐藏过去位置、专家未来动作和补全结果均不进入 actor。推理可删除整个辅助头。联合目标为动作 L1 + 10×KL + 0.1×masked SmoothL1；仅对有效过去位置归一化。

## 数据和运行

[collect_flow.py](collect_flow.py) 回放现成官方专家关节动作，同步保存三路无损 PNG、所有持久衣服顶点、相机内外参、可见性、关节及逐物理步时间。深度只用于当前可见表面筛选，不进入策略。相机刷新周期设为零以获得每步同步图像，物理与专家控制未修改。可见性是三相机深度一致性（1 cm 容差、3×3 邻域）的近似；选择仅使用当前表面，GT 遮挡期轨迹是特权上界。RGB tracker 未实现。

`FlowHistory` 每个 90 Hz 物理步保存当前观察；每隔 3 步取历史，共 16 帧。缺失历史用 mask，禁止复制当前帧伪造历史。在线接口没有未来动作或隐藏监督字段。[flow_data.py](flow_data.py) 先按衣服划分，再构造窗口：Seen_0–7 train、Seen_8 validation、Seen_9 test。当前只能对合并数据的 episode 0 确认衣服/pose；其他 episode 必须提供单衣服未合并源，代码主动拒绝猜测重复的本地 ID。

在已部署服务器的独立 checkout 中运行（路径必须绝对，因为 Kit 会切换工作目录）：

```bash
LEHOME_GPU=2 bash integrations/LeHome/run.sh collect-flow \
  --dataset-root "$PWD/data/lehome_garment_folding/demonstrations/top_long_merged" \
  --episode 0 --job-name ei-liupeiqi-data-collection \
  --output "$PWD/results/lehome_garment_folding/flow-replays/episode-000"

CUDA_VISIBLE_DEVICES=2 .runtime/venv/bin/python integrations/LeHome/train_flow.py \
  --data "$PWD/results/lehome_garment_folding/flow-replays" \
  --output "$PWD/results/lehome_garment_folding/flow-training/tracks_completion" \
  --mode tracks_completion --steps 100 --accumulate 1 --lr 0.0003 \
  --imagenet "$PWD/.runtime/lehome/torch/hub/checkpoints/resnet18-f37072fd.pth" \
  --pilot --tiny --overfit-index 60 --log-every 10 \
  --job-name ei-liupeiqi-wam-training
```

这条训练命令明确是工程检查：小型 Transformer、完整 ResNet18、原始 RGB 分辨率、单窗口过拟合。正式设置不使用 `--tiny/--pilot/--overfit-index`，默认 30000 步、有效 batch 16、lr 1e-5；四组须使用相同训练集合、窗口、初始化、数据顺序和预算，另在未见场景做配对闭环评估。上面的 pilot 权重不能作为正式叠衣基线结论。

## 已运行检查与限制

`tests/test_lehome_flow.py` 的 10 项检查覆盖当前可见点选择、ROS 相机投影、无隐藏目标/query 泄漏、训练期未来动作隔离、轨迹对动作的影响、辅助共享梯度、冷启动/空轨迹/NaN padding、成对初始化和点顺序、checkpoint/动作队列、离线与在线窗口及动作时间对齐。完整尺寸模型和真实窗口训练的数值验收另记录在 `flow-validation.json`，不能由 tiny 单测替代。

尚待正式实验：完整按衣服分割的同步数据、四组完整预算和多随机种子训练、未见衣服闭环成功率、估计轨迹版本。静态预测“过去位置等于当前位置”及运动点（窗口位移 >5 mm）误差必须同时报告；仅补全误差改善不足以证明 policy 获益。

## 本次实际数值验收

完整模型为 74,929,807 参数，原始 RGB 输入上前向/反向 4.45 秒，峰值 CUDA 分配 0.97 GiB（单批检查，不含完整优化器训练内存）。共享辅助梯度非零，全部梯度有限；删除辅助头，动作最大差值 0。真实回放 315 动作、316 观测、14746 顶点、948 张无损 RGB；951 个源产物在 Mac/Baidu 完整 SHA-256 一致。

三组小型 Transformer、完整 ResNet18、原始分辨率，同一 tick=180 窗口各训练 500 步、seed=1000、有效 batch=1、lr=3e-4，初始权重 SHA 相同。step 500 的 prior-zero 归一化动作 L1：RGB-H 0.02198，Tracks 0.02011，Tracks＋Completion 0.01863。这些都是训练误差，不是策略优劣证据。

**补全质量验收未通过。** 全部 48 个隐藏点平均误差 28.35 mm，高于静态预测 19.50 mm；12 个运动点上为 64.07 mm，静态为 75.71 mm。初始 100 步短跑也保留，未删掉不理想结果。现阶段不能把辅助头称为已学好的轨迹补全模型，更不能声称 Flow 提高了叠衣成功率。

[免认证模型/训练/轨迹查看页](https://peiqil.com/dynamic-robot-bench-viewer/lehome/flow-model/) · [机器验收记录](flow-validation.json)。源码与记录通过 GitHub 同步 Mac/Baidu；gpu17 再次 SSH banner 超时，未同步。
