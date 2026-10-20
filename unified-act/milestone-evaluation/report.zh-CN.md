# 四方法 × 四阶段的实际任务评估

全部320次闭环已完成并通过证据复核；以下每格均为同一20个名义位姿各一次独立初始化的final_success。

| Method | 5k | 10k | 20k | 30k |
|---|---:|---:|---:|---:|
| ACT | 15% (3/20) | 10% (2/20) | 15% (3/20) | 10% (2/20) |
| Tracks (aux OFF) | 10% (2/20) | 0% (0/20) | 10% (2/20) | 15% (3/20) |
| v3 AUX | 15% (3/20) | 5% (1/20) | 20% (4/20) | 25% (5/20) |
| v4 AUX | 5% (1/20) | 15% (3/20) | 15% (3/20) | 15% (3/20) |

ACT仅当前RGB/state；Tracks (aux OFF)输入历史轨迹但不训练辅助目标；v3/v4训练过去补全与未来预测。辅助输出均未用于闭环动作推理。

20个名义位姿ID62001..62020固定，每个ID跨16组共用同一命令位姿与资产参考。每格只初始化一次，不根据形变筛选或重试。粒子布料微观形态/速度有随机差异，因此不能称精确物理状态配对。命令平移1e-6m/旋转1e-5deg/缩放1e-6、rest mesh SHA、关节位置/速度1e-5以及60physics ticks均核验。600动作/90Hz/prefix10、首次成功后50动作与原成功判据不变。主final_success、次ever_success；工程失败单列，完成结果不重跑。

ever_success events: 48/320; final_success events: 40/320. 这两个总数只是事件汇总；每格20次，不将320个跨方法事件合并为一个成功率。

实际运行控制通过：控制位姿62001曾在独立ACT/v4进程完全复现；但其他位姿揭示厘米级的布料随机差异，随后明确改为名义位姿协议。USD/物理机械臂位置一致、相机与布料实际更新；已有专家323动作回放成功，其初态与缓存差值0、末状态相对缓存RMS差2.58mm。另在先前无法微观匹配的62002/62003检查名义位姿验收和差异记录。这些控制不计入320次结果。

另做离线成功判据正例复核：4/4个已有专家末状态重算为成功，原版公式与记录数值一致。这些是已有数据检查，不计入320次新策略执行。

独立复核了320份实际初态数组和320次几何判定；20个名义参考mesh的最小两两坐标L∞差为0.028763 m。视频帧数核验320条。

相对各名义位姿参考，320次实际初态的mesh最大坐标差：中位0.00mm、P95 28.12mm、全局最大48.19mm；有限差分速度差全局最大0.516m/s。这些差异按预定协议记录，不筛掉任何正常初始化。Wilson区间包含本次位姿/初始化变化，无法估计训练seed变化。

全量427-window development验证（复用开发数据，不是成功率）：30k checkpoint的Chunk MSE依次为

- ACT: chunk MSE 0.059920; first-action MSE 0.023873 rad².
- Tracks (aux OFF): chunk MSE 0.060421; first-action MSE 0.025143 rad².
- v3 AUX: chunk MSE 0.060920; first-action MSE 0.024225 rad².
  Past EPE 9.68 mm (static 14.21); future EPE 7.78 mm (static 13.83).
- v4 AUX: chunk MSE 0.060224; first-action MSE 0.025203 rad².
  Past EPE 10.54 mm (static 14.21); future EPE 8.69 mm (static 13.83).

辅助头的运动拟合与策略成功率需要分别判断。单训练seed、单任务与20个初态不足以支持跨任务架构结论。比较各阶段均使用预定权重，没有按成功率挑选checkpoint。

可视化：v3/v4四阶段共64个窗口、128张原始英文PNG；网页展示同一8个预选窗口，另明确标注其中位/最大误差例子。16输入点/48保留点，过去/未来各0.5s，t=0已知锚点不计EPE。独立NPZ重计分通过512项检查；未来RGB/GT仅展示，未作为推理输入。专家窗口与真实policy闭环视频分开展示。投影仅使用校准有效的固定顶视相机；已有数据的腕部外参缓存错误，因此不展示腕部投影，3D轨迹与EPE不受此影响。

[Success matrix PNG](success-matrix.png) · [Verified outcomes JSON](matrix-summary.json) · [Trajectory catalog](trajectory-catalog.json) · [Independent rollout audit](rollout-evidence-audit.json) · [Frozen protocol](protocol.json) · [Runtime controls](runtime-controls-summary.json)

这里只验证LeHome仿真任务。Tracks使用包括遮挡历史的oracle顶点；没有物理机器人、视觉tracker部署或跨任务泛化测试。

Training/model source: f3c0744. Corrected runtime and scheduler identities are recorded in protocol.json and the verified summary. All16 exports strictly loaded and hashed before execution. Actual actions, horizons, initial states, success flags, USD/physics pose agreement and videos were checked. The earlier196-run stale-USD batch and stopped strict-microstate cohort are excluded; all320 final outcomes are newly executed under the uniform nominal-pose protocol.
Verified summary: 2026-10-20T14:27:11.005507+00:00.
