# 哪些历史信息帮助预测？第二轮单种子诊断

**验证选中结果：本设置下未检出目标自身历史的明确额外收益；工具历史在本设置的固定模型比较中降低误差。**

沿用第一轮数据/缓存/家族划分；seed 7、共同随机初始化，各 10000 更新、batch 32、target-only、补全 loss=0。防泄漏/loss/数据检查及独立 overfit 均通过。

| checkpoint | H0 ADE/FDE | H_self ADE/FDE | H_all ADE/FDE |
|---|---:|---:|---:|
| 验证选中 | 0.473/0.625 | 0.458/0.620 | 0.355/0.465 |
| 最终 10000 | 0.676/0.858 | 0.491/0.650 | 0.402/0.467 |

单位 mm，窗口→episode→跨 episode 等权平均；测试 15 家族/45 episodes/945 窗口。选中更新：H0 9500、H_self 9000、H_all 9500。

预定差值（正值为增益）：

- 验证选中：Delta_self +0.015 mm (+3.1%; 家族 bootstrap 95% CI [-0.024, +0.054])；Delta_cross +0.104 mm (+22.7%; 家族 bootstrap 95% CI [+0.069, +0.146])。
- 最终：Delta_self +0.185 mm (+27.4%; 家族 bootstrap 95% CI [+0.150, +0.222])；Delta_cross +0.089 mm (+18.1%; 家族 bootstrap 95% CI [+0.069, +0.111])。

接触建立附近 Δcross：+0.273 mm (+25.8%; 家族 bootstrap 95% CI [+0.101, +0.493])。
接触解除附近 Δcross：+0.030 mm (+3.4%; 家族 bootstrap 95% CI [-0.050, +0.116])。
实际移动子集 Δcross：+0.237 mm (+27.8%; 家族 bootstrap 95% CI [+0.155, +0.334])。

保持当前位置/恒速 ADE：3.629/0.781；恒速需目标历史。旧 C 验证历史 ADE 2.362，repeat-current 11.161；共享梯度 cosine 中位数 0.098、负比例 12.5%（16 batch，仅选中 C 可用），不支持普遍梯度冲突。细节见 DIAGNOSTICS.md。

优化仍限制判断：验证末段波动，自身历史差值对 checkpoint 敏感；10000 步不保证收敛。总正式更新 30000，耗时 102.8/96.6/98.7 s，峰值 allocated 均 205.9 MiB。

**下一步建议：** 同协议 seed 17/27 检查历史增益跨种子稳定性（仅准备配置，未运行）。本轮单种子、复用已查看测试集，属探索性诊断；家族 CI 不代表训练稳定性。H_all 的 target-only 与旧 A 不可直接归因比较。

[在线页面](https://peiqil.com/dynamic-robot-bench-viewer/oracle-history/round2/) · [原始指标](evaluation/metrics.csv) · [成对差值与 CI](evaluation/paired_differences.csv) · [冻结协议](PROTOCOL.md)。
