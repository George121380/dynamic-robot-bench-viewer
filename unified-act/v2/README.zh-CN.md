# UnifiedACT v2：尽量少改 ACT

v2 保留固定版本 LeRobot 0.4.3 的 ACT。标准 ACT 条件直接调用上游 `ACT.forward()`；当前图像编码、CVAE、decoder、动作头、训练 L1+10KL 均由原生路径负责。新增逻辑放在外围：历史 RGB tokens、轨迹 MLP、一次点条件融合、两个点预测头。v1 保留在 `v1/` 和 Git commit `fe3ec86`，不转换旧权重。

[在线设计与review修复](https://peiqil.com/dynamic-robot-bench-viewer/unified-act/v2/) · [完整 ACT 差异](act-forward.patch) · [英文总图](architecture.svg) · [点分支](point-branch.svg) · [逐项 review 回复](review-response.zh-CN.md)。

## ACT 到底改了哪里

`act_extension.py` 继承上游 `ACT`，构造函数不改。默认无扩展时 `super().forward(batch)`；扩展路径保留上游 forward 原文，只增加两处条件接口：encoder 前追加历史 token/position，encoder 后对 memory 做点融合。点头另有 `prior=True, return_memory=True` 读取观察表示，避免未来动作 posterior 泄漏，并跳过无用的动作解码。

完整差异在 `act-forward.patch`；测试逐字核对当前安装的上游 forward、保存的原文及这份 patch。没有运行时 AST 修改、monkey patch、forward hooks 或修改已安装包。`model.py` 不再手写一套 posterior/encoder/decoder/action-head 前向。升级上游必须重新审查 diff 并通过 parity 测试。

外围仍显式处理输入归一化和原 ACT 的 padded L1+10KL。单帧 ACT 作为锚点，ACT-H 保留相同历史帧；stationary/tracks 共用同一轨迹编码和融合容量。不同任务的尺寸、相机、物理时间、统计和控制 schema 由 adapter 声明；不是一个 checkpoint 已经学会全部任务。

## 简化后的模型

当前 RGB 仍走原 ACT 的完整空间网格；过去 RGB 用同一 ResNet-18，池化4×4后加物理时间编码作为额外 tokens。点分支只有 `[当前XYZ/.5m, 历史位移/.05m, 时间秒, valid]` 的共享 MLP（H16：128→128→128→512，99,072参数），然后 `M′=M+tanh(g)Attn(LN(M),LN(P),LN(P))`，gate初始0.1。

**v2删除沿轨迹图像采样、点视觉投影、相机标定依赖和辅助随机种子计数器。** RGB 与几何分别编码，只在 memory 融合。stationary 仅将数值位移置零，保留锚点、时间、mask、RGB和参数容量，因此主对照现在更直接检验数值运动信息。没有3NN基底、关系网络、future planner或flow-matching动作头。

策略保留原 ACT action chunk。动力学与过去补全各用一个小的 XYZ/time cross-attention 头，直接回归位移；无 query self-attention，可以分块查询。点头均从 z=0 的原生观察 encoder 读出，隐藏过去/未来点仅作标签。

动力学仅支持声明为 **piecewise-constant、无预览** 的已提交控制：预测时间τ只可读取开始时间严格小于τ的命令。相同实际控制前缀下，改变更晚后缀不能改变早期预测。会预览整个轨迹的控制器必须导出实际施加前缀或重新声明模型协议，不能错误套用此 mask。

## 数据与训练外围

LeHome adapter 直接读取冻结缓存，不再导入旧实验脚本或改sys.path。actor观察与补全标签加载解耦；四种条件在aux OFF/ON下的actor输入均相同。每次启动对实际消费的core/rgb/points做SHA验收，生成包含真实字节hash的receipt；读取期间检测文件编辑。RGB-only且auxOFF不读取点文件。v2不读取原始trajectory或标定，所以原始标定变化不再改变模型输入。

现有LeHome点历史明确是 **persistent-vertex oracle，包括过去遮挡位置**；mask表示时间存在/坐标有限，不等于传感器可见性。v2没有实现真实tracker，不能将oracle结果当部署感知能力。

通用 `unified-act-data-v2` 强制必需键、维度/dtype、时间/mask、raw source/exporter hash、点来源与遮挡语义、控制语义、提交批次/时间和控制覆盖。provenance记录的一致性可以验收，记录是否真实仍需要原始导出/控制协议证明。不能把调用方声明当物理事实证明。

主实验aux默认OFF。OFF/detached使用普通PyTorch backward、AdamW和分开的actor/head clip；detached不构建encoder反向图，且fork/restore调用方RNG，不维护隐藏随机计数。原先的完整累积梯度限幅仅保留为显式选择的 `bounded` 实验选项，隔离在 `optimization.py`；其0.1限制是全局原始共享梯度范数，不是逐模块或Adam更新的10%保证。

验证记录最终反归一化、prior0、去padding的raw action chunk MSE、首动作MSE及逐维MSE/单位。补全统一记录all/moving/static EPE、repeat-current和可用时的“观测点平均LS速度”参考。该速度参考不使用隐藏点GT，也不是3NN或隐藏点真实速度。只有完整validation split且包含移动点时，才允许计算补全质量gate通过；训练窗口/部分验证只能做诊断。

恢复会验收自身所有模块（包括data.py）、上游ACT、依赖版本、数据字节receipt与配方；回放区间的旧日志归档，主曲线只保留有效step，记录attempt并累计耗时。CPU合成回归检查连续/中断恢复的模型、Adam状态、RNG逐位一致；真实任务没有训练。

`ObservationHistory`/`ChunkExecutor` 提供同步历史缓冲、reset、明确的执行前缀和动作队列。点条件由外部tracker提供与时间窗口对齐的因果轨迹。预测100步不等于执行100步；`n_action_steps`显式设置，执行相同前缀后重观测。该接口经CPU测试，已通过薄适配接入LeHome rollout，保留旧模型分支；Isaac实际闭环、异步延迟补偿或性能仍待验收。

## 验证与使用

```bash
python -m unittest discover -s tests -p 'test_unified_act*.py' -v
python -m dynamic_robot_bench.models.unified_act.runner preflight --config configs/unified-act/lehome-preflight.json
```

新配置schema为 `unified-act-run-v2`，steps仍为0。`evaluate` CLI要求checkpoint，避免把未训练输出当模型成绩。见 `validation.json`、`real-data-check.json` 和 `unit-tests.txt`。

本轮验证只用CPU；合成小模型回归包含少量optimizer更新，真实任务更新为0。CUDA/BF16、真实tracker、完整跨任务历史导出和新模型闭环质量仍未验收。原训练hold及过期B20z授权边界不变。

隔离checkout可复用已部署的LeHome环境，不复制权重/资产：显式设置 `LEHOME_RUNTIME`（旧.runtime/lehome）、`LEHOME_PY`（已验venv/bin/python）、`LEHOME_LAB`（旧IsaacLab目录）、`LEHOME_ASSETS_ROOT`（已下载资产），再调用当前checkout的 `integrations/LeHome/act_pilot_run.sh --checkpoint V2_CHECKPOINT --output NEW_OUTPUT --n-action-steps 10 ...`。launcher始终把当前代码root加入PYTHONPATH，环境路径不决定模型代码版本。此命令是后续验收入口，本轮没有执行。
