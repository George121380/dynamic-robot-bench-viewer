# Review 修复与范围 / v2

依据 `dev/research/unified-act-flow-review/REVIEW.zh-CN.md` 对fe3ec86的审查。接受确定的数据错误与验收缺口，不把研究建议改写成已验证的模型收益。用户进一步要求尽量少改ACT；因此v2直接调用原生默认路径，扩展路径仅有一份显式小patch。

- **R1 已修复**：actor帧索引独立于补全标签，始终取正确的当前RGB。四条件、episode初段和完整历史窗口均有Torch回归；真实原分辨率样本补充验收。
- **R2 已修复消费路径**：启动核对实际cache SHA，恢复身份使用实际字节receipt。原始标定/trajectory依赖在v2删除，不再读取；不是声称它们已经过额外验收。运行中的文件编辑会拒绝。
- **R3 已修复**：移除旧loader动态导入，数据逻辑在自身data.py中；训练恢复指纹覆盖该模块及其他自身模块、上游ACT和依赖版本。
- **R4 边界明确，未实现tracker**：现有坐标仍是包括遮挡位置的oracle历史。metadata明确来源/mask语义；删除轨迹视觉采样，消除遮挡表面特征混入该分支的风险。没有伪称oracle输入已能在线观测。
- **R5 已加强**：v2强制字段、tensor schema、source/exporter hash、point来源、控制保持语义、提交批次和时间、覆盖范围。PointWorld桥不再接受一个布尔声明。记录真实性需要原始导出/控制协议验收，loader只能核对声明一致性。
- **R6 已实现**：统一evaluate返回补全EPE、moving/static、repeat-current、可用时的全局观测LS速度参考，以及质量gate；仅完整validation且有moving目标才有资格通过。不会自动启动shared实验。
- **R7 代码接入完成，运行验收待做**：新增通用同步ObservationHistory/ChunkExecutor和HistoryPolicy薄桥，LeHome rollout显式识别v2 checkpoint并使用新执行器；保留旧模型分支。队列/reset/执行前缀/懒加载历史经过CPU回归，launcher明确加入repo PYTHONPATH。Isaac实际闭环和延迟/策略质量仍待合格checkpoint后的任务级验收。
- **R8 已修复并实测**：恢复前归档回放日志后缀，主日志无重复step；记录attempt并累计耗时。合成小模型连续/中断恢复的权重、Adam状态、RNG逐位一致。异常退出耗时写入manifest；强制kill时只能保留最后durable heartbeat的耗时下界。

额外完成：动力学按query时间mask晚命令，通过命令后缀不影响分叉前输出的测试；真实三相机480×640、512维/4encoder原生ACT训练输出、主loss和encoder梯度逐位对齐。点补全不再维护隐藏随机seed/counter，验证不改变模型状态或RNG。默认OFF/detached不用自定义梯度累积算法。

未引入graph、future planner、视频生成或新的动作生成器。保留原生ACT、RGB-H、stationary/tracks主对照；运动信息是否被有用消费，仍需物理一致的配对任务与闭环结果证明。当前没有新的训练性能结论。
