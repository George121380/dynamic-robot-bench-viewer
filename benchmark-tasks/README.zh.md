# Benchmark 任务 GIF 总览

**26 项目录任务与 16 个 PhysMani 原生任务均有 GIF，共 42 个。** [免登录在线页面](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/)支持中英文、任务搜索、优先级／来源／深度筛选和暂停。[English notes](README.en.md)。本目录仅新增可视化；已有站点页面保留。

来源包括项目既有传送带／双圆盘专家、手指诊断和 PhysMani 专家；ManiSkill、RoboCasa、robomimic、PerAct、Kubric、Physion、CLEVRER、CoPhy 与 Farama 官方／作者素材。各卡片保留原始链接；[sources.json](sources.json)记录来源、revision、署名、源哈希、相机裁剪、播放倍率和 42 个 GIF 的逐帧检查。PhysMani 保留上游代码 CC BY-NC-SA 4.0 标注。

**TurnFaucet-v1 唯一使用旧版 TurnFaucet-v0 官方动作参考，卡片明确标记 v0；不代表 v1 环境或数据验收。** PerAct 图是作者外部策略示例；PhysMani 图是已验收脚本专家示范。所有图均不计为本项目学习模型成绩。

GIF 为宽度不超过 384、8 fps、128 色的有损预览，共约 36.9 MiB；超过 20 秒的源视频加速并注明倍率。RoboCasa 取三视角拼接视频最左侧外部相机，PhysMani 使用 front（原始间隔 0.05 秒），预览传输曾转 JPEG quality 85。仅用于选型查看，不用于训练或物理指标。页面延迟加载，并用 JPEG poster 支持暂停和系统减少动画偏好。

42 个文件均经多帧、非重复像素、时长、循环及 SHA-256 检查；浏览器验证了语言切换、P0 五项、搜索、暂停和 390 像素窄屏。工具及完整双语任务／数据文档在私人实现仓库的 `task/benchmark-task-docs` 分支；其 main 未合并，不据此改变任务实现状态。

全部 42 个 GIF 后标明深度：已有原始／项目深度、可状态重渲染、可新采 RGB-D、现有 RGB 需估计／重建或待确认。说明对应数据版本的能力，GIF 仍只展示 RGB；可重渲染还需版本、相机和帧对齐验收。[depth_labels.json](depth_labels.json)保留双语摘要，不含内部数据路径。

深度筛选只作用于 26 项目录，16 个 PhysMani 原生任务始终显示。目录中已有深度 11、可重渲染 14、可新采 4、估计／重建 2、部分可用 2、版本待确认 1，条件允许重叠。ManiSkill 区分公开原始状态和项目诊断；PerAct 所选归档未解包、CoPhy 子数据集、Adroit 完整状态和 TurnFaucet-v1 的限制保留在各 GIF 旁。原 42 个 GIF／poster 未改动。
