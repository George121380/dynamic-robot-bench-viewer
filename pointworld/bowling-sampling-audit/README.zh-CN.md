# Bowling 点采样与尺度审计

**已验证：小物体分辨率是合理嫌疑，但当前适配还存在可修正的 RGB-D 一致性问题，以及明显的时间／动作分布偏移。现在不能把失败作为 PointWorld 多物体能力上限。** 本轮只读 296 条现有输入与接触记录，运行官方 CPU 数据加载器和采样／池化函数；没有新训练、新模型预测或替换旧结果。

[免认证交互页](https://peiqil.com/dynamic-robot-bench-viewer/pointworld/bowling-sampling-audit/) · [English](README.en.md) · [旧模型预测](https://peiqil.com/dynamic-robot-bench-viewer/pointworld/bowling-v3/)

## 点数：没有完全丢掉瓶子，但分辨率有限

- 296 条、2960 个瓶子：原始每瓶输入 49–174 点，中位数 96。官方 1.5 cm 网格采样的确定性 test 分支保留 20–54 点，中位数 37；train 分支每体素随机选一点。
- 当前 `run_collision_chain.batch_from_arrays` 直接调用 `gather_features`，没有调用 `grid_sample_transform`。场景输入中位数 1804 点，官方采样后 942；机器人每时刻 500 点，采样后中位数 189。**当前输入已经更密，不能解释为我们只给了几颗点；密度改变仍可能影响预训练特征与稀疏卷积。** 未证明恢复官方采样会提升准确率。
- 当前 small-DROID 的四次 stride=2 池化对应 1.5 / 3 / 6 / 12 / 24 cm。seed3004 每瓶基础层占 30–52 格，6 cm 层占 3–9 格，24 cm 层占 1–2 格且与其他场景点混合。细点经 decoder 与 skip connection 保留，不能把粗层混合解释为物体被删除。
- 8 条横跨 train / validation / old test / fresh test 的输入，与官方 FNV 采样索引、Torch 深度投影、`GridPooling.forward(skip_postprocess=True)` 核对：索引／组数完全一致，逐相机可见性 mask 差异均为 0。该调用执行真实聚类和 torch_scatter reduction，仅跳过不改变聚类的 sparse tensor 构建及后处理。

## 更直接的问题：图像中的瓶子太小，点和缩放深度的筛选不一致

`collect_bowling.visible_inputs` 用 224×224 原始深度生成点；随后 `letterbox` 把 RGB / depth 缩为 180×180，加左右各 70 px 黑边到 320×180。RGB 用 bilinear、depth 用 nearest，K 已按像素中心修正，没有发现简单内参缩放错误。模型在点的投影位置 bilinear 取缩放后深度，并用后方 3 mm／前方 1.5 mm 门槛取 DINO 特征。

- 瓶子在其来源视角的选中表面投影：宽度中位数 **4.018 px**，高度 **13.661 px**；DINOv3 ViT-L16 patch 为 **16×16 px**。瓶子宽度不足一个 patch，细粒度识别和物体分离存在困难，但不能据此断言视觉特征完全没有信息，几何输入也仍在。
- 双视角合并后，每瓶通过图像特征门槛的点比例中位数 **50.0%**。只有 seed76 的一个瓶子完全无有效图像特征；没有“大量整瓶未被看到”的证据。
- 若逐瓶／逐来源视角统计，现有点覆盖中位数 **39.639%**。只在 CPU 上从同一份缩放后深度有效像素重新反投影当前点，这个几何一致性诊断为 **100%**；每视角点数中位数反而从 58 降为 37。新的点集与旧点集不同，没有生成未来标签，也没有送给网络。
- 这说明缩放前点云与缩放后深度的插值筛选造成明显损失，且**增加点数并不解决该损失**。100% 只是按相同像素生成／重投影的自一致性，不是 DINO 识别能力、未来预测准确率或因果消融结论。优先修复一致的 RGB-D 点生成，再比较模型。
- 将门槛放宽至 10 mm 的只读诊断让双视角中位覆盖达到 67.96%。它可能引入跨表面／跨物体特征，尚未运行预测，不能作为优化成效。

[论文附录 A.1](https://arxiv.org/html/2601.03782v1#A1) 也讨论小而薄的物体在深度／标定误差下难以区分。我们的仿真使用 GT 深度，但图像缩放与可见性实现仍会损失特征；这与原生数据的估计深度误差不是同一个问题。

## 物理尺寸相近，时间和运动尺度不相近

从固定 OCBench 版本 `6939a1e84f7ce9dbdd20c9f80d4cf335e8f83b49` 的实际编译模型读取：球直径 **8.5 cm**、质量 **64.311 g**；瓶子完整 body-local mesh 范围 **4.5448×4.5448×15.0027 cm**、质量 **4.5 g**。mesh 顶点经过 geom rotation / translation 变换，未把 MuJoCo `geom_size` 误当 mesh 半边长。单位为米，没有发现 ×1000 的单位错误；瓶宽约三个基础网格。

官方 CPU pipeline 的原生参考为 DROID 64 个训练片段／8 个源 episode、BEHAVIOR 32／2；禁用几何／颜色 augmentation，仍走 train 随机体素点选择。这里只是已下载锁定子集，不是整个预训练语料的分布统计。

- 两边都是 Robotiq 2F-85。当前姿态的夹爪 XYZ 范围中位数：Bowling **13.9 / 7.5 / 16.7 cm**，DROID **7.6 / 14.0 / 16.9 cm**；轴向会随姿态改变，尺寸量级接近。
- 当前场景范围中位数：Bowling **0.796 / 1.647 / 0.150 m**，DROID **0.890 / 1.597 / 1.351 m**。高度不同反映平面前景 ROI 与真实房间／桌面背景；这是 workspace 范围，不能冒充物体尺寸。
- DROID 无被动物体 GT identity，无法确定瓶子处于完整训练物体尺寸分布的哪一分位。BEHAVIOR/task0000 的 radio 可见 link 约 14×32×20 cm，是更大物体的辅助参考；它没有用于 small-DROID 的预训练。
- 全部 62 个恢复的 DROID episode 时间戳：episode 的采样间隔中位数分布为 **0.134–0.150 s**；其 10 步片段时长的 episode 中位数再取中位数为 **1.417 s**（范围约 1.400–1.433 s）。本次 Bowling 为 **0.4 s / 4 s**。论文的名义 1 秒与此次恢复发布包的实际时长需区分。
- `time_steps=torch.linspace(0,1,11)` 只编码相对步索引，没有实际 dt；`compute_flow_derivatives` 也不除物理秒数。机器人点每步平均位移的轨迹中位数：Bowling **5.902 cm**，DROID 对照 **2.082 cm**。
- 按发布 DROID 均值／方差归一化，先取每轨迹／每通道 `p95(|z|)` 再取轨迹中位数：Bowling 206 个 train 的 y 向 velocity-like 通道 **13.90σ**，acceleration-like **19.73σ**；64 个 DROID 对照分别 **1.51σ / 1.77σ**。这是索引有限差分特征，不是 m/s 或 m/s²。时间、动作路径、坐标方向共同改变了分布，尚未单独归因。
- 官方 `compute_helper_variables` 对相对 GT 逐轴截在 **±0.5 m**，没有硬限制模型输出。Bowling 自定义物理 Huber 使用完整 GT，没有做该截断。球最大单轴位移的 episode 中位数 **0.946 m**、最大 **1.506 m**；逐 episode 的球点–未来时刻中，超出任一轴 0.5 m 的比例中位数 **55.20%**。瓶子的同一比例全为 0。不能简单截断真实球 GT 来掩盖误差。

## 排除了什么，尚未排除什么

296 条保存的 500 Hz 正接触力记录中，全部机器人–球接触都在当前采样覆盖的 Robotiq body 上，没有遗漏“实际由未输入的机械臂／手腕撞球”这一问题。但覆盖 body 不等于视觉 mesh 与 collision surface 逐点重合。122/296 条的 0.4 s 输出时间格上没有恰好记录到机器人–球接触（±2.1 ms 判定）；离散机器人点曲线仍可能编码该作用，不能把它称为完全没有动作输入。

前一轮验证选模偏向静止解，step2750 在验证集有 24 TP / 19 FP / 24 FN，却被综合分数淘汰。所选模型 0/76 不能证明架构永远不能倾倒预测；也不能用已看过的测试重新选模。当前 query 球速近零，不能将失败简单归咎于输入缺少初始球速度。

**判断：当前设置确有影响解释的适配问题；小物体／稀疏结构是额外合理嫌疑，还不是唯一主因。** 现在能成立的是“这个 small-DROID + 当前适配／训练／选模设置，未学好快速长距离碰撞传播”。不能推广成 PointWorld 全尺寸模型或所有多物体场景都无效。

## 下一轮有解释力的检查（未执行训练）

1. 在物理尺寸、质量和动力学不变的情况下，统一缩放后 RGB-D 点生成与标定，恢复官方采样流程；逐物体记录 geometry 与图像特征覆盖，禁止使用未来 ID／contact 作为输入。
2. 先检查 8–16 条训练轨迹能否拟合机器人→球短期运动，再用约 1.4 秒／10 步窗口核对时间与动作特征范围。短窗口不保证完成原 4 秒全链倒瓶，不将其与旧 4 秒成绩混为一谈。
3. 单独改变相机距离／FOV，提高瓶子有效像素尺寸，保持物理场景和接触不变；与点采样变化分开做消融。增加采样点、整体放大仿真或放宽深度门槛都不能替代该对照。
4. 固定兼顾运动 FDE、倒瓶检出与静止误动的验证协议；新留出轨迹只在条件／选模锁定后测试。没有依据当前测试挑“好看的”checkpoint。

## 文件与复现

机器记录：`reports/bowling-sampling-audit.json`、`bowling-contact-scale-audit.json`、`bowling-native-reference.json`、`bowling-resized-depth-audit.json`、`bowling-sampling-function-check.json`。原始 296 个 NPZ 的 SHA256 在采样报告逐条记录。原生参考阶段源码 `94202d5`，官方函数核验 `9636322`，初次采样审计 `d6465ac`。审计／renderer 代码均在 `benchmark_adapters/`；没有改动原始 collector、训练入口或 checkpoint。

在有 NumPy / h5py / Pillow 的 CPU 环境：

```bash
python -m benchmark_adapters.audit_bowling_sampling --prepared .runtime/bowling-prepared/main-v3 --raw .runtime/bowling-raw/main-v3 --output reports/bowling-sampling-audit.json --display .runtime/bowling-sampling-display
python -m benchmark_adapters.audit_bowling_rgbd --prepared .runtime/bowling-prepared/main-v3 --output reports/bowling-resized-depth-audit.json
```

在安装原生模型依赖的 CPU 环境：

```bash
python -m benchmark_adapters.audit_pointworld_reference --output reports/bowling-native-reference.json --batch-output .runtime/bowling-native-reference-input.npz
python -m benchmark_adapters.check_bowling_sampling --prepared .runtime/bowling-prepared/main-v3 --native .runtime/bowling-native-reference-input.npz --output reports/bowling-sampling-function-check.json
```

接触 geometry 审计还需固定 OCBench CPU 环境与 benchmark checkout：`python -m benchmark_adapters.audit_bowling_contacts --benchmark-root /path/to/benchmark --prepared .runtime/bowling-prepared/main-v3 --raw .runtime/bowling-raw/main-v3 --output reports/bowling-contact-scale-audit.json`。全部本轮计算只用 CPU，没有新增 GPU 占用。
