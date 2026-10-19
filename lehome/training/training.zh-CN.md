# RGB-H / FlowACT 训练配套

**训练配套已实现：官方数据准备、同步回放、冻结划分、四组统一训练、独立验证选模、完整续训、离线评估和原生仿真入口。正式 30,000 步、多种子训练尚未执行。** 数值验收以 `training-validation.json` 为准；开发短跑不能当作方法优劣或叠衣成功率。

## 公平比较约定

四组统一使用 16 帧历史，每隔 3 个 90 Hz 物理步采样，跨度 0.5 s；三相机均为 640×480、相同 ImageNet 归一化、共享 ResNet18、每帧每相机 4×4 tokens；同样当前实测 12 维关节和 100×12 动作块。训练/验证窗口、数据顺序、成对初始化、归一化统计、动作损失、优化器及预算相同。参数骨架相同；等步数不意味着等算力。

- `rgb_history`：RGB-H，只用 RGB 历史与当前关节。数据加载不解码 `world_points/visible`，不产生 `track_xyz/query_xyz/hidden_displacement`；在线缓存也只接收 RGB/关节，传 GT 会报错。
- `geometry`：额外输入 K=16 个衣服点当前 XYZ，模型屏蔽过去轨迹。
- `tracks`：额外输入 K=16 个点的同窗口过去轨迹，只训练动作。
- `tracks_completion`：与 `tracks` 同样推理输入，联合补全另 48 点的过去位移；辅助头不向 actor 回灌，部署可删除。

本项目统一使用 RGB-H 命名。GT 是仿真上界，未实现 RGB tracker。辅助分支仍在 CVAE 未来动作 latent 之前；验证和在线推理固定 prior=0。

## 数据准备

官方动作源固定 `lehome/dataset_challenge@2bfdd30795ae25bba189649bf71cbb33f5b2a03c`。`prepare_flow_sources.py` 从官方每件衣服的未合并 Parquet 提取 action/index 和初始 pose，HTTP Range 避免下载原 RGB/深度。已有 10 件长袖、250 集、83,068 帧动作源；下载约 7.20 MB 的列块/元信息。验签范围是固定 revision 和已获取 range 的 SHA-256，**不是完整上游大 Parquet 的哈希验证**。派生文件另存 SHA，metadata 保留源路径/LFS OID/range 回执。第一集的动作和 pose 已与原合并数据及既有同步回放核对一致。

在 Baidu 独立 checkout 使用以下命令；所有数据/结果/缓存位于个人目录。`train.sh` 设置专用 venv、缓存、单卡 CUDA 和 CPU 线程。不要在项目外复用全局缓存。

```bash
# 全部官方动作源已准备；此命令可校验重用，或在可访问 HF 的机器重建。
bash integrations/LeHome/train.sh prepare \
  --output "$PWD/data/lehome_garment_folding/official-action-sources"

# 串行使用一张开发卡回放现成专家动作，并同步重新渲染 RGB/GT。
# 全量为 250 集，不是手工收集。失败 attempt/log 保留；同一命令可续跑。
.runtime/venv/bin/python integrations/LeHome/collect_flow_dataset.py \
  --sources "$PWD/data/lehome_garment_folding/official-action-sources" \
  --output "$PWD/results/lehome_garment_folding/flow-training-data-formal-01" --gpu 2

bash integrations/LeHome/train.sh dataset freeze \
  --data "$PWD/results/lehome_garment_folding/flow-training-data-formal-01" \
  --manifest "$PWD/results/lehome_garment_folding/flow-training-data-formal-01/dataset-formal-01.json" --formal
```

采集从官方单件衣服元信息确定 garment/local episode/pose，不猜合并数据偏移。PNG 为无损，压缩级别 1；忽略 Mac 传输产生的隐藏元数据文件。记录每个物理步、三相机内外参/刷新计数、实测关节、持久 cloth vertex、可见性及专家动作，规定 `obs[t] -> action[t] -> step -> obs[t+1]`。深度只用于当前可见表面筛选，不进入 actor。

冻结清单固定 episode 和全部 PNG/NPZ/报告的 SHA-256、公共窗口协议、按衣服划分及 **仅训练集** 拟合的状态/动作统计。Seen_0–7 train，Seen_8 validation，Seen_9 offline test。正式清单至少需要 200 集训练和 25 集验证；不完整开发集不能伪装正式数据。所有完整回放都保留成功标签，不静默按成功筛选。

当前开发数据是 Seen_0/1 各一集训练、Seen_8 一集验证；共 1,026 动作，223 个训练窗口、119 个验证窗口，无测试集。它用于配套验收；其余正式同步 RGB/GT 尚待批量回放，不能把已经备好的 250 集动作源称作已经生成 250 集 GT 数据。

## 训练、验证和续训

```bash
# 单组正式训练。默认完整 74.9M 架构，配置固定在 flow-formal.json。
LEHOME_GPU=2 bash integrations/LeHome/train.sh train \
  --data "$PWD/results/lehome_garment_folding/flow-training-data-formal-01" \
  --manifest "$PWD/results/lehome_garment_folding/flow-training-data-formal-01/dataset-formal-01.json" \
  --output "$PWD/results/lehome_garment_folding/flow-formal-01/rgb_history/seed-1000" \
  --imagenet "$PWD/.runtime/lehome/torch/hub/checkpoints/resnet18-f37072fd.pth" \
  --mode rgb_history --seed 1000

# 恢复同一次训练：完全相同命令加 --resume。
# --stop-after N 是受控中断检查，在 optimizer step N 完成后安全保存。

# 四组 × 三种子，在一张卡上串行执行；保留并恢复未完成任务。
bash integrations/LeHome/train.sh suite \
  --data "$PWD/results/lehome_garment_folding/flow-training-data-formal-01" \
  --manifest "$PWD/results/lehome_garment_folding/flow-training-data-formal-01/dataset-formal-01.json" \
  --output "$PWD/results/lehome_garment_folding/flow-formal-suite-01" \
  --imagenet "$PWD/.runtime/lehome/torch/hub/checkpoints/resnet18-f37072fd.pth" --gpu 2
```

正式默认 30,000 optimizer steps，有效 batch 16（microbatch 1、累积 16）、policy/backbone lr 均 1e-5、AdamW、clip=1、500 步 warmup 后 cosine 至 0.1×lr。每 500 步验证固定 128 个均匀抽取的窗口，每 1000 步保存；全量离线验证另用 `--max-windows 0`。同种子所有对照使用相同配置和验证索引。配置字段、数据指纹、初始权重 SHA、执行源码 SHA、各损失/共享梯度及加权辅助梯度都进入日志。

`configs/flow-dev.json` 是 6 步开发配方；`--pilot --tiny` 使用固定小型 Transformer，仍保持 16 帧、三相机和原始 RGB 分辨率。完整架构用 `--pilot` 而不加 `--tiny`。默认 point sampling 为 `fixed`：同窗口 K/hidden 划分固定；可在新配方中明确选 `epoch`，只对训练按 episode/epoch 重采样，验证永远固定。不静默改采样策略。

`last.pt` 原子保存模型、AdamW、scheduler、Python/NumPy/CPU/CUDA RNG、已消费样本 cursor 和最佳验证指标。采样器不把 DataLoader 预取进度算作已训练样本。SIGINT/SIGTERM 在优化器边界保存；未提交日志保留到单独文件。续训要求原 run 目录、相同数据/配方/核心源码；不能通过改 `--steps` 或学习率静默变更实验。`checkpoint.pt` 为最近的模型权重，`best.pt` **只按 validation prior-action L1** 选择，不用测试衣服或辅助指标替代选模准则。精确恢复验收针对相同软件/硬件环境；跨设备不保证 bitwise 相同。

原生 CUDA adaptive pooling 的反向不支持严格确定性，因此实现使用相同分箱的逐区均值；CPU 的值/梯度与原算子一致，实际 CUDA 连续/恢复检查另验证。图像和轨迹缓存有内存上限；RGB-H 不加载 GT tensor，Flow 只缓存少量 episode。

## 离线与仿真评估

```bash
LEHOME_GPU=2 bash integrations/LeHome/train.sh evaluate \
  --checkpoint /absolute/run/best.pt --data /absolute/replay-root \
  --manifest /absolute/dataset.json --split validation --max-windows 0 \
  --output /absolute/run/validation-full.json

LEHOME_GPU=2 bash integrations/LeHome/run.sh flow-rollout \
  --checkpoint /absolute/run/best.pt --garment Top_Long_Seen_9 \
  --seed 901 --output /absolute/fresh-rollout
```

离线动作误差按有效元素汇总，记录归一化 L1 和弧度 MAE。补全报告全部点 EPE、>5 mm 运动点 EPE、各自静态参考；补全 gate 失败仍按事实输出，不能用“训练完成”代替质量通过。评估校验 checkpoint 数据指纹及训练统计，使用保存的验证采样 seed。测试集只能显式 `--split test` 评估，不参与 best.pt 选择。

原生入口支持四组 checkpoint，保持相同相机刷新、物理、初始化和成功阈值；RGB-H 不读取策略用 GT，几何成功指标在 actor 外部计算。标准上限 600 步，首次成功后再运行 50 步。短跑或 pilot checkpoint 必须显式 `--pilot`；保存视频/动作/报告，不能当正式成绩。未来正式比较需要预先冻结新的成对场景，旧 20 个开发场景不再当作未见测试。

## 验收入口

`verify_training_package.py` 在真实且衣服隔离的数据上执行四组短训、两 worker 预取下的 3→6 步续训与连续 6 步逐项对比、改配方拒绝、完整 74.9M 模型优化器更新，以及 best checkpoint 离线回执重现。数值见 `training-validation.json` 与 [免认证训练页](https://peiqil.com/dynamic-robot-bench-viewer/lehome/training/)。这些检查不证明 Flow 对叠衣策略有益；最终仍需正式训练及配对闭环结果。

已执行原生检查：RGB-H 与 Tracks＋Completion 各 3 步，两个 960×480 视频均完整解码 4 帧；RGB-H 策略用 GT 轨迹读取为 0，Flow 为 4，两个部署实例均删除辅助头。这只是 checkpoint→原生仿真的接口验收。23 项 LeHome 测试全部通过；Mac 共 72 项 CPU 测试中 57 通过、15 因依赖缺失跳过。
