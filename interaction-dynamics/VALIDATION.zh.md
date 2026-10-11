# 物理验收记录
四个 P0 协议的 20 种模式，在 seeds 0/1/2 上 **60/60 通过**。每条是实际 Panda/PhysX 控制和积分，包含原生 RGB-D、固定点以及真实子步接触。**69/69 CPU 回归测试通过**，包含原有测试和 13 项新接口测试。没有训练神经网络。

[English](VALIDATION.en.md) · [机器可读完整结果](validation.json) · [实现／命令](README.zh.md) · [23 个 GIF](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/)

## 逐任务模式
- ToolContactRelease：engage_pull、near_miss、contact_release、failed_engagement，每个 3/3。
- HookPullDynamics：successful_engagement、hook_miss、ineffective_contact、detachment，每个 3/3。无效接触只使目标沿错误方向移动，负 X 最大进展低于 1 mm，精化后的 engagement 标签为 false。
- CollisionChain：direct_push、two_body、three_body、near_miss、failed_propagation、collision_free_motion，每个 3/3。三体传播具有真实 A–B／B–C 接触和 A<B<C 起动顺序；机器人／工具没有直接接触 B/C。碰撞后 B 继续自由运动另行检查。
- FreeMotionInterception：interception、missed、early、late、redirection、no_intervention，每个 3/3。成功／early 有真实接触及速度改变；miss／late／无干预无目标接触；方向改变超过 45°。

另加独立物理参数配置：每个 A/B/C 分别采样质量、摩擦和恢复系数，工具请求速度 0.30–0.34 m/s、撞击角 ±0.025 rad。六种碰撞链模式 × 三个 seeds **18/18 通过**；独立参数的 OOD Physics 三体样本 **1/1 通过**。这是额外小样本，不替代基础 60 条验收。失败传播仍显式覆盖 B 为 5 kg／高摩擦。

每条 111 帧、110 指令、550 个物理接触子步。点运输最大数值差 **5.96e−8 m**；固定 IDs、局部点和物体位姿关系通过校验，RGB-D／相机矩阵有限且尺寸正确。

## 重现性与评价
- 固定 seed0 重跑全部 20 模式：poses、velocities、points、local_points、point_ids、contact_state、action/command **20/20 逐数组完全一致**，同一 Linux CPU 运行时。
- 在线 float32 对齐后，四个任务各一条＋真实 WebSocket 碰撞链一条，**5/5 在线／离线预测完全一致**；回调发生在未来积分之前。旧 60 条在线 float64 预测与导出 float32 的微小差异保留为修复证据。
- Offline CLI 实际评估了 WebSocket 三体样本，stationary smoke 的 Object ADE 0.088245 m、Target ADE 0.083155 m、传播准确率 0；无 contact head，接触时间指标为 null。它是接口／指标验证，不是学习模型成绩。
- Oracle 轨迹自比较 ADE/FDE 为 0；配对 response／OOD gap 接口通过测试及实际样本调用。跨域小样本的 stationary/CV gap 保存供检查，不据此推断模型泛化。
- 当前代码重放 60 条已存真值的 annotation：所有离散模式／事件及 phase 一致。不同 NumPy 版本只造成速度变化统计最大 1.49e−8 m/s 差异，不影响判定。

## 诊断对
3 个 seeds × 3 类，共 **9/9 accepted**；这是实测匹配验收，严格与近似另行区分。
- Action counterfactual：全部完整 native 初态 ID 相同，当前 RGB-D 完全一致；只改预提交动作。目标未来平均差异 4.13–4.56 cm。
- Hidden velocity：3 对当前 RGB-D/proprio/calibration／未来动作完全一致；移除 Oracle 当前点后，全部非历史模型输入严格相同。默认 Oracle 当前点仍有 0.39–1.04 微米差异，默认 strict 标志为 false。目标未来平均差异 28.45–33.30 cm。
- Contact history：A 过去有真实目标接触、B 无；未来动作相同。seed0/2 当前 RGB-D 完全相同，seed1 RGB MAE 为 0.000102/255；机器人／Oracle 点有近似差异，3 对均不称全输入严格 ambiguity。目标未来平均差异 5.04–7.06 cm。

配对字段完整保存 held／changed variables、状态／动作 ID、观察匹配及未来差异。可视化使用 A/B 共用的世界投影和尺度，anchor 静帧可单独检查。

## OOD 与保留的失败
OOD Geometry 4/4、OOD Physics 4/4、三体 OOD Composition 1/1；另验收 ID 两个几何 families 的三体样本 2/2。family1 的 cylinder 组件样本属于 train，完整 box→cylinder→box 顺序仍未出现在 ID。这些验证只覆盖所选正模式，不是所有 OOD 模式网格。

原记录保留，未改成功阈值：
- acceptance-001 的 failed_propagation seed2：B 移动 1.39 cm，拒绝；改为显式 5 kg／高摩擦 B 后重跑全部 60 模式通过。
- diagnostics-001 的工具式 contact history：当前可见状态不匹配，拒绝；改用原生球拦截后的物理历史。
- 早期 composition two_body 实际带三个目标，前缀组合已见过；排除出 OOD 验收，并让配置直接拒绝该错误范围。
- acceptance-005 重标注时重新计算的点出现 1.42e−14 m 差异，严格保留检查停止了任务；该不完整运行排除，改为保留已有 Oracle 点后生成 acceptance-006。
- 短暂速度相关不等于有效钩拉；engagement 加入超过 5 mm 负 X 进展门槛，近似标签明确标注。

## 产物、版本与限制
Git 只保存代码、配置、文档和小型结果摘要。原始 HDF5 位于本工作树 `data/interaction_dynamics/`，含 acceptance-006、repro-001、diagnostics-final-seed0/1/2、OOD profiles、online-final-001 和 ws-online-001；本地与 gpu17 都可读取。Baidu 同步代码／文档，未运行本轮仿真。

真实 RGB-D 积分来源 commit：`d68def4bc00e1bbe26a1b64d1cc51ab6226d301c`。acceptance-006 是保留原始数值、相机与指令的派生 annotation 文件，不是第二次物理积分；其原文件 SHA、仿真源码指纹与 annotation 指纹分开保存。最新 v3 annotation 已用当前代码逐条重放：60/60 标签及 phase 一致，原位姿、速度、点、接触、指令及 RGB-D 逐数组完全保留。新增 task_success 单独记录物理目标达成，privileged/progress_displacement_m 记录每帧各物体运动进度。

限制：hand 点为局部包围盒近似，phase／engagement 是近似标签；力接触可能短暂闪烁，导出只包括跟踪对象间及机器人–对象接触，未包含桌面反作用力。只做 CPU 单环境小样本验收，未做大规模稳定性统计或原 Isaac Sim 全流程 GPU 回归。P1 新门／抽屉 link、搬运滑移任务尚未扩展；已有路径保留。没有神经模型成绩。

