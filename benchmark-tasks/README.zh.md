# Benchmark 任务 GIF 总览

**26 项目录任务与 16 个 PhysMani 原生任务均有 GIF，共 42 个。** [免登录在线页面](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/)支持中英文、任务搜索、优先级／来源筛选和暂停。[English notes](README.en.md)。本目录仅新增可视化；已有站点页面保留。

来源包括项目既有传送带／双圆盘专家、手指诊断和 PhysMani 专家；ManiSkill、RoboCasa、robomimic、PerAct、Kubric、Physion、CLEVRER、CoPhy 与 Farama 官方／作者素材。各卡片保留原始链接；[sources.json](sources.json)记录来源、revision、署名、源哈希、相机裁剪、播放倍率和 42 个 GIF 的逐帧检查。PhysMani 保留上游代码 CC BY-NC-SA 4.0 标注。

**TurnFaucet-v1 唯一使用旧版 TurnFaucet-v0 官方动作参考，卡片明确标记 v0；不代表 v1 环境或数据验收。** PerAct 图是作者外部策略示例；PhysMani 图是已验收脚本专家示范。所有图均不计为本项目学习模型成绩。

GIF 为宽度不超过 384、8 fps、128 色的有损预览，共约 36.9 MiB；超过 20 秒的源视频加速并注明倍率。RoboCasa 取三视角拼接视频最左侧外部相机，PhysMani 使用 front（原始间隔 0.05 秒），预览传输曾转 JPEG quality 85。仅用于选型查看，不用于训练或物理指标。页面延迟加载，并用 JPEG poster 支持暂停和系统减少动画偏好。

42 个文件均经多帧、非重复像素、时长、循环及 SHA-256 检查；浏览器验证了语言切换、P0 五项、搜索、暂停和 390 像素窄屏。工具及完整双语任务／数据文档在私人实现仓库的 `task/benchmark-task-docs` 分支；其 main 未合并，不据此改变任务实现状态。
