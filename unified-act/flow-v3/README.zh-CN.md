# Current RGB + historical flow / v3

按用户要求，Tracks 的历史输入仅为点轨迹；ACT 与 Tracks 均只接收当前三相机 RGB 和当前关节。H16、K16、Q48、0.5s 点历史保持不变。新实验从配对初始化重新开始，不续用输入定义不同的 v2 权重。RGB-H 与旧 v2 配置仍可复现。

架构只增加显式 `schema=unified-act-v3, rgb_history=false` 输入契约；`model.py` 跳过历史图像 token。原生 ACT forward、CVAE、decoder、action head、显式 patch 不变。点编码仍是共享历史 MLP + 一次 gated cross-attention。动作训练仍为原生 L1+10KL。辅助任务为隐藏过去补全与观察专用专家未来预测，两个头共用一次独立的 z=0 观察编码；共享辅助梯度全局范数上限10%。预测点不回填动作分支，未来动作不输入，未引入3NN。

## 提速设置

- 当前 RGB 直接取原冻结 `rgb.npy` 一帧；不分配、读取、传输过去15帧。每个 Tracks 微批次的主/辅助两次编码共处理6幅图像，旧版满历史为96幅。实际加速须看 GPU 稳态更新，不能把图像数量比当速度比。
- 点数据与未来标签的 episode 缓存容量由2提高到20，覆盖当前全部训练/验证 episode；lazy 缓存只解压每个已访问 episode 一次，RGB 继续 memory-map。启动实际文件 SHA 校验及运行期变更检查保留。
- query chunk128→1024，当前每个点头720个查询一次处理；不改标签或损失归一化。
- 共享梯度预算保留逐参数 FP64 reduction 和原 Python 加和顺序，统一一次传回 CPU，减少逐参数同步。微批次指标也统一传回；有限数检查保留。
- 两卡并行独立实验，BF16、microbatch1×accumulation16、AdamW lr1e-5 / wd1e-4 保持配对一致，不改图像分辨率或训练步数。

## 可续训

每25个完整 optimizer updates 原子写 `last.pt`，每100步完整427窗 validation 后写策略 checkpoint / best。`last.pt` 含模型、Adam、CPU/CUDA/Python RNG、数据 cursor、best 与 pending validation 状态。优雅停止在完整更新边界保存；硬中断最多回退到最近检查点，回放日志后缀归档，主曲线 step 唯一。

单个训练使用原 frozen checkout / config / output 加 `--resume`。节点 worker 同样加 `--resume`：完成训练由 runner 验证 identity 后直接返回，未开始的组正常启动。写入 prepared.json 同目录 `stop-pilot.json` 后 worker 停止分发并向自己创建的子进程发 SIGTERM、保存状态；再次明确 `--resume` 会归档停止请求。平台硬停不保证留下当前更新，应优先用 stop-file 并等待 stopped 状态。

续训严格核对源码、数据、配置和环境版本。只加载 actor 权重不称为续训。延长总步数须明确 runner `--resume --extend-steps N`，只允许变大且其余 identity 完全相同；该能力不自动授权3000步。新源代码或新输入定义应另起实验。

## 实验口径

两组×seeds1000/1001/1002×500updates，完整 validation 每100步记录 prior z=0 的反归一化真实 action chunk MSE（去 padding）、first action / 逐关节 MSE，past/future EPE 与梯度比例。保留原30次配对闭环安排，runtime 失败单独报告；3000步确认仍待 pilot 审阅。相同数据暴露与 ACT 初始化，计算成本单列。该对照检验 tracks+aux 整体收益，不能单独归因辅助任务。

点输入仍为包含过去遮挡顶点的 oracle；不是 RGB tracker。validation 为复用开发集，test20–24未触碰。验证回执与当前调度状态见 validation.json / status.json；不能把未训练点输出当质量结论。


最新资源安排：北京-H100-I的5卡（实际H800），同一500-step pilot。**用户明确本次不resume：六组全部从配对初始化开始，使用全新输出目录，不加载旧checkpoint。** 最多5组并行、第6组排队，旧任务保留档案，续训功能仍可后续使用。
