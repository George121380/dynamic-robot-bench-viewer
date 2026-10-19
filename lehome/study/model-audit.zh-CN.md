# RGB-H / FlowACT 设计审查与公平实验

当前状态：用户已要求在开发机做一轮验证，现仅启动独立的小预算 pilot；完整正式训练与8卡节点申请仍暂停。原 ACT 最小扩展已实现，关闭扩展后原生推理输出和训练损失差均为0，核心梯度最大差4.69e-9；未来动作与隐藏点的信息边界检查通过。

## 开发机本轮验证（进行中）

执行目录 `results/lehome_garment_folding/act-dev-validation-01/`，独立于旧 `flow-study-01`，不解除后者的 `training-hold.json`。Seen_0完整回放0–15训练、16–19验证，20–24未用；20条无损RGB缓存逐值相同，数据指纹 `f2f982c9f6c73c9322e5205013a8310c6f0ad0e035da6913bf25d2c6e4bbd0aa`。保留完整专家失败，不按成功筛选。

本轮五组 ACT / ACT-H / Geometry / Tracks / Completion，各固定500更新、训练种子1000、有效batch16，250/500更新用完整4集验证的prior-zero action L1选best。AdamW lr及backbone lr1e-5、weight decay1e-4、恒定lr、clip10、BF16、严格确定性；相同初始化和样本顺序。保留原ACT encoder/decoder/CVAE、ReLU/postnorm及原padding损失。原ACT仅当前RGB；其他模型相同16帧/0.5s。当前三相机保持原完整空间特征；额外15帧用共享ResNet与4×4池化。原生decoder无padding接口，故只拼真实历史token，micro-batch1；不把冷启动假帧送入attention。

点编码器采用共享MLP，16×8展开，128→128→128→512，共99,072参数，点间交互交给原ACT。辅助头一层128维decoder（348,035参数），从posterior混合前观察token读取；隐藏query/标签不进actor，推理删除辅助头。两种点编码器已在相同8个窗口各学习300更新：MLP训练EPE6.596→2.863mm，大编码器6.593→5.108mm；独立旧开发验证119窗口为16.168/17.002mm，均未超过静态13.816mm。此处只证明可学习，尚无泛化收益；它们没有RGB上下文，不能据此否定RGB条件补全。策略点模块重新初始化，不继承这次小样本拟合权重。

本轮先进行真实640×480、两worker、有效batch16的连续2更新与1→2更新精确恢复检查，再串行五组500更新。随后五个固定开发pose5001–5005，主执行100/次执行10，两者均预测100，计划50次原生完整闭环。逐组核对相同pose/scale与初始cloth顶点差≤1e-5m；失败原样保留。单衣服/单训练种子/500更新只用于筛查，不能作收敛或稳定排名。GT轨迹仍是特权上界，不是RGB估计flow。

代码入口：`act_history_policy.py`、`act_pilot_data.py`、`validate_act_history.py`、`point_encoder_pilot.py`、`act_pilot_train.py`、`act_pilot_rollout.py`、`act_pilot_run.sh`、`run_act_pilot.py`。只使用开发机1 GPU2的可用资源，policy进程显存上限12GiB，不申请新节点，不操作同事任务。精确状态/更新数见 `pilot-status.json`、各run的 `metrics.jsonl` 与 `manifest.json`。在线页是发布快照，不是实时连接。

补充实测：真实640×480、两worker、有效batch16的连续2步与1→2步恢复全状态逐值一致；静态/平移/旋转/仿射输入语义检查通过；40个实际窗口的离线缓存与在线因果history相同，RGB点文件读取0。原ACT第250更新的427窗口验证L1=0.65747（训练均值参考0.83622），尚非闭环成绩。gpu17本轮SSH已恢复，代码工作树已同步GitHub提交；只同步代码，未运行GPU任务，远端会话认证helper尚缺，不使用远端共享GitHub凭证。

辅助作用范围：新原ACT扩展的补全头读取主Transformer混合前的观察token，aux梯度只经过共享CNN、图像投影和点MLP，不直接更新原ACT主Transformer。这样保留原actor骨架并排除未来posterior泄漏，但也限制了辅助监督的作用路径。

以下为本轮之前的提案与旧实现历史记录；“尚未实现/未训练”描述仅适用于其记录时点，最新状态以上文与执行JSON为准。

当前状态：按用户最新要求，训练调度进程已停止，正式训练尚未开始，等待用户检查下列设置。单个 8 卡节点的资源使用已获允许，但尚未申请或发起训练；数据回放继续，不会自动转入训练。暂停回执为任务目录中的 `training-hold.json`。最终结果尚未产生，不能据工程预检断言 Flow 有效。

## 最新提案：先做小实验与架构验收（未启动训练）

当前自定义四组不是原 ACT 的最小扩展；上一轮提出的原 ACT 同骨架重构仍未实现。下方原配方和31项检查是旧实现留档，不能当作新方案已通过验证。当前训练 hold 保持生效；本轮只做无参数更新的 CPU 检查。

**建议的小任务：** 仅 `Top_Long_Seen_0`，episode 0–15 训练、16–19 验证、20–24 暂不使用，先划分 episode 再切窗口。保留完整折叠流程、原三相机640×480、16帧/0.5s历史及原成功判定；先减少衣服多样性，避免任意裁剪前200步却没有完成实际折叠。原ACT单帧，ACT-H及三个点模型共享16帧历史。

**建议预算：** 先检查原 ACT 的500/1000/2000步学习曲线；最多五组×一个种子1000×2000步，即10,000次policy更新，是上一轮五组×三种子×30k提案的1/45。原ACT这条跑完可直接计入共同预算，不重复训练。若出现数据/控制错误或连单集动作都不能拟合，先排查再推进；ACT闭环成功率低本身不禁止比较历史/Flow，因为这也可能是单帧信息不足。各组执行相同2000步上限与验证时点，不按每组成绩单独追加预算。先用五个新开发pose种子5001–5005，每个执行节奏25次成对闭环，主100步前缀、次10步前缀，共50次；不动正式测试资产/种子。单种子仅筛查设置，不构成稳定方法排名。

提速优先是小数据、少更新、各组共用且逐字节一致的无损RGB解码缓存，保留端到端训练。冻结ResNet并缓存特征可用于更便宜的工程诊断，但会屏蔽补全监督改善视觉backbone的作用，不能用其负结果否定Completion。新ACT重构后必须重测吞吐，不沿用旧365小时估算，也不承诺未经实测的小时数。

**现有点编码器：** 每点每时刻8维 `[当前XYZ/0.5m, 过去相对当前位移/0.05m, 相对时间, 有效mask]`，形状B×16点×16时刻×8。共享Linear映射到256，每点两层时间Transformer，以当前时刻token汇总过去；再做两层点间Transformer，映射到每点512维，给ACT共16个token。点索引仅用于窗口内关联，没有语义mesh-ID embedding。相同权重处理各点，点的枚举顺序不应改变策略；时间值保留历史顺序信息。当前坐标用于定位，位移显式表达运动。

这套结构有合理动机，但256维、2+2层、K=16、aux=0.1都未经过充分模型选择。当前点编码器3,293,952参数。建议先比较简单候选：每点16×8按固定时间槽展开，三层共享MLP `128→128→128→512`，ReLU，线性层含bias共99,072参数；点间融合交给原ACT encoder，不另加Transformer。它保留完整固定窗口与mask，点顺序仍可交换。此候选尚未实现或训练，不能把参数变少等同于已验证效果更好。

**必须逐层通过的验收：**

1. 关闭扩展后，与原LeRobot ACT的输出、padding损失、CVAE与关键梯度数值一致；原ACT类复用，当前帧保留完整空间特征。此重构尚待实现。
2. 在静态、平移、旋转/仿射合成数据检查时间、坐标与mask，再用200–500步小样本学习检查两种点编码器是否可拟合。小样本拟合成功不等于泛化。
3. 补全在独立episode上同时报告全部点和>5mm运动点EPE，至少对照静态、最近邻、三近邻位移插值。隐藏点当前XYZ仅进辅助query；未来动作posterior不进辅助分支。辅助只更新共享观察编码，不回灌actor。
4. 记录动作/辅助梯度范数、夹角及权重后的比例，识别断连或明显冲突；aux=0.1只是待验证起点，不能靠梯度相等保证收益。补全失败可先令aux=0，仍单独验证Tracks。
5. 确认专家回放、单集拟合及控制链路有效后，再看Geometry−ACT-H、Tracks−Geometry、Completion−Tracks及对原ACT的差异；报告真实闭环、失败视频和固定步数学习曲线。静态物体或全不动片段不足以检验轨迹价值。

**数据质量快照：** 新采集已完成15条专家回放，其中13条在源动作结束时通过原几何判定。这不是策略成绩，也不是策略成功率上限。完整失败回放保留并带标签；应先核对控制、接触与终止时序，不将所有失败归因于网络。小任务变简单也可能使ACT达到天花板，无差异不否定Flow在更难动态任务上的作用。

**本轮已执行事实：** 旧开发集2个训练episode/223窗口、1个验证episode/119窗口的所有轨迹通过冻结SHA检查；没有读取正式test。验证集静态EPE13.816mm，最近邻10.838mm，三近邻10.671mm；>5mm运动点分别41.221、25.505、22.970mm。三近邻没有学习参数，只用16条输入轨迹与允许的当前query位置。该结果来自一个开发验证episode；旧6步神经预检只看2窗口，不能直接与它比较。

现有点编码器另完成CPU前向/梯度检查：输出B×16×512；点置换最大差1.07e-6，Geometry对历史修改完全不敏感，冷启动mask完全屏蔽NaN，空点集输出为零并mask，梯度有限且连通。改变过去运动使未训练编码输出改变，只证明输入通路存在，不证明学到了有用运动。**本轮optimizer更新数为0，未用GPU。**

折叠层之间当前空间邻近不等于布面邻接；16条稀疏轨迹加当前query也未必唯一确定48条其余历史。应将任务理解为有RGB和训练先验的条件估计，而非保证恢复完整4D形变。GT遮挡轨迹仍是特权信息。

机器可读提案及真实诊断见 [flow-pilot-review.json](flow-pilot-review.json)；只读脚本 `audit_track_interpolation.py` 不加载policy/optimizer/图像编码器/仿真。原生ACT依据 [LeRobot v0.4.3](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/act/modeling_act.py)。

## 旧四组实现与冻结配方（暂停，仅留档）

## 待用户审核的实际设置

以下是当前实现与 `configs/flow-study-01.json` 的有效设置，尚不表示用户已批准开始训练。

- **四组输入：** RGB-H 为 16 帧三相机 RGB + 当前 12 维实测关节；Geometry 加 K=16 当前 XYZ；Tracks 加同 K 点过去轨迹；Tracks+Completion 的推理输入与 Tracks 相同，训练时另以 48 个隐藏点的当前 XYZ 和过去位移构造补全监督。关节只输入当前状态，不输入关节历史。
- **共同观察与动作：** 原图 640×480，无裁剪、缩放或图像增强；历史间隔 3 个 90 Hz tick，覆盖 0.5 s。缺失历史用 mask；不复制首帧补齐。训练窗口起点也每 3 tick 取一个，按种子打乱、遍历完再打乱。预测未来 100×12 个关节控制目标，执行前 10 步后重规划（9 Hz），不做 temporal ensembling。
- **RGB/ACT 结构：** ImageNet ResNet18，冻结 BN 统计量但训练 backbone 权重；每帧每相机输出 4×4 空间 token，加相机、空间、时间编码。主宽度 512、8 heads、FFN 3200、dropout 0.1；共享观察 encoder 2 层、actor encoder 4 层、action decoder 1 层。CVAE posterior encoder 4 层、latent 32；训练采样 posterior，验证/推理固定 z=0。
- **点结构与补全：** 点编码宽度 256、4 heads、FFN 1024，先每点 2 层时间 encoder，再 2 层点间 encoder，映射到 512；补全 decoder 2 层，只从共享观察特征读取。先从当前可见表面 FPS 选 64 点，再按种子随机分 16 输入/48 隐藏；同一窗口每次访问固定，窗口内身份一致，不按位移大小抽样。XYZ 除 0.5 m，过去相对当前的位移除 0.05 m；补全输出以 std=1e-4 权重、零 bias 初始化。
- **数据：** 官方固定 revision 的 10 件 Seen 长袖、250 集动作全部回放，同一次回放生成 RGB/关节/GT。Seen_0–7 的 200 集训练，Seen_8 的 25 集验证，Seen_9 的 25 集离线测试；按衣服划分后切窗口。完整回放保留成功标签，不只挑成功轨迹。状态/动作均值和标准差只从训练集拟合，std 下限 0.01。完整清单及 SHA 冻结前不允许正式训练。
- **预算与优化：** 四组各种子 1000/1001/1002，共 12 次独立训练，每次 30,000 optimizer steps；单卡 micro-batch 1、累积 16，等效 batch 16，共消费 480,000 个窗口样本/次。AdamW：backbone/policy lr 均 1e-5，betas=(0.9,0.999)、eps=1e-8、weight decay=1e-4；500-step warmup，cosine 到起始 lr 的 0.1，梯度 clip=1。bfloat16、严格确定性、2 个 loader worker、4 CPU threads；ResNet 分批每次 6 张图，关闭 backbone checkpointing，单进程显存上限 16 GiB。
- **损失与选模：** 所有组为归一化动作的有效步平均 L1 + 10×KL；只有 Completion 额外加 0.1×归一化隐藏过去位移 SmoothL1（beta=1），不预测未来轨迹。每 500 更新在同样的固定 128 个验证窗口上计算 prior-zero action L1 选 best；每 1000 步保存完整断点，每 100 步日志。最终 best 在完整 validation/test 窗口离线评估。测试成功率、补全误差均不选模型。
- **闭环评估：** Seen_9、Unseen_0/1 各 10 个环境种子 2027..2036，四组×三训练种子共 360 次；点种子 2026，相同初始化、90 Hz、600 步上限、首次成功后再执行 50 步。主指标 final success，次指标 ever success，报告成对差值及 95% bootstrap 区间。8 卡将用于独立实验并行，不改为扩大 batch 的 DDP；具体并行调度仍待配置核准后实施。

**需要在解释结果时保留的限制：** GT 过去轨迹（包括遮挡段）是仿真特权信息，不是从 RGB 估计的 optical flow；RGB-H 与 Flow 的输入信息及有效容量不同。主机制比较为 Tracks−Geometry、Completion−Tracks。旧单帧 ACT 的 14/20 不属于这次公平主比较。6 步工程预检不能证明收敛或补全有效；目前没有正式训练分数。

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

正式任务目录为 `results/lehome_garment_folding/flow-study-01/`。`run_flow_study.py` 实现 250 集回放 → 全 SHA 冻结 → 四组×三种子等预算训练 → 全窗口 validation/test → 冻结场景闭环 → 配对统计。当前该调度器已按用户要求停止，只有独立采集进程继续。以下为既有串行入口参考，未经用户确认设置不得重启；8 卡并行执行尚未发起。出错保留记录，不静默改协议。

```bash
.runtime/venv/bin/python -u integrations/LeHome/run_flow_study.py \
  --output "$PWD/results/lehome_garment_folding/flow-study-01" \
  --sources "$PWD/data/lehome_garment_folding/official-action-sources" \
  --imagenet "$PWD/.runtime/lehome/torch/hub/checkpoints/resnet18-f37072fd.pth" \
  --config integrations/LeHome/configs/flow-study-01.json \
  --preflight "$PWD/results/lehome_garment_folding/flow-study-01/preflight-03" \
  --collection-gpu 3 --training-gpu 2
```

已执行部分仅在开发节点上进行：一张卡串行回放，另一张用于已结束的工程预检；没有正式训练在运行。状态查看 `study-status.json` 与 `training-hold.json`。页面是带时间戳的发布快照，不伪装实时结果。gpu17 仍因 SSH 连接失败未同步。

已执行：31 项 LeHome 检查全过；完整 74.9M 四组在 bfloat16、有效 batch 16、两 worker 预取下各运行 6 步，3→6 步续训与连续训练的参数/优化器/调度/RNG/cursor 完全一致（参数最大差 0），离线 best 回执一致。源码与预检见 `model-audit-validation.json`；这不是正式成绩。

在线页已发布，并将此次待审核设置与暂停状态同步为新快照。本地发布器支持后续约每半小时更新（需另行启动，依赖 Mac 联网及个人 Keychain）；发布器只发布文件，不启动训练。正式评估完成后可生成 12 个预先固定的完整视频与统计。临时 GitHub 认证只在子进程中生效，不在共享服务器保存凭证。
