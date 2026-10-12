# 当前所有可获取真值深度的任务
目前已验证的范围是 **43 个具体任务／协议条目：24 项直接读取、10 项原状态重渲染、5 项新采集、4 项新交互协议原生 RGB-D**。去掉 PhysMani 总览重复计数，正常／高速各计一项；这不是 43 个独立物理任务家族。CLEVRER 原视频和未验收的 TurnFaucet-v1 不在该范围。

项目新加入的 **PointWorld-BEHAVIOR / task0000** 另有仿真初帧深度；**PointWorld-DROID** 也有可读初帧深度，但来源是 FoundationStereo 双目估计。二者作为额外数据域列在末节，不混入 43 项旧目录计数。

2026-10-11 只读复查了已有数据：39 份 NPZ／468 帧全部通过数值 SHA256、dtype、RGB-depth shape、有效像素、相机标定与 GIF 解码检查；另外读取四个 P0 协议各一条 111 帧 HDF5，通过 RGB-D／时间／持续点运输审计。没有启动新仿真、采集或模型推理。证据见 [depth_recheck.json](depth_recheck.json)，完整来源索引见 [depth_capable.json](depth_capable.json)。

[English](DEPTH_CAPABLE.en.md) · [原任务 RGB–depth GIF 页面](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/) · [四个新协议 RGB/XYZ/contact GIF](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/) · [旧运行说明与命令](../benchmark-tasks/depth/)

## 分类怎样理解
这里按**深度样本实际取得的路径**分类，不是按模拟器的所有潜在能力分类。39 个旧样本现在都可以读取，但其中 10 个是从状态补渲染、5 个是新轨迹。不能据此声称原 RGB 数据包已有深度，也不能把新轨迹 depth 配回旧视频。43 项均不依赖单目深度模型。

### 直接读取已有深度（24 项）
- ManiSkill 五项及 Panda 手指诊断共 6 项；这里读取的是已有项目诊断 HDF5，不是整套官方专家数据。官方存状态、不存图像的轨迹仍可按匹配版本另行重放。
- PhysMani 8 个基础任务 × 正常／高速，共 16 项。读取真实 `observations`／原深度 PNG，按 RGB24、near/far 解码；`wm_predictions` 中的预测深度不能用作 Ground Truth。
- MOVi-C、Physion-v1.5-OCP 两项是无机器人动作的物理数据。MOVi-C 为 ray distance，使用标准 Z 反投影前必须转换。

- **[PandaFingerArticulationDiagnostic-v0](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/PandaFingerArticulationDiagnostic-v0.gif)**：项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/PandaFingerArticulationDiagnostic-v0.json)。
- **[RollBall-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/RollBall-v1.gif)**：项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/RollBall-v1.json)。
- **[PullCubeTool-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/PullCubeTool-v1.gif)**：项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/PullCubeTool-v1.json)。
- **[PokeCube-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/PokeCube-v1.gif)**：项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/PokeCube-v1.json)。
- **[PickCube-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/PickCube-v1.gif)**：项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/PickCube-v1.json)。
- **[PushT-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/PushT-v1.gif)**：项目诊断 HDF5 已存 RGB、毫米深度及相机参数；没有下载官方专家全库。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/PushT-v1.json)。
- **[MOVi-C](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/MOVi-C.gif)**：官方 TFRecord 原生深度；数值为 ray distance，反投影前须转 Z。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/MOVi-C.json)。
- **[Physion-v1.5-OCP](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/Physion.gif)**：原始 TDW float32 深度和矩阵；同帧 RGB-D 从 1024² 同步步进采样为 256²。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/Physion-v1.5-OCP.json)。
- **[beat_the_rotating_buzz](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/beat_the_rotating_buzz.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/beat_the_rotating_buzz.json)。
- **[beat_the_rotating_buzz_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/beat_the_rotating_buzz_high_speed.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/beat_the_rotating_buzz_high_speed.json)。
- **[insert_onto_rotating_peg](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/insert_onto_rotating_peg.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/insert_onto_rotating_peg.json)。
- **[insert_onto_rotating_peg_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/insert_onto_rotating_peg_high_speed.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/insert_onto_rotating_peg_high_speed.json)。
- **[pick_moving_target_on_the_table](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/pick_moving_target_on_the_table.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/pick_moving_target_on_the_table.json)。
- **[pick_moving_target_on_the_table_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/pick_moving_target_on_the_table_high_speed.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/pick_moving_target_on_the_table_high_speed.json)。
- **[place_cups_on_rotating_frame](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/place_cups_on_rotating_frame.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/place_cups_on_rotating_frame.json)。
- **[place_cups_on_rotating_frame_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/place_cups_on_rotating_frame_high_speed.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/place_cups_on_rotating_frame_high_speed.json)。
- **[remove_cups_from_rotating_frame](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/remove_cups_from_rotating_frame.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/remove_cups_from_rotating_frame.json)。
- **[remove_cups_from_rotating_frame_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/remove_cups_from_rotating_frame_high_speed.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/remove_cups_from_rotating_frame_high_speed.json)。
- **[put_rubbish_in_moving_bin](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/put_rubbish_in_moving_bin.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/put_rubbish_in_moving_bin.json)。
- **[put_rubbish_in_moving_bin_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/put_rubbish_in_moving_bin_high_speed.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/put_rubbish_in_moving_bin_high_speed.json)。
- **[push_moving_button](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/push_moving_button.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/push_moving_button.json)。
- **[push_moving_button_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/push_moving_button_high_speed.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/push_moving_button_high_speed.json)。
- **[moving_basketball_in_hoop](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/moving_basketball_in_hoop.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/moving_basketball_in_hoop.json)。
- **[moving_basketball_in_hoop_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/moving_basketball_in_hoop_high_speed.gif)**：项目专家原始观测：解码 RGB24 深度；没有使用 WM 预测。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/moving_basketball_in_hoop_high_speed.json)。

### 恢复原状态重渲染（10 项）
RoboCasa 八项恢复原 XML、逐帧 state 和 ep_meta 相机；新渲染 RGB 与 depth 成对使用。不是从视频估计，也不是仅靠动作重跑。与原视频 RGB 有误差，已逐项记录；原状态渲染不能直接证明 action rollout、成功判据或新 contact labels 已验收。

ToolHang 使用原 MuJoCo 状态；Hammer 使用原 D4RL qpos/qvel/board_pos。所选 Minari Hammer 文件只有 success 等字段，不能单靠该包恢复完整原场景。

- **[OpenDrawer](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/OpenDrawer.gif)**：原 XML／状态／相机重渲染；与原视频 RGB MAE 8.25/255。本页 RGB 与 depth 为同次新渲染。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/OpenDrawer.json)。
- **[PanTransfer](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/PanTransfer.gif)**：原 XML／状态／相机重渲染；与原视频 RGB MAE 6.47/255。本页 RGB 与 depth 为同次新渲染。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/PanTransfer.json)。
- **[CloseFridge](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/CloseFridge.gif)**：原 XML／状态／相机重渲染；与原视频 RGB MAE 11.60/255。本页 RGB 与 depth 为同次新渲染。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/CloseFridge.json)。
- **[SlideDishwasherRack](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/SlideDishwasherRack.gif)**：原 XML／状态／相机重渲染；与原视频 RGB MAE 2.96/255。本页 RGB 与 depth 为同次新渲染。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/SlideDishwasherRack.json)。
- **[StackBowlsCabinet](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/StackBowlsCabinet.gif)**：原 XML／状态／相机重渲染；与原视频 RGB MAE 2.65/255。本页 RGB 与 depth 为同次新渲染。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/StackBowlsCabinet.json)。
- **[CoffeeSetupMug](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/CoffeeSetupMug.gif)**：原 XML／状态／相机重渲染；与原视频 RGB MAE 6.29/255。本页 RGB 与 depth 为同次新渲染。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/CoffeeSetupMug.json)。
- **[SlideToasterOvenRack](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/SlideToasterOvenRack.gif)**：原 XML／状态／相机重渲染；与原视频 RGB MAE 2.99/255。本页 RGB 与 depth 为同次新渲染。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/SlideToasterOvenRack.json)。
- **[StirVegetables](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/StirVegetables.gif)**：原 XML／状态／相机重渲染；与原视频 RGB MAE 7.12/255。本页 RGB 与 depth 为同次新渲染。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/StirVegetables.json)。
- **[ToolHang](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/ToolHang.gif)**：原 demo_0 完整 MuJoCo 状态重渲染 RGB-D；尚无原 RGB 逐像素对照。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/ToolHang.json)。
- **[AdroitHandHammer-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/Hammer.gif)**：原 D4RL qpos/qvel/board_pos 重渲染；所选 Minari 实文件只有 success，没有完整状态。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/AdroitHandHammer-v1.json)。

### 新采 RGB-D 已跑通（5 项）
这五项均已得到新 RGB-D，但验证范围不同：RLBench 两项是 live expert；传送带是保持机器人状态的传感器 smoke；双圆盘 depth 样本没有发生 A–B 碰撞；CoPhy 仅 Blocktower 的新小序列，不是完整发布 counterfactual 协议。

- **[match_and_pick_from_conveyor](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/match_and_pick_from_conveyor.gif)**：真实 Isaac Sim 场景新采 RGB-D；保持机器人状态，验证传送带运动及传感器，未评测抓取成功。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/match_and_pick_from_conveyor.json)。
- **[push_puck_collision](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/push_puck_collision.gif)**：现有 CollisionEnv 新采深度。该样本因 second_strike 失败，未发生 A–B 碰撞；不是成功示范。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/push_puck_collision.json)。
- **[reach_and_drag](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/reach_and_drag.gif)**：新采 RLBench 专家示范；任务 Python/TTM 与 PerAct 固定版本相同，未读取作者 Drive 归档。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/reach_and_drag.json)。
- **[CoPhy](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/CoPhy.gif)**：仅 Blocktower：作者函数和 URDF 的新 RGB-D 序列；没有执行完整 AB/CD 协议或其他子集。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/CoPhy.json)。
- **[sweep_to_dustpan_of_size](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/media/sweep_to_dustpan_of_size.gif)**：新采 RLBench 专家示范；任务 Python/TTM 与 PerAct 固定版本相同，未读取作者 Drive 归档。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/metadata/sweep_to_dustpan_of_size.json)。

### 新交互协议原生 RGB-D（4 项）
四个协议都保存 `observation/depth_m` float32 米制 Z，和 RGB、相机、proprioception 同步。共有 60 条基础验收 rollout，每条 111 帧观察／110 条预提交控制／550 个接触子步；固定物理点和接触标注在 privileged 分组。四协议复用三种物理家族，Hook 与 Tool 共享 L 工具环境。模型训练 adapter 尚未完成，不能把物理验收当作模型成绩。

- **[ToolContactRelease-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/media/ID_tool_contact_release_family000000_seed0_contact_release.gif)**：原生 RGB-D、固定物理身份点与接触字段已有验收；这里的 GIF 为 RGB/XYZ/contact，未显示 depth 色图。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/validation.json)。
- **[HookPullDynamics-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/media/ID_hook_pull_family000000_seed0_detachment.gif)**：原生 RGB-D、固定物理身份点与接触字段已有验收；这里的 GIF 为 RGB/XYZ/contact，未显示 depth 色图。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/validation.json)。
- **[CollisionChain-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/media/ID_collision_chain_family000000_seed0_three_body.gif)**：原生 RGB-D、固定物理身份点与接触字段已有验收；这里的 GIF 为 RGB/XYZ/contact，未显示 depth 色图。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/validation.json)。
- **[FreeMotionInterception-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/media/ID_free_motion_interception_family000000_seed0_interception.gif)**：原生 RGB-D、固定物理身份点与接触字段已有验收；这里的 GIF 为 RGB/XYZ/contact，未显示 depth 色图。 [数值／来源证据](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/validation.json)。

## 尚不属于已验证真值深度
- **CLEVRER**：标准视频没有已核实的像素 depth GT；对象中心 3D 标签不等于表面深度。用原视频时深度仍应标记 estimated。
- **TurnFaucet-v1**：匹配数据／资产未验收。当前旧 v0 GIF 不证明 v1 可用；它是待解决资产问题，不宜归类为“永远只能估计”。
- **旧传送带／双圆盘 RGB 数据**：已有新采 RGB-D 只解决新数据；没有证明原数据全部能精确补回 depth。
- **CoPhy BallsCF／CollisionCF、其他 Physion 类别**：本轮已验证范围只覆盖 Blocktower／Collide 实样，不能外推到所有子集。

## 对 4D MAE / World Model 的实际影响
真值深度能生成逐帧观测点云，但不会自动得到具有同一物理身份的点轨迹，也不会自动恢复接触、动作时序或关节 link 对应关系。因此按“depth 是否能拿到”看，上述 43 项都有已验证路径；按“能否直接接入当前统一 Oracle point/contact schema”看，四个新 P0 协议证据最完整，其他任务仍要转换／逐项验收。

统一输出应保留米制、ray/Z 类型、valid mask、同帧 RGB 与内外参，以及原始时间／frame_ids。39 个 NPZ 每份只均匀选 12 帧，GIF 播放时钟是展示时钟，不能当作密集动作条件训练序列。完整轨迹、多视角、分割、持续点、接触和无泄漏 split 需要另行准备。

本地旧样本入口为 `dev/benchmarks/benchmark_depth_samples/<sample_id>/sample.npz`，对应 metadata／preview.gif；新协议为 `dev/benchmarks/benchmark_interaction_data/acceptance-006/*.h5`。数值数组不在 Git，也未发布公网；代码／文档跨设备同步不代表原始数据自动复制。无 PR，本次更新在 `task/benchmark-subset-v1`。

## 新加入的 PointWorld 数据域：也能读取深度，来源单独标记
以上 43 项是原 Benchmark 目录的已验收真值深度范围。项目另新增 PointWorld 的两个数据域；不把这两个数据域与 43 个原目录条目混成独立任务数量。

- **[PointWorld-BEHAVIOR / task0000](https://peiqil.com/dynamic-robot-bench-viewer/pointworld/behavior.gif)**：仿真 `depth_linear`，发布 flow HDF5 直接保存 `camera_*/initial_depth`（uint16 毫米），除 1000 转米。另有局部 mesh 点及位姿轨迹；它是初帧深度，不是每帧 depth 视频。部署记录已验证 5,202 train／578 test clips 与 CPU loader；本轮读取锁定源码／报告，没有再次独立审计 Baidu 原数组，也未运行 OmniGibson 原始生成。支持补逐帧深度的源码路径不等于当前该流程已跑通。[相机源码](https://github.com/NVlabs/PointWorld/blob/3872ec6ee73146aa671192ef79b5dfbedc0246e3/simulation/behavior/camera.py)、[保存字段](https://github.com/NVlabs/PointWorld/blob/3872ec6ee73146aa671192ef79b5dfbedc0246e3/simulation/behavior/writer.py)。
- **[PointWorld-DROID](https://peiqil.com/dynamic-robot-bench-viewer/pointworld/droid.gif)**：发布 flow 同样有初帧 depth，但其生成器调用 FoundationStereo 从左右双目图像估计深度，必须标记 `estimated_stereo`，不能称为仿真／独立测量真值。部署记录 578 train／49 test clips；模型估计已在发布数据中，因此读取这些值无需重新推理。独立 `depth_320x180` 发布组可另下载，但当前 flow 子集不能自动当作逐帧 depth 历史。Viewer 的“GT”表示训练参考标注，不证明物理 Oracle 精度。[深度生成源码](https://github.com/NVlabs/PointWorld/blob/3872ec6ee73146aa671192ef79b5dfbedc0246e3/real/compute_depth.py)、[flow 初帧字段](https://github.com/NVlabs/PointWorld/blob/3872ec6ee73146aa671192ef79b5dfbedc0246e3/real/convert_2d_flows_to_3d.py)。

来源锁定 `PointWorld-data 3872ec6` 与部署 `9f35b32`，项目根目录 `dev/model/PointWorld/reports/data.json`、`dataset-loader.json`；[公开进展与 GIF](https://peiqil.com/dynamic-robot-bench-viewer/pointworld/)。上述两份 GIF 是 scene-flow 参考／预测对比，不是 RGB–depth 热图。BEHAVIOR 的仿真 GT、DROID 的双目估计、RGB-only 单目估计应作为三类不同来源保留。
