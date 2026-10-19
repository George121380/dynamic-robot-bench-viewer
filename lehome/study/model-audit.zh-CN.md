# RGB-H / FlowACT 设计审查与公平实验

结论：四组可以用于受控的仿真上界实验。信息边界和时间对齐检查通过；正式实验修正了补全初始化、位移尺度和共同执行节奏，并冻结数据、选模与成对闭环协议。训练任务先生成全部同步数据，再自动启动四组训练。最终结果尚未产生，不能据工程预检断言 Flow 有效。

## 审查结论与修改

- RGB-H 仅用同一窗口的 16 帧三路 RGB 与当前实测 12 维关节。Geometry 加 16 点当前 XYZ；Tracks 加这些点同窗口过去位移；Completion 只增加训练期的 48 点过去位移监督。所有条件共享 RGB 编码、actor、CVAE、动作块和配方。RGB-H 不加载 GT array，也不会调用 GT 缓存。
- 图像与顶点必须来自同一次新回放，遵循 `obs[t] -> action[t] -> step`。按衣服先划分，再切窗口；训练统计不读验证或测试。FPS 只看当前可见表面，随机 K/hidden 划分固定，不按运动或未来选点。遮挡期间的过去轨迹仍是仿真特权信息。
- 辅助头在共享观察编码器之后、未来动作 CVAE posterior 之前分支。隐藏 query、标签和预测结果均不回到 actor。部署删除辅助头；验证与推理使用 prior zero。该 CVAE 使用方式与 [ACT 官方说明](https://tonyzhaozh.github.io/aloha/) 一致；本模型的 RGB 历史及 Flow 模块是自定义扩展，不声称逐层复现公开 ACT checkpoint。
- 旧 head 随机输出对应几十厘米，超过训练位移尺度。仅用训练集的 42,144 个有效标签审查：位移中位数 0.84 mm、均值 14.46 mm、p95 112.08 mm。现在 XYZ 仍除 0.5 m，位移单独除固定 0.05 m；head 用微小权重和零 bias，从接近静态位移开始，第一步仍有共享编码器梯度。aux 权重保持 0.1，不根据测试成绩调节。旧 checkpoint 的默认单位和执行节奏保持兼容。
- 原来一次执行 100 步，约 1.11 s 才重新看观察，会限制使用运动反馈。正式四组统一预测 100 步、执行前 10 步再规划，物理和关节控制仍为 90 Hz。不加入 temporal ensembling，也不只给 Flow 更快的规划频率。
- 全量打乱采样时，反复解压整个 GT NPZ 会浪费 IO/CPU。Flow 可复用按源内容 SHA 保存的只读 NPY memmap；RGB-H 不调用它。缓存窗口与原数组逐值一致，重新打开时验证完整派生 SHA，不依赖 PFS 的 mtime。缓存不改变采样、标签或模型输入。

**容量解释：** 同骨架的总参数相同，但 RGB-H 不激活点编码器，不能声称有效容量或 FLOPs 完全相同。Geometry/Tracks 的机制对照共用同一有效架构；Tracks/Completion 的推理容量相同。Flow 整体对 RGB-H 的比较同时增加特权输入及配套编码器，因此不能把全部差异只归因于时间表示。会单独报告参数分组和实际时长。

## 冻结的比较

主基线是重新训练的 RGB-H，旧公开单帧 ACT 及其 14/20 仅是开发参考。

1. Geometry − RGB-H：额外当前三维几何的作用。
2. Tracks − Geometry：在相同点当前位置基础上，额外过去运动的作用。
3. Tracks+Completion − Tracks：相同推理输入下，补全监督的作用。
4. Tracks+Completion − RGB-H：整体特权几何/运动方案相对 RGB-H 的作用。

四组均为 16 帧、stride 3、90 Hz、0.5 s、三相机原始 640×480 RGB、当前关节、100×12 动作块和 10 步执行前缀。相同 ImageNet 权重、归一化、配对初始化、窗口顺序、30,000 optimizer steps、有效 batch 16、种子 1000/1001/1002、AdamW、policy/backbone lr 1e-5、500 warmup 与 cosine、clip 1。所有模型使用同样 bfloat16 与严格确定性；等更新步数不等于等算力，另记录时长与峰值显存。

动作 L1、10×KL 和损失 mask 相同；只有 Completion 加 0.1×补全 SmoothL1。按相同验证时点的 prior-zero action L1 选 best，不用测试成功率或补全误差选模型。每 1000 步轮换条件执行，使中间进度也有成对预算，不静默提前停止某组。源码、完整配方、数据指纹或观察协议改变时，续训拒绝继续。

官方未合并动作源固定 revision；总计 250 集、83,068 帧。正式同步数据为 Seen_0–7 各 25 集训练（200），Seen_8 的 25 集验证，Seen_9 的 25 集离线测试。全部完整专家回放保留并报告成功标签，不按成功静默过滤。只有 3 集的旧开发清单不能用于正式训练。

## 成对闭环与结论边界

固定 Seen_9、Unseen_0、Unseen_1 三件衣服，各 10 个新环境种子 2027..2036；每个训练种子都运行所有 30 个场景和四组，共 360 次。点抽样种子 2026 相同；初始 pose/scale 必须一致，初始 cloth 顶点最大差不超过 1e-5 m。上限 600 动作，首次成功后继续 50 步，原五个几何条件不变。主指标是 final success，ever success 为次指标。保存原生视频、关节动作、检查结果和 checkpoint SHA。

汇总要求全部成对单元齐全，缺失或重复时不能排名；保留失败 attempt。报告每件衣服、每个训练种子的成功率，以及共享训练种子/衣服/pose 重采样的配对 95% bootstrap 区间。三个衣服资产和三个训练种子的区间只能支持这个有限范围，不外推整个衣服分布。两个 Unseen 资产曾出现在旧开发评估，因此称为新 pose seeds，不把它包装成从未接触的全新 benchmark。

补全同时报告全部点与 >5 mm 运动点 EPE、静态参考。短训仍未超过静态参考，结构可训练不代表补全已有效。若 RGB-H 也未学会闭环折衣，不能据此宣布 Flow 无用，应先判断数据质量、收敛和控制误差。GT Flow 是特权上界；要主张相同 RGB 信息下的实际优势，还需要因果 RGB tracker 并在其估计轨迹上重训。

## 执行与续跑

正式任务目录为 `results/lehome_garment_folding/flow-study-01/`。`run_flow_study.py` 在完整预检通过后接管已运行的采集队列：250 集回放 → 全 SHA 冻结 → 四组×三种子等预算训练 → 全窗口 validation/test → 冻结场景闭环 → 配对统计。出错保留记录并停止，不静默改协议。

```bash
.runtime/venv/bin/python -u integrations/LeHome/run_flow_study.py \
  --output "$PWD/results/lehome_garment_folding/flow-study-01" \
  --sources "$PWD/data/lehome_garment_folding/official-action-sources" \
  --imagenet "$PWD/.runtime/lehome/torch/hub/checkpoints/resnet18-f37072fd.pth" \
  --config integrations/LeHome/configs/flow-study-01.json \
  --preflight "$PWD/results/lehome_garment_folding/flow-study-01/preflight-03" \
  --collection-gpu 3 --training-gpu 2
```

这是同一开发节点内的两张部分使用卡：一张串行回放，一张训练预检/训练，未占整节点或多个节点，不影响他人任务。状态查看 `study-status.json`，中间模型进度为 `training-progress.json`。页面是带时间戳的发布快照，不伪装实时结果。gpu17 仍因 SSH 连接失败未同步。

已执行：31 项 LeHome 检查全过；完整 74.9M 四组在 bfloat16、有效 batch 16、两 worker 预取下各运行 6 步，3→6 步续训与连续训练的参数/优化器/调度/RNG/cursor 完全一致（参数最大差 0），离线 best 回执一致。源码与预检见 `model-audit-validation.json`；这不是正式成绩。

在线页由 Mac 本地独立发布器约每半小时更新状态快照；依赖 Mac 联网和个人 Keychain 可用，离线期间服务器训练仍独立运行。最终服务器报告自动生成 12 个预先固定的完整视频与统计；发布器在恢复可用后上传。临时 GitHub 认证只在子进程中生效，不在共享服务器保存凭证。
